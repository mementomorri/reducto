package lsp

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"path/filepath"
)

type PythonClient struct {
	base    *BaseClient
	rootDir string
}

func NewPythonClient(rootDir string) (*PythonClient, error) {
	pyrightPath, err := exec.LookPath("pyright")
	if err != nil {
		pylspPath, err2 := exec.LookPath("pylsp")
		if err2 != nil {
			return nil, fmt.Errorf("neither pyright nor pylsp found in PATH")
		}
		base, err := NewBaseClient(pylspPath)
		if err != nil {
			return nil, err
		}
		return &PythonClient{
			base:    base,
			rootDir: rootDir,
		}, nil
	}

	base, err := NewBaseClient(pyrightPath, "--outputjson")
	if err != nil {
		return nil, err
	}

	return &PythonClient{
		base:    base,
		rootDir: rootDir,
	}, nil
}

func (c *PythonClient) Initialize(ctx context.Context, rootURI string) error {
	absPath, err := filepath.Abs(rootURI)
	if err != nil {
		absPath = rootURI
	}
	uri := "file://" + absPath
	return c.base.Initialize(ctx, uri)
}

func (c *PythonClient) FindReferences(ctx context.Context, uri string, line, column int) ([]Reference, error) {
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

func (c *PythonClient) GoToDefinition(ctx context.Context, uri string, line, column int) (*Definition, error) {
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

func (c *PythonClient) Shutdown() error {
	return c.base.Shutdown()
}

func (c *PythonClient) IsInitialized() bool {
	return c.base.IsInitialized()
}

func (c *PythonClient) DidOpen(uri, content string) error {
	return c.base.DidOpen(uri, "python", content)
}

func (c *PythonClient) DidClose(uri string) error {
	return c.base.DidClose(uri)
}
