package mcp

import (
	"regexp"
	"strings"
)

func ApplyUnifiedDiff(original, diff string) (string, error) {
	lines := strings.Split(original, "\n")
	diffLines := strings.Split(diff, "\n")

	hunks, err := parseHunks(diffLines)
	if err != nil {
		return "", err
	}

	for i := len(hunks) - 1; i >= 0; i-- {
		lines, err = applyHunk(lines, hunks[i])
		if err != nil {
			return "", err
		}
	}

	return strings.Join(lines, "\n"), nil
}

type hunk struct {
	oldStart int
	oldCount int
	newStart int
	newCount int
	changes  []diffLine
}

type diffLine struct {
	kind    byte
	content string
}

var hunkHeaderRegex = regexp.MustCompile(`^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@`)

func parseHunks(diffLines []string) ([]hunk, error) {
	var hunks []hunk
	var currentHunk *hunk

	for _, line := range diffLines {
		if strings.HasPrefix(line, "@@ ") {
			if currentHunk != nil {
				hunks = append(hunks, *currentHunk)
			}

			matches := hunkHeaderRegex.FindStringSubmatch(line)
			if matches == nil {
				continue
			}

			currentHunk = &hunk{}
			if matches[1] != "" {
				currentHunk.oldStart = parseInt(matches[1])
			}
			if matches[2] != "" {
				currentHunk.oldCount = parseInt(matches[2])
			} else {
				currentHunk.oldCount = 1
			}
			if matches[3] != "" {
				currentHunk.newStart = parseInt(matches[3])
			}
			if matches[4] != "" {
				currentHunk.newCount = parseInt(matches[4])
			} else {
				currentHunk.newCount = 1
			}
		} else if currentHunk != nil && len(line) > 0 {
			kind := line[0]
			if kind == '+' || kind == '-' || kind == ' ' {
				currentHunk.changes = append(currentHunk.changes, diffLine{
					kind:    kind,
					content: line[1:],
				})
			}
		}
	}

	if currentHunk != nil {
		hunks = append(hunks, *currentHunk)
	}

	return hunks, nil
}

func parseInt(s string) int {
	var result int
	for _, c := range strings.TrimSpace(s) {
		if c >= '0' && c <= '9' {
			result = result*10 + int(c-'0')
		}
	}
	return result
}

func applyHunk(lines []string, h hunk) ([]string, error) {
	var result []string
	lineIdx := 0

	for lineIdx < h.oldStart-1 && lineIdx < len(lines) {
		result = append(result, lines[lineIdx])
		lineIdx++
	}

	for _, change := range h.changes {
		switch change.kind {
		case ' ':
			if lineIdx < len(lines) {
				result = append(result, lines[lineIdx])
				lineIdx++
			}
		case '-':
			lineIdx++
		case '+':
			result = append(result, change.content)
		}
	}

	for lineIdx < len(lines) {
		result = append(result, lines[lineIdx])
		lineIdx++
	}

	return result, nil
}
