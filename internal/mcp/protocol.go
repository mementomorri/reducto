package mcp

import (
	"encoding/json"
	"fmt"
)

const (
	JSONRPCVersion = "2.0"
)

type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type Response struct {
	JSONRPC string       `json:"jsonrpc"`
	ID      interface{}  `json:"id,omitempty"`
	Result  interface{}  `json:"result,omitempty"`
	Error   *ErrorObject `json:"error,omitempty"`
}

type ErrorObject struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func NewError(code int, message string, data interface{}) *ErrorObject {
	return &ErrorObject{
		Code:    code,
		Message: message,
		Data:    data,
	}
}

func (e *ErrorObject) Error() string {
	return fmt.Sprintf("JSON-RPC error %d: %s", e.Code, e.Message)
}

func ParseRequest(data []byte) (*Request, error) {
	var req Request
	if err := json.Unmarshal(data, &req); err != nil {
		return nil, fmt.Errorf("failed to parse request: %w", err)
	}
	if req.JSONRPC != JSONRPCVersion {
		return nil, fmt.Errorf("invalid JSON-RPC version: %s", req.JSONRPC)
	}
	return &req, nil
}

func MarshalResponse(resp *Response) ([]byte, error) {
	return json.Marshal(resp)
}

func SuccessResponse(id interface{}, result interface{}) *Response {
	return &Response{
		JSONRPC: JSONRPCVersion,
		ID:      id,
		Result:  result,
	}
}

func ErrorResponse(id interface{}, code int, message string, data interface{}) *Response {
	return &Response{
		JSONRPC: JSONRPCVersion,
		ID:      id,
		Error:   NewError(code, message, data),
	}
}

const (
	ParseError     = -32700
	InvalidRequest = -32600
	MethodNotFound = -32601
	InvalidParams  = -32602
	InternalError  = -32603
)

const (
	FileNotFound   = -32001
	ParseFailure   = -32002
	TestFailure    = -32003
	GitConflict    = -32004
	LSPUnavailable = -32005
)
