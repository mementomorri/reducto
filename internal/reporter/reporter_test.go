package reporter

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/alexkarsten/reducto/pkg/models"
)

func TestNew(t *testing.T) {
	cfg := &models.Config{}
	r := New(cfg)

	if r == nil {
		t.Fatal("New returned nil")
	}
	if r.cfg != cfg {
		t.Error("config not set correctly")
	}
	if r.outputDir != ".reducto" {
		t.Errorf("expected outputDir .reducto, got %s", r.outputDir)
	}
}

func TestGenerate(t *testing.T) {
	tmpDir := t.TempDir()

	cfg := &models.Config{}
	r := New(cfg)
	r.outputDir = filepath.Join(tmpDir, ".reducto")

	result := &models.RefactorResult{
		SessionID: "test-session-123",
		Changes: []models.FileChange{
			{
				Path:        "test.py",
				Description: "Refactored function",
				Original:    "def old():\n    pass\n",
				Modified:    "def new():\n    pass\n",
			},
		},
		MetricsBefore: models.ComplexityMetrics{
			LinesOfCode:          100,
			CyclomaticComplexity: 10,
			CognitiveComplexity:  15,
			MaintainabilityIndex: 70.0,
		},
		MetricsAfter: models.ComplexityMetrics{
			LinesOfCode:          80,
			CyclomaticComplexity: 8,
			CognitiveComplexity:  12,
			MaintainabilityIndex: 75.0,
		},
	}

	err := r.Generate(result)
	if err != nil {
		t.Fatalf("Generate returned error: %v", err)
	}

	expectedPath := filepath.Join(tmpDir, ".reducto", "reducto-report-test-session-123.md")
	if _, err := os.Stat(expectedPath); os.IsNotExist(err) {
		t.Errorf("expected report file at %s", expectedPath)
	}

	content, err := os.ReadFile(expectedPath)
	if err != nil {
		t.Fatalf("failed to read report: %v", err)
	}

	contentStr := string(content)
	if !strings.Contains(contentStr, "test-session-123") {
		t.Error("report should contain session ID")
	}
	if !strings.Contains(contentStr, "100") || !strings.Contains(contentStr, "80") {
		t.Error("report should contain LOC before and after")
	}
}

func TestGenerateBaseline(t *testing.T) {
	tmpDir := t.TempDir()

	cfg := &models.Config{}
	r := New(cfg)
	r.outputDir = filepath.Join(tmpDir, ".reducto")

	result := &BaselineResult{
		TotalFiles:   10,
		TotalSymbols: 50,
		Hotspots: []ComplexityHotspot{
			{
				File:                 "complex.py",
				Line:                 10,
				Symbol:               "process_data",
				CyclomaticComplexity: 15,
				CognitiveComplexity:  20,
			},
		},
	}

	err := r.GenerateBaseline(result)
	if err != nil {
		t.Fatalf("GenerateBaseline returned error: %v", err)
	}

	entries, err := os.ReadDir(r.outputDir)
	if err != nil {
		t.Fatalf("failed to read output dir: %v", err)
	}

	found := false
	for _, entry := range entries {
		if strings.HasPrefix(entry.Name(), "reducto-baseline-") {
			found = true
			content, err := os.ReadFile(filepath.Join(r.outputDir, entry.Name()))
			if err != nil {
				t.Fatalf("failed to read baseline: %v", err)
			}

			contentStr := string(content)
			if !strings.Contains(contentStr, "10") {
				t.Error("baseline should contain total files")
			}
			if !strings.Contains(contentStr, "complex.py") {
				t.Error("baseline should contain hotspot file")
			}
			break
		}
	}

	if !found {
		t.Error("expected baseline report file to be created")
	}
}

func TestFormatBaselineMarkdown(t *testing.T) {
	cfg := &models.Config{}
	r := New(cfg)

	result := &BaselineResult{
		TotalFiles:   5,
		TotalSymbols: 25,
		Hotspots: []ComplexityHotspot{
			{
				File:                 "test.py",
				Line:                 10,
				Symbol:               "test_func",
				CyclomaticComplexity: 8,
				CognitiveComplexity:  10,
			},
		},
	}

	content := r.formatBaselineMarkdown("test-session", result)

	if !strings.Contains(content, "# reducto Baseline Analysis Report") {
		t.Error("should contain title")
	}
	if !strings.Contains(content, "| Total Files | 5 |") {
		t.Error("should contain total files")
	}
	if !strings.Contains(content, "| Total Symbols | 25 |") {
		t.Error("should contain total symbols")
	}
	if !strings.Contains(content, "test.py") {
		t.Error("should contain hotspot file")
	}
	if !strings.Contains(content, "test_func") {
		t.Error("should contain hotspot symbol")
	}
}

func TestFormatMarkdown(t *testing.T) {
	cfg := &models.Config{}
	r := New(cfg)

	report := &models.Report{
		SessionID:     "test-123",
		GeneratedAt:   time.Now(),
		LOCBefore:     100,
		LOCAfter:      80,
		LOCReduced:    20,
		FilesModified: []string{"test.py", "main.py"},
		MetricsDelta: models.MetricsDelta{
			CyclomaticComplexityDelta: 2,
			CognitiveComplexityDelta:  3,
			MaintainabilityIndexDelta: 5.0,
		},
	}

	result := &models.RefactorResult{
		SessionID: "test-123",
		Changes: []models.FileChange{
			{
				Path:        "test.py",
				Description: "Simplified function",
				Original:    "def old():\n    return 1\n",
				Modified:    "def new():\n    return 1\n",
			},
		},
		MetricsBefore: models.ComplexityMetrics{
			LinesOfCode:          100,
			CyclomaticComplexity: 10,
			CognitiveComplexity:  15,
			MaintainabilityIndex: 70.0,
		},
		MetricsAfter: models.ComplexityMetrics{
			LinesOfCode:          80,
			CyclomaticComplexity: 8,
			CognitiveComplexity:  12,
			MaintainabilityIndex: 75.0,
		},
	}

	content := r.formatMarkdown(report, result)

	if !strings.Contains(content, "# reducto Compression Report") {
		t.Error("should contain title")
	}
	if !strings.Contains(content, "test-123") {
		t.Error("should contain session ID")
	}
	if !strings.Contains(content, "test.py") {
		t.Error("should contain modified file")
	}
	if !strings.Contains(content, "Simplified function") {
		t.Error("should contain change description")
	}
}

func TestExtractModifiedFiles(t *testing.T) {
	cfg := &models.Config{}
	r := New(cfg)

	changes := []models.FileChange{
		{Path: "test.py"},
		{Path: "main.py"},
		{Path: "test.py"},
		{Path: "utils.py"},
	}

	files := r.extractModifiedFiles(changes)

	if len(files) != 3 {
		t.Errorf("expected 3 unique files, got %d", len(files))
	}

	seen := make(map[string]bool)
	for _, f := range files {
		if seen[f] {
			t.Errorf("duplicate file %s in result", f)
		}
		seen[f] = true
	}
}

func TestGenerateDiff(t *testing.T) {
	cfg := &models.Config{}
	r := New(cfg)

	tests := []struct {
		name     string
		original string
		modified string
		wantDiff bool
	}{
		{
			name:     "identical content",
			original: "line1\nline2\n",
			modified: "line1\nline2\n",
			wantDiff: false,
		},
		{
			name:     "modified line",
			original: "line1\nline2\n",
			modified: "line1\nmodified\n",
			wantDiff: true,
		},
		{
			name:     "added line",
			original: "line1\n",
			modified: "line1\nline2\n",
			wantDiff: true,
		},
		{
			name:     "removed line",
			original: "line1\nline2\n",
			modified: "line1\n",
			wantDiff: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			diff := r.generateDiff(tt.original, tt.modified)

			if tt.wantDiff {
				if !strings.Contains(diff, "-") && !strings.Contains(diff, "+") {
					t.Error("expected diff to contain changes")
				}
			} else {
				if strings.Contains(diff, "-") || strings.Contains(diff, "+") {
					t.Error("expected no diff for identical content")
				}
			}
		})
	}
}

func TestLoad(t *testing.T) {
	t.Run("no reports", func(t *testing.T) {
		tmpDir := t.TempDir()

		cfg := &models.Config{}
		r := New(cfg)
		r.outputDir = tmpDir

		err := r.Load("")
		if err == nil {
			t.Error("expected error when no reports exist")
		}
	})

	t.Run("with report", func(t *testing.T) {
		tmpDir := t.TempDir()

		reportContent := "# reducto Compression Report\n\nSession: test-123\n"
		reportPath := filepath.Join(tmpDir, "reducto-report-test-123.md")
		err := os.WriteFile(reportPath, []byte(reportContent), 0644)
		if err != nil {
			t.Fatalf("failed to create test report: %v", err)
		}

		cfg := &models.Config{}
		r := New(cfg)
		r.outputDir = tmpDir

		err = r.Load("test-123")
		if err != nil {
			t.Fatalf("Load returned error: %v", err)
		}
	})

	t.Run("latest report", func(t *testing.T) {
		tmpDir := t.TempDir()

		oldReport := "# reducto Compression Report\n\nSession: old\n"
		oldPath := filepath.Join(tmpDir, "reducto-report-old.md")
		err := os.WriteFile(oldPath, []byte(oldReport), 0644)
		if err != nil {
			t.Fatalf("failed to create old report: %v", err)
		}

		time.Sleep(10 * time.Millisecond)

		newReport := "# reducto Compression Report\n\nSession: new\n"
		newPath := filepath.Join(tmpDir, "reducto-report-new.md")
		err = os.WriteFile(newPath, []byte(newReport), 0644)
		if err != nil {
			t.Fatalf("failed to create new report: %v", err)
		}

		cfg := &models.Config{}
		r := New(cfg)
		r.outputDir = tmpDir

		err = r.Load("")
		if err != nil {
			t.Fatalf("Load returned error: %v", err)
		}
	})
}

func TestGenerateDryRun(t *testing.T) {
	tmpDir := t.TempDir()

	cfg := &models.Config{}
	r := New(cfg)
	r.outputDir = filepath.Join(tmpDir, ".reducto")

	plan := &models.RefactorPlan{
		SessionID: "dry-run-test-123",
		Changes: []models.FileChange{
			{
				Path:        "utils/new_file.py",
				Description: "Extract duplicate function 'process_data' found in 3 files",
				Original:    "",
				Modified:    "def process_data(data):\n    return data.strip()\n",
			},
			{
				Path:        "src/main.py",
				Description: "Remove duplicate code, use extracted function",
				Original:    "def process_data(data):\n    return data.strip()\n",
				Modified:    "from utils.new_file import process_data\n",
			},
		},
		Description: "Found 3 duplicate code blocks",
	}

	err := r.GenerateDryRun(plan, "deduplicate", "/project")
	if err != nil {
		t.Fatalf("GenerateDryRun returned error: %v", err)
	}

	expectedPath := filepath.Join(tmpDir, ".reducto", "reducto-dryrun-dry-run-test-123.md")
	if _, err := os.Stat(expectedPath); os.IsNotExist(err) {
		t.Errorf("expected dry-run report file at %s", expectedPath)
	}

	content, err := os.ReadFile(expectedPath)
	if err != nil {
		t.Fatalf("failed to read dry-run report: %v", err)
	}

	contentStr := string(content)
	if !strings.Contains(contentStr, "DRY RUN MODE") {
		t.Error("dry-run report should contain DRY RUN MODE")
	}
	if !strings.Contains(contentStr, "dry-run-test-123") {
		t.Error("dry-run report should contain session ID")
	}
	if !strings.Contains(contentStr, "deduplicate") {
		t.Error("dry-run report should contain command name")
	}
	if !strings.Contains(contentStr, "utils/new_file.py") {
		t.Error("dry-run report should contain file paths")
	}
	if !strings.Contains(contentStr, "Proposed Changes") {
		t.Error("dry-run report should have Proposed Changes section")
	}
}

func TestFormatDryRunMarkdown(t *testing.T) {
	cfg := &models.Config{}
	r := New(cfg)

	t.Run("with changes", func(t *testing.T) {
		plan := &models.RefactorPlan{
			SessionID: "test-session",
			Changes: []models.FileChange{
				{
					Path:        "test.py",
					Description: "Test change",
					Original:    "old code\n",
					Modified:    "new code\n",
				},
			},
			Description: "Test plan",
		}

		content := r.formatDryRunMarkdown(plan, "deduplicate", "/test/path")

		if !strings.Contains(content, "# reducto Dry-Run Report") {
			t.Error("should contain title")
		}
		if !strings.Contains(content, "**DRY RUN MODE**") {
			t.Error("should contain dry-run warning")
		}
		if !strings.Contains(content, "deduplicate") {
			t.Error("should contain command name")
		}
		if !strings.Contains(content, "/test/path") {
			t.Error("should contain path")
		}
		if !strings.Contains(content, "test-session") {
			t.Error("should contain session ID")
		}
		if !strings.Contains(content, "Proposed Changes") {
			t.Error("should contain proposed changes section")
		}
		if !strings.Contains(content, "test.py") {
			t.Error("should contain file path")
		}
	})

	t.Run("with no changes", func(t *testing.T) {
		plan := &models.RefactorPlan{
			SessionID:   "empty-session",
			Changes:     []models.FileChange{},
			Description: "No changes found",
		}

		content := r.formatDryRunMarkdown(plan, "idiomatize", "/empty")

		if !strings.Contains(content, "No changes proposed") {
			t.Error("should indicate no changes")
		}
	})

	t.Run("new file creation", func(t *testing.T) {
		plan := &models.RefactorPlan{
			SessionID: "new-file-session",
			Changes: []models.FileChange{
				{
					Path:        "utils/new.py",
					Description: "Create new utility file",
					Original:    "",
					Modified:    "def helper():\n    pass\n",
				},
			},
			Description: "Create new file",
		}

		content := r.formatDryRunMarkdown(plan, "pattern", "/project")

		if !strings.Contains(content, "--- /dev/null") {
			t.Error("should show /dev/null for new files")
		}
		if !strings.Contains(content, "+++ b/utils/new.py") {
			t.Error("should show new file path")
		}
	})

	t.Run("file deletion", func(t *testing.T) {
		plan := &models.RefactorPlan{
			SessionID: "delete-session",
			Changes: []models.FileChange{
				{
					Path:        "old_file.py",
					Description: "Remove obsolete file",
					Original:    "old content\n",
					Modified:    "",
				},
			},
			Description: "Delete file",
		}

		content := r.formatDryRunMarkdown(plan, "deduplicate", "/project")

		if !strings.Contains(content, "--- a/old_file.py") {
			t.Error("should show original file path for deletion")
		}
		if !strings.Contains(content, "+++ /dev/null") {
			t.Error("should show /dev/null for deleted files")
		}
	})
}

func TestEstimateLOCChange(t *testing.T) {
	cfg := &models.Config{}
	r := New(cfg)

	tests := []struct {
		name        string
		changes     []models.FileChange
		wantPattern string
	}{
		{
			name:        "no changes",
			changes:     []models.FileChange{},
			wantPattern: "0",
		},
		{
			name: "only additions",
			changes: []models.FileChange{
				{Original: "", Modified: "line1\nline2\n"},
			},
			wantPattern: "+",
		},
		{
			name: "only removals",
			changes: []models.FileChange{
				{Original: "line1\nline2\n", Modified: ""},
			},
			wantPattern: "-",
		},
		{
			name: "mixed changes",
			changes: []models.FileChange{
				{Original: "", Modified: "new1\n"},
				{Original: "old1\nold2\n", Modified: ""},
			},
			wantPattern: "/",
		},
		{
			name: "modification",
			changes: []models.FileChange{
				{Original: "line1\nline2\nline3\n", Modified: "new1\nnew2\n"},
			},
			wantPattern: "-",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := r.estimateLOCChange(tt.changes)
			if !strings.Contains(result, tt.wantPattern) {
				t.Errorf("expected pattern %q in result %q", tt.wantPattern, result)
			}
		})
	}
}
