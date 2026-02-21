package lsp

import (
	"context"
	"fmt"
	"sync"
)

type Reference struct {
	URI     string `json:"uri"`
	Line    int    `json:"line"`
	Column  int    `json:"column"`
	Context string `json:"context,omitempty"`
}

type Definition struct {
	URI    string `json:"uri"`
	Line   int    `json:"line"`
	Column int    `json:"column"`
}

type Client interface {
	Initialize(ctx context.Context, rootURI string) error
	FindReferences(ctx context.Context, uri string, line, column int) ([]Reference, error)
	GoToDefinition(ctx context.Context, uri string, line, column int) (*Definition, error)
	Shutdown() error
	IsInitialized() bool
}

type Manager struct {
	clients map[string]Client
	mu      sync.RWMutex
}

func NewManager() *Manager {
	return &Manager{
		clients: make(map[string]Client),
	}
}

func (m *Manager) Register(language string, client Client) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.clients[language] = client
}

func (m *Manager) GetClient(language string) Client {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.clients[language]
}

func (m *Manager) Initialize(ctx context.Context, rootURI string, languages []string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	for _, lang := range languages {
		client, ok := m.clients[lang]
		if !ok {
			continue
		}

		if !client.IsInitialized() {
			if err := client.Initialize(ctx, rootURI); err != nil {
				return fmt.Errorf("failed to initialize LSP for %s: %w", lang, err)
			}
		}
	}

	return nil
}

func (m *Manager) FindReferences(ctx context.Context, language, uri string, line, column int) ([]Reference, error) {
	m.mu.RLock()
	client, ok := m.clients[language]
	m.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("no LSP client for language: %s", language)
	}

	return client.FindReferences(ctx, uri, line, column)
}

func (m *Manager) GoToDefinition(ctx context.Context, language, uri string, line, column int) (*Definition, error) {
	m.mu.RLock()
	client, ok := m.clients[language]
	m.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("no LSP client for language: %s", language)
	}

	return client.GoToDefinition(ctx, uri, line, column)
}

func (m *Manager) Shutdown() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	var errs []error
	for lang, client := range m.clients {
		if err := client.Shutdown(); err != nil {
			errs = append(errs, fmt.Errorf("%s: %w", lang, err))
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("shutdown errors: %v", errs)
	}

	return nil
}
