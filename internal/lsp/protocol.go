package lsp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
)

type Position struct {
	Line      int `json:"line"`
	Character int `json:"character"`
}

type Range struct {
	Start Position `json:"start"`
	End   Position `json:"end"`
}

type Location struct {
	URI   string `json:"uri"`
	Range Range  `json:"range"`
}

type TextDocumentIdentifier struct {
	URI string `json:"uri"`
}

type TextDocumentPositionParams struct {
	TextDocument TextDocumentIdentifier `json:"textDocument"`
	Position     Position               `json:"position"`
}

type ReferenceContext struct {
	IncludeDeclaration bool `json:"includeDeclaration"`
}

type ReferenceParams struct {
	TextDocumentPositionParams
	Context ReferenceContext `json:"context"`
}

type InitializeParams struct {
	ProcessID    int                    `json:"processId"`
	RootURI      string                 `json:"rootUri"`
	Capabilities map[string]interface{} `json:"capabilities"`
}

type InitializeResult struct {
	Capabilities map[string]interface{} `json:"capabilities"`
}

type BaseClient struct {
	cmd          *exec.Cmd
	stdin        io.WriteCloser
	stdout       io.Reader
	requestID    atomic.Int64
	pending      map[int64]chan json.RawMessage
	pendingMu    sync.Mutex
	initialized  bool
	shutdownOnce sync.Once
}

func NewBaseClient(command string, args ...string) (*BaseClient, error) {
	cmd := exec.Command(command, args...)
	cmd.Env = append(os.Environ(), "NO_COLOR=1")

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to create stdin pipe: %w", err)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		stdin.Close()
		return nil, fmt.Errorf("failed to create stdout pipe: %w", err)
	}

	cmd.Stderr = os.Stderr

	if err := cmd.Start(); err != nil {
		stdin.Close()
		return nil, fmt.Errorf("failed to start LSP server: %w", err)
	}

	client := &BaseClient{
		cmd:     cmd,
		stdin:   stdin,
		stdout:  stdout,
		pending: make(map[int64]chan json.RawMessage),
	}

	go client.readResponses()

	return client, nil
}

func (c *BaseClient) readResponses() {
	reader := bufio.NewReader(c.stdout)

	var contentLength int
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return
		}
		line = strings.TrimSpace(line)

		if line == "" {
			if contentLength > 0 {
				body := make([]byte, contentLength)
				if _, err := io.ReadFull(reader, body); err != nil {
					return
				}

				var response struct {
					ID     int64           `json:"id"`
					Result json.RawMessage `json:"result"`
					Error  *struct {
						Code    int    `json:"code"`
						Message string `json:"message"`
					} `json:"error"`
				}

				if err := json.Unmarshal(body, &response); err == nil {
					c.pendingMu.Lock()
					if ch, ok := c.pending[response.ID]; ok {
						delete(c.pending, response.ID)
						ch <- body
					}
					c.pendingMu.Unlock()
				}
				contentLength = 0
			}
			continue
		}

		if strings.HasPrefix(line, "Content-Length: ") {
			lengthStr := strings.TrimPrefix(line, "Content-Length: ")
			contentLength, _ = strconv.Atoi(lengthStr)
		}
	}
}

func (c *BaseClient) Call(ctx context.Context, method string, params interface{}) (json.RawMessage, error) {
	id := c.requestID.Add(1)

	request := map[string]interface{}{
		"jsonrpc": "2.0",
		"id":      id,
		"method":  method,
		"params":  params,
	}

	body, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	ch := make(chan json.RawMessage, 1)
	c.pendingMu.Lock()
	c.pending[id] = ch
	c.pendingMu.Unlock()

	header := fmt.Sprintf("Content-Length: %d\r\n\r\n", len(body))
	if _, err := c.stdin.Write([]byte(header)); err != nil {
		return nil, fmt.Errorf("failed to write header: %w", err)
	}
	if _, err := c.stdin.Write(body); err != nil {
		return nil, fmt.Errorf("failed to write body: %w", err)
	}

	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case response := <-ch:
		var result struct {
			Result json.RawMessage `json:"result"`
			Error  *struct {
				Code    int    `json:"code"`
				Message string `json:"message"`
			} `json:"error"`
		}

		if err := json.Unmarshal(response, &result); err != nil {
			return nil, fmt.Errorf("failed to parse response: %w", err)
		}

		if result.Error != nil {
			return nil, fmt.Errorf("LSP error %d: %s", result.Error.Code, result.Error.Message)
		}

		return result.Result, nil
	}
}

func (c *BaseClient) Initialize(ctx context.Context, rootURI string) error {
	params := InitializeParams{
		ProcessID: os.Getpid(),
		RootURI:   rootURI,
		Capabilities: map[string]interface{}{
			"textDocument": map[string]interface{}{
				"references": map[string]interface{}{
					"dynamicRegistration": false,
				},
				"definition": map[string]interface{}{
					"dynamicRegistration": false,
				},
			},
		},
	}

	result, err := c.Call(ctx, "initialize", params)
	if err != nil {
		return fmt.Errorf("initialize failed: %w", err)
	}

	var initResult InitializeResult
	if err := json.Unmarshal(result, &initResult); err != nil {
		return fmt.Errorf("failed to parse initialize result: %w", err)
	}

	_, err = c.Call(ctx, "initialized", map[string]interface{}{})
	if err != nil {
		return fmt.Errorf("initialized notification failed: %w", err)
	}

	c.initialized = true
	return nil
}

func (c *BaseClient) IsInitialized() bool {
	return c.initialized
}

func (c *BaseClient) Shutdown() error {
	var err error
	c.shutdownOnce.Do(func() {
		ctx := context.Background()
		_, err = c.Call(ctx, "shutdown", nil)

		c.stdin.Close()
		if c.cmd != nil && c.cmd.Process != nil {
			c.cmd.Process.Kill()
			c.cmd.Wait()
		}
	})
	return err
}

func (c *BaseClient) Notify(method string, params interface{}) error {
	notification := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  method,
		"params":  params,
	}

	body, err := json.Marshal(notification)
	if err != nil {
		return fmt.Errorf("failed to marshal notification: %w", err)
	}

	header := fmt.Sprintf("Content-Length: %d\r\n\r\n", len(body))
	if _, err := c.stdin.Write([]byte(header)); err != nil {
		return fmt.Errorf("failed to write header: %w", err)
	}
	if _, err := c.stdin.Write(body); err != nil {
		return fmt.Errorf("failed to write body: %w", err)
	}

	return nil
}

func (c *BaseClient) DidOpen(uri, languageID, content string) error {
	return c.Notify("textDocument/didOpen", map[string]interface{}{
		"textDocument": map[string]interface{}{
			"uri":        uri,
			"languageId": languageID,
			"version":    1,
			"text":       content,
		},
	})
}

func (c *BaseClient) DidClose(uri string) error {
	return c.Notify("textDocument/didClose", map[string]interface{}{
		"textDocument": map[string]interface{}{
			"uri": uri,
		},
	})
}
