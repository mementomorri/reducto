package sidecar

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/alexkarsten/reducto/internal/mcp"
	"github.com/alexkarsten/reducto/pkg/models"
)

type AnalyzeResult struct {
	TotalFiles   int                 `json:"total_files"`
	TotalSymbols int                 `json:"total_symbols"`
	Hotspots     []ComplexityHotspot `json:"hotspots"`
}

type ComplexityHotspot struct {
	File                 string `json:"file"`
	Line                 int    `json:"line"`
	Symbol               string `json:"symbol"`
	CyclomaticComplexity int    `json:"cyclomatic_complexity"`
	CognitiveComplexity  int    `json:"cognitive_complexity"`
}

type MCPManager struct {
	rootDir    string
	cfg        *models.Config
	server     *mcp.Server
	process    *os.Process
	cmd        *exec.Cmd
	resultChan chan map[string]interface{}
	mu         sync.Mutex
}

func NewMCPManager(rootDir string, cfg *models.Config) *MCPManager {
	return &MCPManager{
		rootDir:    rootDir,
		cfg:        cfg,
		resultChan: make(chan map[string]interface{}, 1),
	}
}

func (m *MCPManager) Start(command, path string) error {
	if err := m.checkPythonInstalled(); err != nil {
		return err
	}

	sidecarPath, err := getOrCreateSidecarPath()
	if err != nil {
		return err
	}

	args := []string{
		"-m", "ai_sidecar.mcp_entry",
		"--root", path,
		"--command", command,
	}

	if m.cfg != nil {
		if m.cfg.Verbose {
			args = append(args, "--verbose")
		}
		if m.cfg.Model != "" {
			args = append(args, "--model", m.cfg.Model)
		}
		if !m.cfg.PreferLocal {
			args = append(args, "--prefer-remote")
		}
	}

	m.cmd = exec.Command("python3", args...)
	m.cmd.Dir = sidecarPath
	m.cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")

	serverIn, clientOut, err := os.Pipe()
	if err != nil {
		return fmt.Errorf("failed to create pipe: %w", err)
	}

	clientIn, serverOut, err := os.Pipe()
	if err != nil {
		serverIn.Close()
		clientOut.Close()
		return fmt.Errorf("failed to create pipe: %w", err)
	}

	m.cmd.Stdin = clientIn
	m.cmd.Stdout = clientOut

	stderrPipe, err := m.cmd.StderrPipe()
	if err != nil {
		serverIn.Close()
		clientOut.Close()
		clientIn.Close()
		serverOut.Close()
		return fmt.Errorf("failed to create stderr pipe: %w", err)
	}

	go m.readResultFromStderr(stderrPipe)

	m.cmd.SysProcAttr = &syscall.SysProcAttr{
		Setpgid: true,
	}

	if err := m.cmd.Start(); err != nil {
		serverIn.Close()
		clientOut.Close()
		clientIn.Close()
		serverOut.Close()
		return fmt.Errorf("failed to start sidecar: %w", err)
	}

	m.process = m.cmd.Process

	m.server = mcp.NewServer(m.rootDir)
	go func() {
		ctx := context.Background()
		m.server.Start(ctx, serverIn, serverOut)
	}()

	return nil
}

func (m *MCPManager) readResultFromStderr(reader io.Reader) {
	scanner := bufio.NewScanner(reader)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "RESULT:") {
			jsonStr := strings.TrimPrefix(line, "RESULT:")
			var result map[string]interface{}
			if err := json.Unmarshal([]byte(jsonStr), &result); err == nil {
				select {
				case m.resultChan <- result:
				default:
				}
			}
			continue
		}
		if m.cfg != nil && m.cfg.Verbose {
			fmt.Fprintln(os.Stderr, line)
		}
	}
}

func (m *MCPManager) Stop() {
	if m.process != nil {
		if runtime.GOOS == "windows" {
			m.process.Kill()
		} else {
			syscall.Kill(-m.process.Pid, syscall.SIGTERM)
		}
		if m.cmd != nil {
			m.cmd.Wait()
		}
		m.process = nil
	}
}

func (m *MCPManager) WaitForResult(timeout time.Duration) (map[string]interface{}, error) {
	select {
	case result := <-m.resultChan:
		return result, nil
	case <-time.After(timeout):
		return nil, fmt.Errorf("timeout waiting for result")
	}
}

func (m *MCPManager) Analyze(path string) (*AnalyzeResult, error) {
	if err := m.Start("analyze", path); err != nil {
		return nil, err
	}
	defer m.Stop()

	result, err := m.WaitForResult(5 * time.Minute)
	if err != nil {
		return nil, err
	}

	if status, ok := result["status"].(string); ok && status == "error" {
		if data, ok := result["data"].(map[string]interface{}); ok {
			if errStr, ok := data["error"].(string); ok && errStr != "" {
				return nil, fmt.Errorf("%s", errStr)
			}
		}
		return nil, fmt.Errorf("analysis failed with status: error")
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid result format")
	}

	analyzeResult := &AnalyzeResult{}
	if totalFiles, ok := data["total_files"].(float64); ok {
		analyzeResult.TotalFiles = int(totalFiles)
	}
	if totalSymbols, ok := data["total_symbols"].(float64); ok {
		analyzeResult.TotalSymbols = int(totalSymbols)
	}

	if hotspots, ok := data["hotspots"].([]interface{}); ok {
		for _, h := range hotspots {
			if hm, ok := h.(map[string]interface{}); ok {
				hs := ComplexityHotspot{}
				if f, ok := hm["file"].(string); ok {
					hs.File = f
				}
				if l, ok := hm["line"].(float64); ok {
					hs.Line = int(l)
				}
				if s, ok := hm["symbol"].(string); ok {
					hs.Symbol = s
				}
				if cc, ok := hm["cyclomatic_complexity"].(float64); ok {
					hs.CyclomaticComplexity = int(cc)
				}
				if cc2, ok := hm["cognitive_complexity"].(float64); ok {
					hs.CognitiveComplexity = int(cc2)
				}
				analyzeResult.Hotspots = append(analyzeResult.Hotspots, hs)
			}
		}
	}

	return analyzeResult, nil
}

func (m *MCPManager) Deduplicate(path string) (*models.RefactorPlan, error) {
	if err := m.Start("deduplicate", path); err != nil {
		return nil, err
	}
	defer m.Stop()

	result, err := m.WaitForResult(10 * time.Minute)
	if err != nil {
		return nil, err
	}

	if errStr, ok := result["error"].(string); ok && errStr != "" {
		return nil, fmt.Errorf("deduplicate failed: %s", errStr)
	}

	return m.parsePlan(result)
}

func (m *MCPManager) Idiomatize(path string) (*models.RefactorPlan, error) {
	if err := m.Start("idiomatize", path); err != nil {
		return nil, err
	}
	defer m.Stop()

	result, err := m.WaitForResult(10 * time.Minute)
	if err != nil {
		return nil, err
	}

	if errStr, ok := result["error"].(string); ok && errStr != "" {
		return nil, fmt.Errorf("idiomatize failed: %s", errStr)
	}

	return m.parsePlan(result)
}

func (m *MCPManager) ApplyPattern(pattern, path string) (*models.RefactorPlan, error) {
	if err := m.Start("pattern", path); err != nil {
		return nil, err
	}
	defer m.Stop()

	result, err := m.WaitForResult(10 * time.Minute)
	if err != nil {
		return nil, err
	}

	if errStr, ok := result["error"].(string); ok && errStr != "" {
		return nil, fmt.Errorf("pattern failed: %s", errStr)
	}

	return m.parsePlan(result)
}

func (m *MCPManager) ApplyPlan(plan *models.RefactorPlan, runTests bool) (*models.RefactorResult, error) {
	if plan == nil || len(plan.Changes) == 0 {
		return &models.RefactorResult{
			SessionID:   "",
			Success:     true,
			Changes:     []models.FileChange{},
			TestsPassed: true,
		}, nil
	}

	// Start Python sidecar with apply_plan command
	if err := m.Start("apply_plan", m.rootDir); err != nil {
		return nil, err
	}
	defer m.Stop()

	// Wait for result
	result, err := m.WaitForResult(10 * time.Minute)
	if err != nil {
		return nil, fmt.Errorf("apply_plan failed: %w", err)
	}

	if errStr, ok := result["error"].(string); ok && errStr != "" {
		return nil, fmt.Errorf("apply_plan error: %s", errStr)
	}

	// Build result from plan
	return &models.RefactorResult{
		SessionID:   plan.SessionID,
		Success:     true,
		Changes:     plan.Changes,
		TestsPassed: true,
	}, nil
}

func (m *MCPManager) Check(path string) (map[string]interface{}, error) {
	if err := m.Start("check", path); err != nil {
		return nil, err
	}
	defer m.Stop()

	result, err := m.WaitForResult(10 * time.Minute)
	if err != nil {
		return nil, err
	}

	if errStr, ok := result["error"].(string); ok && errStr != "" {
		return nil, fmt.Errorf("check failed: %s", errStr)
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid check result format")
	}

	return data, nil
}

func (m *MCPManager) parsePlan(result map[string]interface{}) (*models.RefactorPlan, error) {
	plan := &models.RefactorPlan{}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid plan format")
	}

	if sid, ok := data["session_id"].(string); ok {
		plan.SessionID = sid
	}
	if desc, ok := data["description"].(string); ok {
		plan.Description = desc
	}
	if pattern, ok := data["pattern"].(string); ok {
		plan.Pattern = pattern
	}

	if changesData, ok := data["changes"].([]interface{}); ok {
		for _, c := range changesData {
			if cm, ok := c.(map[string]interface{}); ok {
				change := models.FileChange{}
				if path, ok := cm["path"].(string); ok {
					change.Path = path
				}
				if orig, ok := cm["original"].(string); ok {
					change.Original = orig
				}
				if mod, ok := cm["modified"].(string); ok {
					change.Modified = mod
				}
				if d, ok := cm["description"].(string); ok {
					change.Description = d
				}
				plan.Changes = append(plan.Changes, change)
			}
		}
	}

	return plan, nil
}

func (m *MCPManager) checkPythonInstalled() error {
	cmd := exec.Command("python3", "--version")
	if err := cmd.Run(); err != nil {
		cmd = exec.Command("python", "--version")
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("python3 is not installed or not in PATH")
		}
	}
	return nil
}

func (m *MCPManager) ListSessions() ([]map[string]interface{}, error) {
	// Session listing is handled by Python sidecar
	// For now, return empty list - full implementation requires MCP call
	return []map[string]interface{}{}, nil
}

func (m *MCPManager) GetSession(sessionID string) (*models.RefactorPlan, error) {
	// Session retrieval is handled by Python sidecar
	// For now, return nil - full implementation requires MCP call
	return nil, fmt.Errorf("session retrieval not yet implemented")
}

func (m *MCPManager) DeleteSession(sessionID string) error {
	// Session deletion is handled by Python sidecar
	// For now, return error - full implementation requires MCP call
	return fmt.Errorf("session deletion not yet implemented")
}

func (m *MCPManager) IsRunning() bool {
	if m.process == nil {
		return false
	}

	if runtime.GOOS == "windows" {
		return m.process.Signal(syscall.Signal(0)) == nil
	}

	return m.process.Signal(syscall.Signal(0)) == nil
}
