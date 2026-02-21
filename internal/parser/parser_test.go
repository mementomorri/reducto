package parser

import (
	"testing"

	"github.com/alexkarsten/reducto/pkg/models"
)

func TestParse_Python(t *testing.T) {
	p := New()

	content := `
def hello():
    pass

class World:
    def greet(self):
        pass
`

	result, err := p.Parse(content, models.LanguagePython)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if len(result.Symbols) < 2 {
		t.Errorf("Expected at least 2 symbols, got %d", len(result.Symbols))
	}
}

func TestParse_Go(t *testing.T) {
	p := New()

	content := `
package main

func hello() {}

type World struct {
	name string
}

func (w *World) greet() {}
`

	result, err := p.Parse(content, models.LanguageGo)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if len(result.Symbols) < 2 {
		t.Errorf("Expected at least 2 symbols, got %d", len(result.Symbols))
	}
}

func TestParse_JavaScript(t *testing.T) {
	p := New()

	content := `
function hello() {}

class World {
    greet() {}
}
`

	result, err := p.Parse(content, models.LanguageJavaScript)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if len(result.Symbols) < 2 {
		t.Errorf("Expected at least 2 symbols, got %d", len(result.Symbols))
	}
}

func TestParse_Imports(t *testing.T) {
	p := New()

	pythonContent := `
import os
from sys import path
`

	result, err := p.Parse(pythonContent, models.LanguagePython)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if len(result.Imports) < 1 {
		t.Error("Expected at least 1 import")
	}
}

func TestParse_Exports(t *testing.T) {
	p := New()

	jsContent := `
export function hello() {}
export const name = "world";
`

	result, err := p.Parse(jsContent, models.LanguageJavaScript)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if len(result.Exports) < 1 {
		t.Error("Expected at least 1 export")
	}
}

func TestCalculateComplexity(t *testing.T) {
	p := New()

	content := `
def complex_function(data):
    if data:
        for item in data:
            if item > 0:
                print(item)
            else:
                print("negative")
    else:
        print("empty")
`

	metrics := p.CalculateComplexity(content)

	if metrics.LinesOfCode == 0 {
		t.Error("LinesOfCode should not be 0")
	}
}

func TestFindBlocks_Python(t *testing.T) {
	p := New()

	content := `
def func1():
    pass

def func2():
    pass
`

	blocks := p.FindBlocks(content, models.LanguagePython)

	if len(blocks) < 2 {
		t.Errorf("Expected at least 2 blocks, got %d", len(blocks))
	}
}

func TestTSParser_Fallback(t *testing.T) {
	p := NewTSParser()

	content := `def hello(): pass`

	result, err := p.Parse(content, models.LanguagePython)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if len(result.Symbols) < 1 {
		t.Error("Expected at least 1 symbol")
	}
}

func TestTSParser_Complexity(t *testing.T) {
	p := NewTSParser()

	content := `
def complex():
    if True:
        for i in range(10):
            if i > 5:
                print(i)
`

	metrics := p.CalculateComplexity(content, models.LanguagePython)

	if metrics.LinesOfCode == 0 {
		t.Error("LinesOfCode should not be 0")
	}
}
