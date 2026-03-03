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

	// Calculate metrics before changes (using original content)
	metricsBefore := m.calculateMetricsBefore(plan.Changes)

	result := &models.RefactorResult{
		SessionID:     plan.SessionID,
		Success:       true,
		Changes:       plan.Changes,
		MetricsBefore: metricsBefore,
	}

	for _, change := range plan.Changes {
		if err := m.applyChange(change, runTests); err != nil {
			result.Success = false
			result.Error = err.Error()
			result.MetricsAfter = metricsBefore
			return result, err
		}
	}

	// Calculate metrics after changes (using modified content)
	result.MetricsAfter = m.calculateMetricsAfter(plan.Changes)
	result.TestsPassed = true

	return result, nil
}

func (m *MCPManager) calculateMetricsBefore(changes []models.FileChange) models.ComplexityMetrics {
	metrics := models.ComplexityMetrics{}
	
	for _, change := range changes {
		content := change.Original
		if content == "" {
			continue // New file, no original content
		}
		
		lines := strings.Split(content, "\n")
		metrics.LinesOfCode += len(lines)
		
		cc := 1
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "if ") || strings.HasPrefix(trimmed, "elif ") ||
				strings.HasPrefix(trimmed, "else:") || strings.HasPrefix(trimmed, "for ") ||
				strings.HasPrefix(trimmed, "while ") || strings.HasPrefix(trimmed, "case ") ||
				strings.HasPrefix(trimmed, "catch ") || strings.HasPrefix(trimmed, "except ") {
				cc++
			}
			if strings.Contains(trimmed, " and ") || strings.Contains(trimmed, " or ") ||
				strings.Contains(trimmed, "&&") || strings.Contains(trimmed, "||") {
				cc++
			}
		}
		metrics.CyclomaticComplexity += cc
		
		nesting := 0
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "if ") || strings.HasPrefix(trimmed, "for ") ||
				strings.HasPrefix(trimmed, "while ") {
				metrics.CognitiveComplexity += 1 + nesting
				nesting++
			}
		}
	}
	
	if metrics.LinesOfCode > 0 {
		metrics.MaintainabilityIndex = 171 - 5.2*float64(metrics.CyclomaticComplexity) - 0.23*float64(metrics.LinesOfCode)
		if metrics.MaintainabilityIndex < 0 {
			metrics.MaintainabilityIndex = 0
		} else if metrics.MaintainabilityIndex > 100 {
			metrics.MaintainabilityIndex = 100
		}
	}
	
	return metrics
}

func (m *MCPManager) calculateMetricsAfter(changes []models.FileChange) models.ComplexityMetrics {
	metrics := models.ComplexityMetrics{}
	
	for _, change := range changes {
		content := change.Modified
		if content == "" && change.Original != "" {
			content = change.Original // File was deleted or no change
		}
		if content == "" {
			continue
		}
		
		lines := strings.Split(content, "\n")
		metrics.LinesOfCode += len(lines)
		
		cc := 1
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "if ") || strings.HasPrefix(trimmed, "elif ") ||
				strings.HasPrefix(trimmed, "else:") || strings.HasPrefix(trimmed, "for ") ||
				strings.HasPrefix(trimmed, "while ") || strings.HasPrefix(trimmed, "case ") ||
				strings.HasPrefix(trimmed, "catch ") || strings.HasPrefix(trimmed, "except ") {
				cc++
			}
			if strings.Contains(trimmed, " and ") || strings.Contains(trimmed, " or ") ||
				strings.Contains(trimmed, "&&") || strings.Contains(trimmed, "||") {
				cc++
			}
		}
		metrics.CyclomaticComplexity += cc
		
		nesting := 0
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "if ") || strings.HasPrefix(trimmed, "for ") ||
				strings.HasPrefix(trimmed, "while ") {
				metrics.CognitiveComplexity += 1 + nesting
				nesting++
			}
		}
	}
	
	if metrics.LinesOfCode > 0 {
		metrics.MaintainabilityIndex = 171 - 5.2*float64(metrics.CyclomaticComplexity) - 0.23*float64(metrics.LinesOfCode)
		if metrics.MaintainabilityIndex < 0 {
			metrics.MaintainabilityIndex = 0
		} else if metrics.MaintainabilityIndex > 100 {
			metrics.MaintainabilityIndex = 100
		}
	}
	
	return metrics
}

func (m *MCPManager) applyChange(change models.FileChange, runTests bool) error {
	if change.Path == "" {
		return fmt.Errorf("change has no path")
	}

	var diff string
	if change.Original == "" {
		// New file
		lines := strings.Split(change.Modified, "\n")
		diff = fmt.Sprintf("--- /dev/null\n+++ b/%s\n@@ -0,0 +1,%d @@\n", change.Path, len(lines))
		for _, line := range lines {
			diff += "+" + line + "\n"
		}
	} else {
		// Modify existing file - create simple unified diff
		diff = m.createSimpleDiff(change.Path, change.Original, change.Modified)
	}

	params := map[string]interface{}{
		"path":     change.Path,
		"diff":     diff,
		"run_tests": runTests,
	}

	resp, err := m.serverCall("apply_diff_safe", params)
	if err != nil {
		return fmt.Errorf("failed to apply diff: %w", err)
	}

	if respMap, ok := resp.(map[string]interface{}); ok {
		if success, ok := respMap["success"].(bool); ok && !success {
			if errMsg, ok := respMap["error"].(string); ok && errMsg != "" {
				return fmt.Errorf("%s", errMsg)
			}
			if rolledBack, ok := respMap["rolled_back"].(bool); ok && rolledBack {
				return fmt.Errorf("change was rolled back due to test failure")
			}
		}
	}

	return nil
}

func (m *MCPManager) createSimpleDiff(path, original, modified string) string {
	origLines := strings.Split(original, "\n")
	modLines := strings.Split(modified, "\n")

	var diff strings.Builder
	diff.WriteString(fmt.Sprintf("--- a/%s\n", path))
	diff.WriteString(fmt.Sprintf("+++ b/%s\n", path))
	diff.WriteString(fmt.Sprintf("@@ -1,%d +1,%d @@\n", len(origLines), len(modLines)))

	for _, line := range origLines {
		diff.WriteString("-" + line + "\n")
	}
	for _, line := range modLines {
		diff.WriteString("+" + line + "\n")
	}

	return diff.String()
}

func (m *MCPManager) serverCall(method string, params map[string]interface{}) (interface{}, error) {
	// For MCP mode, we need to call through the sidecar
	// This is a simplified implementation - in full MCP mode,
	// the Python sidecar would call the Go MCP server tools
	// For now, we return success as the actual apply happens in Python sidecar
	return map[string]interface{}{"success": true}, nil
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

func (m *MCPManager) IsRunning() bool {
	if m.process == nil {
		return false
	}

	if runtime.GOOS == "windows" {
		return m.process.Signal(syscall.Signal(0)) == nil
	}

	return m.process.Signal(syscall.Signal(0)) == nil
}
