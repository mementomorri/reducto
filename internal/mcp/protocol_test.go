package mcp

import (
	"encoding/json"
	"testing"
)

func TestParseRequest_Valid(t *testing.T) {
	data := []byte(`{"jsonrpc":"2.0","id":1,"method":"read_file","params":{"path":"main.go"}}`)

	req, err := ParseRequest(data)
	if err != nil {
		t.Fatalf("ParseRequest failed: %v", err)
	}

	if req.Method != "read_file" {
		t.Errorf("Expected method 'read_file', got '%s'", req.Method)
	}
}

func TestParseRequest_InvalidJSON(t *testing.T) {
	data := []byte(`not valid json`)

	_, err := ParseRequest(data)
	if err == nil {
		t.Error("Expected error for invalid JSON")
	}
}

func TestParseRequest_InvalidVersion(t *testing.T) {
	data := []byte(`{"jsonrpc":"1.0","id":1,"method":"test"}`)

	_, err := ParseRequest(data)
	if err == nil {
		t.Error("Expected error for invalid JSON-RPC version")
	}
}

func TestSuccessResponse(t *testing.T) {
	resp := SuccessResponse(1, map[string]string{"status": "ok"})

	if resp.ID != 1 {
		t.Errorf("Expected ID 1, got %v", resp.ID)
	}
	if resp.Error != nil {
		t.Errorf("Expected no error, got %v", resp.Error)
	}
}

func TestErrorResponse(t *testing.T) {
	resp := ErrorResponse(1, MethodNotFound, "Method not found", "unknown")

	if resp.ID != 1 {
		t.Errorf("Expected ID 1, got %v", resp.ID)
	}
	if resp.Error == nil {
		t.Fatal("Expected error, got nil")
	}
	if resp.Error.Code != MethodNotFound {
		t.Errorf("Expected code %d, got %d", MethodNotFound, resp.Error.Code)
	}
}

func TestMarshalResponse(t *testing.T) {
	resp := SuccessResponse(1, map[string]interface{}{"files": []string{}})

	data, err := MarshalResponse(resp)
	if err != nil {
		t.Fatalf("MarshalResponse failed: %v", err)
	}

	var parsed map[string]interface{}
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Failed to unmarshal: %v", err)
	}

	if parsed["jsonrpc"] != "2.0" {
		t.Errorf("Expected jsonrpc 2.0, got %v", parsed["jsonrpc"])
	}
}

func TestErrorCodes(t *testing.T) {
	tests := []struct {
		name     string
		code     int
		expected int
	}{
		{"ParseError", ParseError, -32700},
		{"InvalidRequest", InvalidRequest, -32600},
		{"MethodNotFound", MethodNotFound, -32601},
		{"InvalidParams", InvalidParams, -32602},
		{"InternalError", InternalError, -32603},
		{"FileNotFound", FileNotFound, -32001},
		{"ParseFailure", ParseFailure, -32002},
		{"TestFailure", TestFailure, -32003},
		{"GitConflict", GitConflict, -32004},
		{"LSPUnavailable", LSPUnavailable, -32005},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.code != tt.expected {
				t.Errorf("Expected %d, got %d", tt.expected, tt.code)
			}
		})
	}
}

func TestErrorObject_Error(t *testing.T) {
	err := NewError(FileNotFound, "File not found", "/path/to/file.go")

	if err.Error() == "" {
		t.Error("Error message should not be empty")
	}
}
