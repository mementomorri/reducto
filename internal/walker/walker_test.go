package walker

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/alexkarsten/dehydrate/pkg/models"
)

func TestWalk(t *testing.T) {
	tests := []struct {
		name            string
		setup           func(tmpDir string)
		excludePatterns []string
		includePatterns []string
		expectedFiles   int
		expectedContent map[string]string
	}{
		{
			name: "include all Python files",
			setup: func(tmpDir string) {
				os.WriteFile(filepath.Join(tmpDir, "a.py"), []byte("print('a')"), 0644)
				os.WriteFile(filepath.Join(tmpDir, "b.py"), []byte("print('b')"), 0644)
				os.Mkdir(filepath.Join(tmpDir, "node_modules"), 0755)
				os.WriteFile(filepath.Join(tmpDir, "node_modules", "c.js"), []byte("console.log('c')"), 0644)
			},
			excludePatterns: []string{"node_modules"},
			includePatterns: []string{"*.py"},
			expectedFiles:   2,
		},
		{
			name: "exclude dotfiles",
			setup: func(tmpDir string) {
				os.WriteFile(filepath.Join(tmpDir, "main.py"), []byte("pass"), 0644)
				os.WriteFile(filepath.Join(tmpDir, ".env"), []byte("SECRET=value"), 0644)
				os.WriteFile(filepath.Join(tmpDir, ".gitignore"), []byte("*.pyc"), 0644)
			},
			excludePatterns: []string{},
			includePatterns: []string{"*.py", ".gitignore"},
			expectedFiles:   2,
		},
		{
			name: "exclude binary files",
			setup: func(tmpDir string) {
				os.WriteFile(filepath.Join(tmpDir, "image.png"), []byte{0x89, 0x50, 0x4E, 0x47}, 0644)
				os.WriteFile(filepath.Join(tmpDir, "script.py"), []byte("pass"), 0644)
				os.WriteFile(filepath.Join(tmpDir, "data.pdf"), []byte("%PDF"), 0644)
			},
			excludePatterns: []string{},
			includePatterns: []string{"*.py", "*.pdf"},
			expectedFiles:   1,
		},
		{
			name: "nested directories",
			setup: func(tmpDir string) {
				os.MkdirAll(filepath.Join(tmpDir, "src", "utils"), 0755)
				os.WriteFile(filepath.Join(tmpDir, "main.py"), []byte("pass"), 0644)
				os.WriteFile(filepath.Join(tmpDir, "src", "utils.py"), []byte("pass"), 0644)
				os.WriteFile(filepath.Join(tmpDir, "src", "utils", "helper.py"), []byte("pass"), 0644)
			},
			excludePatterns: []string{},
			includePatterns: []string{"*.py"},
			expectedFiles:   3,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpDir := t.TempDir()
			tt.setup(tmpDir)

			walker := New(tt.excludePatterns, tt.includePatterns)
			files, err := walker.Walk(tmpDir)

			if err != nil {
				t.Fatalf("Walk() error = %v", err)
			}

			if len(files) != tt.expectedFiles {
				t.Errorf("Walk() found %d files, want %d", len(files), tt.expectedFiles)
				for _, f := range files {
					t.Logf("  Found file: %s", f.Path)
				}
			}

			for _, f := range files {
				if f.Hash == "" {
					t.Errorf("File %s has empty hash", f.Path)
				}
				if f.Content == "" {
					t.Errorf("File %s has empty content", f.Path)
				}
			}
		})
	}
}

func TestDetectLanguage(t *testing.T) {
	walker := New(nil, nil)

	tests := []struct {
		path     string
		expected models.Language
	}{
		{"test.py", models.LanguagePython},
		{"script.js", models.LanguageJavaScript},
		{"app.ts", models.LanguageTypeScript},
		{"component.tsx", models.LanguageTypeScript},
		{"main.go", models.LanguageGo},
		{"README.md", models.LanguageUnknown},
		{"data.json", models.LanguageUnknown},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			result := walker.DetectLanguage(tt.path)
			if result != tt.expected {
				t.Errorf("DetectLanguage(%s) = %v, want %v", tt.path, result, tt.expected)
			}
		})
	}
}

func TestCountLines(t *testing.T) {
	walker := New(nil, nil)

	tests := []struct {
		content  string
		expected int
	}{
		{"", 1},
		{"one line", 1},
		{"line1\nline2", 2},
		{"line1\nline2\nline3", 3},
		{"line1\nline2\nline3\n", 4},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := walker.CountLines(tt.content)
			if result != tt.expected {
				t.Errorf("CountLines() = %d, want %d", result, tt.expected)
			}
		})
	}
}

func TestGetProjectStats(t *testing.T) {
	tmpDir := t.TempDir()

	os.WriteFile(filepath.Join(tmpDir, "main.py"), []byte("line1\nline2\nline3"), 0644)
	os.WriteFile(filepath.Join(tmpDir, "app.js"), []byte("line1\nline2"), 0644)
	os.WriteFile(filepath.Join(tmpDir, "README.md"), []byte("doc"), 0644)

	walker := New([]string{}, []string{"*.py", "*.js"})
	stats, err := walker.GetProjectStats(tmpDir)

	if err != nil {
		t.Fatalf("GetProjectStats() error = %v", err)
	}

	if stats.TotalFiles != 2 {
		t.Errorf("TotalFiles = %d, want 2", stats.TotalFiles)
	}

	if stats.TotalLines != 5 {
		t.Errorf("TotalLines = %d, want 5", stats.TotalLines)
	}

	if stats.ByLanguage[models.LanguagePython] != 1 {
		t.Errorf("Python files = %d, want 1", stats.ByLanguage[models.LanguagePython])
	}

	if stats.ByLanguage[models.LanguageJavaScript] != 1 {
		t.Errorf("JavaScript files = %d, want 1", stats.ByLanguage[models.LanguageJavaScript])
	}
}

func TestShouldExcludeDir(t *testing.T) {
	walker := New([]string{"node_modules", "venv", ".git"}, nil)

	tests := []struct {
		path     string
		expected bool
	}{
		{"/project/node_modules", true},
		{"/project/venv", true},
		{"/project/.git", true},
		{"/project/src", false},
		{"/project/tests", false},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			result := walker.shouldExcludeDir(tt.path)
			if result != tt.expected {
				t.Errorf("shouldExcludeDir(%s) = %v, want %v", tt.path, result, tt.expected)
			}
		})
	}
}

func TestShouldExcludeFile(t *testing.T) {
	walker := New(nil, nil)

	tests := []struct {
		path     string
		expected bool
	}{
		{".env", true},
		{".gitignore", false},
		{".env.example", false},
		{"app.min.js", true},
		{"package.lock", true},
		{"go.sum", true},
		{"image.png", true},
		{"data.pdf", true},
		{"script.py", false},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			result := walker.shouldExcludeFile(tt.path)
			if result != tt.expected {
				t.Errorf("shouldExcludeFile(%s) = %v, want %v", tt.path, result, tt.expected)
			}
		})
	}
}

func TestShouldIncludeFile(t *testing.T) {
	tests := []struct {
		name            string
		includePatterns []string
		path            string
		expected        bool
	}{
		{
			name:            "include Python files",
			includePatterns: []string{"*.py"},
			path:            "test.py",
			expected:        true,
		},
		{
			name:            "exclude non-Python files",
			includePatterns: []string{"*.py"},
			path:            "test.js",
			expected:        false,
		},
		{
			name:            "include multiple extensions",
			includePatterns: []string{"*.py", "*.js"},
			path:            "app.js",
			expected:        true,
		},
		{
			name:            "no patterns - include all",
			includePatterns: []string{},
			path:            "any.txt",
			expected:        true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			walker := New(nil, tt.includePatterns)
			result := walker.shouldIncludeFile(tt.path)
			if result != tt.expected {
				t.Errorf("shouldIncludeFile(%s) = %v, want %v", tt.path, result, tt.expected)
			}
		})
	}
}
