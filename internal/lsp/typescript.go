package lsp

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"path/filepath"
)

type TypeScriptClient struct {
	base    *BaseClient
	rootDir string
}

func NewTypeScriptClient(rootDir string) (*TypeScriptClient, error) {
	typescriptServerPath, err := exec.LookPath("typescript-language-server")
	if err != nil {
		tsserverPath, err2 := exec.LookPath("tsserver")
		if err2 != nil {
			return nil, fmt.Errorf("neither typescript-language-server nor tsserver found in PATH")
		}
		base, err := NewBaseClient(tsserverPath)
		if err != nil {
			return nil, err
		}
		return &TypeScriptClient{
			base:    base,
			rootDir: rootDir,
		}, nil
	}

	base, err := NewBaseClient(typescriptServerPath, "--stdio")
	if err != nil {
		return nil, err
	}

	return &TypeScriptClient{
		base:    base,
		rootDir: rootDir,
	}, nil
}

func (c *TypeScriptClient) Initialize(ctx context.Context, rootURI string) error {
	absPath, err := filepath.Abs(rootURI)
	if err != nil {
		absPath = rootURI
	}
	uri := "file://" + absPath
	return c.base.Initialize(ctx, uri)
}

func (c *TypeScriptClient) FindReferences(ctx context.Context, uri string, line, column int) ([]Reference, error) {
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

func (c *TypeScriptClient) GoToDefinition(ctx context.Context, uri string, line, column int) (*Definition, error) {
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

func (c *TypeScriptClient) Shutdown() error {
	return c.base.Shutdown()
}

func (c *TypeScriptClient) IsInitialized() bool {
	return c.base.IsInitialized()
}

func (c *TypeScriptClient) DidOpen(uri, content string) error {
	return c.base.DidOpen(uri, "typescript", content)
}

func (c *TypeScriptClient) DidClose(uri string) error {
	return c.base.DidClose(uri)
}
