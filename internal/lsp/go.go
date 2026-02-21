package lsp

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"path/filepath"
)

type GoClient struct {
	base    *BaseClient
	rootDir string
}

func NewGoClient(rootDir string) (*GoClient, error) {
	goplsPath, err := exec.LookPath("gopls")
	if err != nil {
		return nil, fmt.Errorf("gopls not found in PATH: %w", err)
	}

	base, err := NewBaseClient(goplsPath, "serve")
	if err != nil {
		return nil, err
	}

	return &GoClient{
		base:    base,
		rootDir: rootDir,
	}, nil
}

func (c *GoClient) Initialize(ctx context.Context, rootURI string) error {
	absPath, err := filepath.Abs(rootURI)
	if err != nil {
		absPath = rootURI
	}
	uri := "file://" + absPath
	return c.base.Initialize(ctx, uri)
}

func (c *GoClient) FindReferences(ctx context.Context, uri string, line, column int) ([]Reference, error) {
	params := ReferenceParams{
		TextDocumentPositionParams: TextDocumentPositionParams{
			TextDocument: TextDocumentIdentifier{URI: uri},
			Position:     Position{Line: line - 1, Character: column},
		},
		Context: ReferenceContext{IncludeDeclaration: true},
	}

	result, err := c.base.Call(ctx, "textDocument/references", params)
	if err != nil {
		return nil, err
	}

	var locations []Location
	if err := json.Unmarshal(result, &locations); err != nil {
		return nil, fmt.Errorf("failed to parse references: %w", err)
	}

	refs := make([]Reference, len(locations))
	for i, loc := range locations {
		refs[i] = Reference{
			URI:    loc.URI,
			Line:   loc.Range.Start.Line + 1,
			Column: loc.Range.Start.Character,
		}
	}

	return refs, nil
}

func (c *GoClient) GoToDefinition(ctx context.Context, uri string, line, column int) (*Definition, error) {
	params := TextDocumentPositionParams{
		TextDocument: TextDocumentIdentifier{URI: uri},
		Position:     Position{Line: line - 1, Character: column},
	}

	result, err := c.base.Call(ctx, "textDocument/definition", params)
	if err != nil {
		return nil, err
	}

	var loc Location
	if err := json.Unmarshal(result, &loc); err != nil {
		return nil, fmt.Errorf("failed to parse definition: %w", err)
	}

	return &Definition{
		URI:    loc.URI,
		Line:   loc.Range.Start.Line + 1,
		Column: loc.Range.Start.Character,
	}, nil
}

func (c *GoClient) Shutdown() error {
	return c.base.Shutdown()
}

func (c *GoClient) IsInitialized() bool {
	return c.base.IsInitialized()
}

func (c *GoClient) DidOpen(uri, content string) error {
	return c.base.DidOpen(uri, "go", content)
}

func (c *GoClient) DidClose(uri string) error {
	return c.base.DidClose(uri)
}
