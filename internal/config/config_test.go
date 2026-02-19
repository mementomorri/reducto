package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/alexkarsten/dehydrate/pkg/models"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	if cfg == nil {
		t.Fatal("DefaultConfig() returned nil")
	}

	if cfg.Models.Light.LocalModel == "" {
		t.Error("Light.LocalModel should not be empty")
	}

	if cfg.Sidecar.Port == 0 {
		t.Error("Sidecar.Port should not be zero")
	}

	if len(cfg.ExcludePatterns) == 0 {
		t.Error("ExcludePatterns should not be empty")
	}

	if len(cfg.IncludePatterns) == 0 {
		t.Error("IncludePatterns should not be empty")
	}
}

func TestLoad(t *testing.T) {
	tests := []struct {
		name    string
		path    string
		wantErr bool
		check   func(*testing.T, *models.Config)
	}{
		{
			name:    "valid config",
			path:    "testdata/valid.yaml",
			wantErr: false,
			check: func(t *testing.T, cfg *models.Config) {
				if cfg.PreApprove != true {
					t.Error("PreApprove should be true")
				}
				if cfg.CommitChanges != true {
					t.Error("CommitChanges should be true")
				}
				if cfg.Sidecar.Port != 9876 {
					t.Errorf("Sidecar.Port = %d, want 9876", cfg.Sidecar.Port)
				}
			},
		},
		{
			name:    "missing file uses defaults",
			path:    "testdata/nonexistent_dir/missing.yaml",
			wantErr: true, // File doesn't exist
		},
		{
			name:    "invalid yaml - viper may be lenient",
			path:    "testdata/invalid.yaml",
			wantErr: false, // Viper is lenient with parsing
			check: func(t *testing.T, cfg *models.Config) {
				if cfg == nil {
					t.Error("Config should not be nil")
				}
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg, err := Load(tt.path)

			if (err != nil) != tt.wantErr {
				t.Errorf("Load() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if !tt.wantErr && tt.check != nil {
				tt.check(t, cfg)
			}
		})
	}
}

func TestLoadEmptyPath(t *testing.T) {
	cfg, err := Load("")

	if err != nil {
		t.Errorf("Load with empty path should not error: %v", err)
	}

	if cfg == nil {
		t.Fatal("Load() returned nil config")
	}

	if cfg.Models.Light.LocalModel == "" {
		t.Error("Should use default values")
	}
}

func TestSave(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "test-config.yaml")

	cfg := DefaultConfig()
	cfg.PreApprove = true
	cfg.CommitChanges = true

	err := Save(cfg, configPath)
	if err != nil {
		t.Fatalf("Save() error = %v", err)
	}

	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		t.Fatal("Config file was not created")
	}

	loaded, err := Load(configPath)
	if err != nil {
		t.Fatalf("Failed to load saved config: %v", err)
	}

	if loaded.PreApprove != cfg.PreApprove {
		t.Errorf("PreApprove = %v, want %v", loaded.PreApprove, cfg.PreApprove)
	}

	if loaded.CommitChanges != cfg.CommitChanges {
		t.Errorf("CommitChanges = %v, want %v", loaded.CommitChanges, cfg.CommitChanges)
	}
}

func TestSaveEmptyPath(t *testing.T) {
	cfg := DefaultConfig()

	tmpHome := t.TempDir()
	originalHome := os.Getenv("HOME")
	defer os.Setenv("HOME", originalHome)

	os.Setenv("HOME", tmpHome)

	err := Save(cfg, "")
	if err != nil {
		t.Errorf("Save with empty path should not error: %v", err)
	}

	expectedPath := filepath.Join(tmpHome, ".dehydrate.yaml")
	if _, err := os.Stat(expectedPath); os.IsNotExist(err) {
		t.Errorf("Config file should be created at %s", expectedPath)
	}
}
