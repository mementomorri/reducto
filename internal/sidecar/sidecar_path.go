package sidecar

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"sync"
)

var (
	embeddedFS     fs.FS
	embeddedOnce   sync.Once
	extractedPath  string
	extractErr     error
	sidecarVersion = "0.1.0"
)

func SetEmbeddedFS(fsys fs.FS) {
	embeddedFS = fsys
}

func getOrCreateSidecarPath() (string, error) {
	embeddedOnce.Do(func() {
		if embeddedFS != nil {
			extractedPath, extractErr = extractEmbeddedSidecar()
		} else {
			extractedPath, extractErr = findLocalSidecar()
		}
	})
	return extractedPath, extractErr
}

func extractEmbeddedSidecar() (string, error) {
	dataDir, err := getDataDir()
	if err != nil {
		return "", fmt.Errorf("failed to get data directory: %w", err)
	}

	sidecarDir := filepath.Join(dataDir, "sidecar")
	versionFile := filepath.Join(sidecarDir, ".version")

	if storedVersion, err := os.ReadFile(versionFile); err == nil {
		if string(storedVersion) == sidecarVersion {
			if validateSidecarDir(sidecarDir) {
				return sidecarDir, nil
			}
		}
	}

	if err := os.RemoveAll(sidecarDir); err != nil && !os.IsNotExist(err) {
		return "", fmt.Errorf("failed to remove old sidecar: %w", err)
	}

	if err := os.MkdirAll(sidecarDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create sidecar directory: %w", err)
	}

	if err := copyFS(embeddedFS, sidecarDir); err != nil {
		return "", fmt.Errorf("failed to extract sidecar: %w", err)
	}

	if err := os.WriteFile(versionFile, []byte(sidecarVersion), 0644); err != nil {
		return "", fmt.Errorf("failed to write version file: %w", err)
	}

	return sidecarDir, nil
}

func findLocalSidecar() (string, error) {
	candidates := []string{
		"python",
		"../python",
		"../../python",
	}

	execPath, err := os.Executable()
	if err == nil {
		execDir := filepath.Dir(execPath)
		candidates = append(candidates,
			filepath.Join(execDir, "python"),
			filepath.Join(execDir, "../python"),
			filepath.Join(execDir, "../../python"),
		)
	}

	for _, candidate := range candidates {
		absPath, err := filepath.Abs(candidate)
		if err != nil {
			continue
		}
		if validateSidecarDir(absPath) {
			return absPath, nil
		}
	}

	return "", fmt.Errorf("could not find ai_sidecar module; ensure Python sidecar is installed")
}

func validateSidecarDir(path string) bool {
	initPath := filepath.Join(path, "ai_sidecar", "__init__.py")
	if _, err := os.Stat(initPath); err == nil {
		return true
	}
	mainPath := filepath.Join(path, "ai_sidecar", "mcp_entry.py")
	if _, err := os.Stat(mainPath); err == nil {
		return true
	}
	return false
}

func getDataDir() (string, error) {
	var baseDir string

	if xdgDataHome := os.Getenv("XDG_DATA_HOME"); xdgDataHome != "" {
		baseDir = xdgDataHome
	} else if runtime.GOOS == "windows" {
		baseDir = os.Getenv("APPDATA")
		if baseDir == "" {
			baseDir = filepath.Join(os.Getenv("USERPROFILE"), "AppData", "Roaming")
		}
	} else if runtime.GOOS == "darwin" {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		baseDir = filepath.Join(homeDir, "Library", "Application Support")
	} else {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		baseDir = filepath.Join(homeDir, ".local", "share")
	}

	dataDir := filepath.Join(baseDir, "reducto")
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create data directory: %w", err)
	}

	return dataDir, nil
}

func copyFS(fsys fs.FS, dst string) error {
	return fs.WalkDir(fsys, ".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		dstPath := filepath.Join(dst, path)

		if d.IsDir() {
			return os.MkdirAll(dstPath, 0755)
		}

		data, err := fs.ReadFile(fsys, path)
		if err != nil {
			return err
		}

		return os.WriteFile(dstPath, data, 0644)
	})
}
