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

	if errStr, ok := result["error"].(string); ok && errStr != "" {
		return nil, fmt.Errorf("analyze failed: %s", errStr)
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

func (m *MCPManager) ApplyPlan(sessionID string) (*models.RefactorResult, error) {
	return nil, fmt.Errorf("ApplyPlan not yet implemented for MCP mode")
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

func (m *MCPManager) IsRunning() bool {
	if m.process == nil {
		return false
	}

	if runtime.GOOS == "windows" {
		return m.process.Signal(syscall.Signal(0)) == nil
	}

	return m.process.Signal(syscall.Signal(0)) == nil
}
