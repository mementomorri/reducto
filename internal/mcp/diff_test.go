package mcp

import (
	"testing"
)

func TestApplyUnifiedDiff_SimpleAddition(t *testing.T) {
	original := "line1\nline2\n"
	diff := `--- a/file.txt
+++ b/file.txt
@@ -1,2 +1,3 @@
 line1
+newline
 line2
`

	result, err := ApplyUnifiedDiff(original, diff)
	if err != nil {
		t.Fatalf("ApplyUnifiedDiff failed: %v", err)
	}

	if result == original {
		t.Error("Result should be different from original")
	}
}

func TestApplyUnifiedDiff_SimpleRemoval(t *testing.T) {
	original := "line1\nline2\nline3\n"
	diff := `--- a/file.txt
+++ b/file.txt
@@ -1,3 +1,2 @@
 line1
-line2
 line3
`

	result, err := ApplyUnifiedDiff(original, diff)
	if err != nil {
		t.Fatalf("ApplyUnifiedDiff failed: %v", err)
	}

	if result == original {
		t.Error("Result should be different from original")
	}
}

func TestApplyUnifiedDiff_SimpleModification(t *testing.T) {
	original := "line1\noldline\nline3\n"
	diff := `--- a/file.txt
+++ b/file.txt
@@ -1,3 +1,3 @@
 line1
-oldline
+newline
 line3
`

	result, err := ApplyUnifiedDiff(original, diff)
	if err != nil {
		t.Fatalf("ApplyUnifiedDiff failed: %v", err)
	}

	if result == original {
		t.Error("Result should be different from original")
	}
}

func TestApplyUnifiedDiff_EmptyDiff(t *testing.T) {
	original := "line1\nline2\n"

	result, err := ApplyUnifiedDiff(original, "")
	if err != nil {
		t.Fatalf("ApplyUnifiedDiff failed: %v", err)
	}

	if result != original {
		t.Error("Empty diff should return original content")
	}
}

func TestApplyUnifiedDiff_NoChange(t *testing.T) {
	original := "line1\nline2\n"
	diff := `--- a/file.txt
+++ b/file.txt
@@ -1,2 +1,2 @@
 line1
 line2
`

	result, err := ApplyUnifiedDiff(original, diff)
	if err != nil {
		t.Fatalf("ApplyUnifiedDiff failed: %v", err)
	}

	if result != original {
		t.Error("No-change diff should return original content")
	}
}

func TestParseHunks_Empty(t *testing.T) {
	lines := []string{}

	hunks, err := parseHunks(lines)
	if err != nil {
		t.Fatalf("parseHunks failed: %v", err)
	}

	if len(hunks) != 0 {
		t.Errorf("Expected 0 hunks, got %d", len(hunks))
	}
}

func TestParseHunks_SingleHunk(t *testing.T) {
	diffLines := []string{
		"--- a/file.txt",
		"+++ b/file.txt",
		"@@ -1,3 +1,4 @@",
		" line1",
		"+newline",
		" line2",
		" line3",
	}

	hunks, err := parseHunks(diffLines)
	if err != nil {
		t.Fatalf("parseHunks failed: %v", err)
	}

	if len(hunks) != 1 {
		t.Errorf("Expected 1 hunk, got %d", len(hunks))
	}
}

func TestParseHunks_MultipleHunks(t *testing.T) {
	diffLines := []string{
		"--- a/file.txt",
		"+++ b/file.txt",
		"@@ -1,2 +1,2 @@",
		" line1",
		"-line2",
		"+newline2",
		"@@ -5,2 +5,2 @@",
		" line5",
		"-line6",
		"+newline6",
	}

	hunks, err := parseHunks(diffLines)
	if err != nil {
		t.Fatalf("parseHunks failed: %v", err)
	}

	if len(hunks) != 2 {
		t.Errorf("Expected 2 hunks, got %d", len(hunks))
	}
}

func TestApplyHunk_AddLines(t *testing.T) {
	lines := []string{"line1", "line2"}
	h := hunk{
		oldStart: 1,
		oldCount: 2,
		newStart: 1,
		newCount: 3,
		changes: []diffLine{
			{kind: ' ', content: "line1"},
			{kind: '+', content: "newline"},
			{kind: ' ', content: "line2"},
		},
	}

	result, err := applyHunk(lines, h)
	if err != nil {
		t.Fatalf("applyHunk failed: %v", err)
	}

	if len(result) != 3 {
		t.Errorf("Expected 3 lines, got %d", len(result))
	}
}

func TestApplyHunk_RemoveLines(t *testing.T) {
	lines := []string{"line1", "line2", "line3"}
	h := hunk{
		oldStart: 1,
		oldCount: 3,
		newStart: 1,
		newCount: 2,
		changes: []diffLine{
			{kind: ' ', content: "line1"},
			{kind: '-', content: "line2"},
			{kind: ' ', content: "line3"},
		},
	}

	result, err := applyHunk(lines, h)
	if err != nil {
		t.Fatalf("applyHunk failed: %v", err)
	}

	if len(result) != 2 {
		t.Errorf("Expected 2 lines, got %d", len(result))
	}
}
