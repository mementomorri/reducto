package lsp

import (
	"context"
	"testing"
)

func TestNewManager(t *testing.T) {
	mgr := NewManager()

	if mgr == nil {
		t.Fatal("NewManager returned nil")
	}
	if mgr.clients == nil {
		t.Error("clients map should be initialized")
	}
}

func TestManager_Register(t *testing.T) {
	mgr := NewManager()
	mockClient := &mockClient{initialized: false}

	mgr.Register("go", mockClient)

	client := mgr.GetClient("go")
	if client == nil {
		t.Error("Client should be registered")
	}
}

func TestManager_GetClient_NotFound(t *testing.T) {
	mgr := NewManager()

	client := mgr.GetClient("nonexistent")
	if client != nil {
		t.Error("GetClient should return nil for unregistered language")
	}
}

func TestPosition_Structure(t *testing.T) {
	pos := Position{
		Line:      10,
		Character: 5,
	}

	if pos.Line != 10 {
		t.Errorf("Expected Line 10, got %d", pos.Line)
	}
	if pos.Character != 5 {
		t.Errorf("Expected Character 5, got %d", pos.Character)
	}
}

func TestRange_Structure(t *testing.T) {
	r := Range{
		Start: Position{Line: 1, Character: 0},
		End:   Position{Line: 5, Character: 10},
	}

	if r.Start.Line != 1 {
		t.Errorf("Expected Start.Line 1, got %d", r.Start.Line)
	}
	if r.End.Line != 5 {
		t.Errorf("Expected End.Line 5, got %d", r.End.Line)
	}
}

func TestLocation_Structure(t *testing.T) {
	loc := Location{
		URI: "file:///path/to/file.go",
		Range: Range{
			Start: Position{Line: 1, Character: 0},
			End:   Position{Line: 1, Character: 10},
		},
	}

	if loc.URI != "file:///path/to/file.go" {
		t.Errorf("Expected URI 'file:///path/to/file.go', got %s", loc.URI)
	}
}

func TestReference_Structure(t *testing.T) {
	ref := Reference{
		URI:     "file:///path/to/file.go",
		Line:    10,
		Column:  5,
		Context: "func example()",
	}

	if ref.URI != "file:///path/to/file.go" {
		t.Errorf("Expected URI 'file:///path/to/file.go', got %s", ref.URI)
	}
	if ref.Line != 10 {
		t.Errorf("Expected Line 10, got %d", ref.Line)
	}
}

func TestDefinition_Structure(t *testing.T) {
	def := Definition{
		URI:    "file:///path/to/file.go",
		Line:   20,
		Column: 0,
	}

	if def.URI != "file:///path/to/file.go" {
		t.Errorf("Expected URI 'file:///path/to/file.go', got %s", def.URI)
	}
	if def.Line != 20 {
		t.Errorf("Expected Line 20, got %d", def.Line)
	}
}

func TestInitializeParams_Structure(t *testing.T) {
	params := InitializeParams{
		ProcessID: 1234,
		RootURI:   "file:///project",
		Capabilities: map[string]interface{}{
			"textDocument": map[string]interface{}{
				"references": map[string]bool{"dynamicRegistration": false},
			},
		},
	}

	if params.ProcessID != 1234 {
		t.Errorf("Expected ProcessID 1234, got %d", params.ProcessID)
	}
	if params.RootURI != "file:///project" {
		t.Errorf("Expected RootURI 'file:///project', got %s", params.RootURI)
	}
}

func TestReferenceParams_Structure(t *testing.T) {
	params := ReferenceParams{
		TextDocumentPositionParams: TextDocumentPositionParams{
			TextDocument: TextDocumentIdentifier{URI: "file:///test.go"},
			Position:     Position{Line: 10, Character: 5},
		},
		Context: ReferenceContext{IncludeDeclaration: true},
	}

	if params.TextDocument.URI != "file:///test.go" {
		t.Errorf("Expected URI 'file:///test.go', got %s", params.TextDocument.URI)
	}
	if params.Position.Line != 10 {
		t.Errorf("Expected Position.Line 10, got %d", params.Position.Line)
	}
	if !params.Context.IncludeDeclaration {
		t.Error("IncludeDeclaration should be true")
	}
}

type mockClient struct {
	initialized bool
}

func (m *mockClient) Initialize(ctx context.Context, rootURI string) error {
	m.initialized = true
	return nil
}

func (m *mockClient) FindReferences(ctx context.Context, uri string, line, column int) ([]Reference, error) {
	return []Reference{
		{URI: uri, Line: line, Column: column},
	}, nil
}

func (m *mockClient) GoToDefinition(ctx context.Context, uri string, line, column int) (*Definition, error) {
	return &Definition{URI: uri, Line: line, Column: column}, nil
}

func (m *mockClient) Shutdown() error {
	m.initialized = false
	return nil
}

func (m *mockClient) IsInitialized() bool {
	return m.initialized
}
