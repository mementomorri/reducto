package parser

import (
	"strings"

	tree_sitter "github.com/tree-sitter/go-tree-sitter"
	tree_sitter_go "github.com/tree-sitter/tree-sitter-go/bindings/go"
	tree_sitter_js "github.com/tree-sitter/tree-sitter-javascript/bindings/go"
	tree_sitter_python "github.com/tree-sitter/tree-sitter-python/bindings/go"

	"github.com/alexkarsten/reducto/pkg/models"
)

type TSParser struct {
	parsers map[models.Language]*tree_sitter.Parser
}

func NewTSParser() *TSParser {
	p := &TSParser{
		parsers: make(map[models.Language]*tree_sitter.Parser),
	}
	p.initParsers()
	return p
}

func (p *TSParser) initParsers() {
	// Initialize Python parser
	pyParser := tree_sitter.NewParser()
	pyParser.SetLanguage(tree_sitter.NewLanguage(tree_sitter_python.Language()))
	p.parsers[models.LanguagePython] = pyParser

	// Initialize JavaScript parser
	jsParser := tree_sitter.NewParser()
	jsParser.SetLanguage(tree_sitter.NewLanguage(tree_sitter_js.Language()))
	p.parsers[models.LanguageJavaScript] = jsParser
	p.parsers[models.LanguageTypeScript] = jsParser

	// Initialize Go parser
	goParser := tree_sitter.NewParser()
	goParser.SetLanguage(tree_sitter.NewLanguage(tree_sitter_go.Language()))
	p.parsers[models.LanguageGo] = goParser
}

func (p *TSParser) Parse(content string, language models.Language) (*ParseResult, error) {
	parser, ok := p.parsers[language]
	if !ok {
		// Fallback to regex parser for unsupported languages
		fallback := New()
		return fallback.Parse(content, language)
	}

	source := []byte(content)
	tree := parser.Parse(source, nil)
	if tree == nil {
		fallback := New()
		return fallback.Parse(content, language)
	}
	defer tree.Close()

	result := &ParseResult{
		Symbols: p.extractSymbolsFromTree(tree, content, language),
		Imports: p.extractImportsFromTree(tree, content, language),
		Exports: []string{},
	}

	return result, nil
}

func (p *TSParser) extractSymbolsFromTree(tree *tree_sitter.Tree, content string, language models.Language) []models.Symbol {
	lines := strings.Split(content, "\n")

	switch language {
	case models.LanguagePython:
		return p.extractPythonSymbolsFromTree(tree, content, lines)
	case models.LanguageJavaScript, models.LanguageTypeScript:
		return p.extractJSSymbolsFromTree(tree, content, lines)
	case models.LanguageGo:
		return p.extractGoSymbolsFromTree(tree, content, lines)
	default:
		return []models.Symbol{}
	}
}

func (p *TSParser) extractPythonSymbolsFromTree(tree *tree_sitter.Tree, content string, lines []string) []models.Symbol {
	var symbols []models.Symbol
	root := tree.RootNode()
	source := []byte(content)

	p.walkPythonNode(root, source, lines, &symbols, "", -1)
	return symbols
}

func (p *TSParser) walkPythonNode(node *tree_sitter.Node, source []byte, lines []string, symbols *[]models.Symbol, currentClass string, classIndent int) {
	if node == nil {
		return
	}

	count := int(node.ChildCount())
	for i := 0; i < count; i++ {
		child := node.Child(uint(i))
		if child == nil {
			continue
		}

		nodeType := child.Kind()

		if nodeType == "class_definition" {
			nameNode := child.ChildByFieldName("name")
			if nameNode != nil {
				name := nameNode.Utf8Text(source)
				startLine := int(child.StartPosition().Row) + 1
				endLine := p.findPythonBlockEnd(lines, startLine-1)

				*symbols = append(*symbols, models.Symbol{
					Name:      name,
					Type:      "class",
					StartLine: startLine,
					EndLine:   endLine,
				})

				// Walk children with new class context
				p.walkPythonNode(child, source, lines, symbols, name, int(child.StartPosition().Column))
				continue
			}
		}

		if nodeType == "function_definition" || nodeType == "async_function_definition" {
			nameNode := child.ChildByFieldName("name")
			if nameNode != nil {
				name := nameNode.Utf8Text(source)
				symbolType := "function"
				if currentClass != "" && int(child.StartPosition().Column) > classIndent {
					symbolType = "method"
				}

				startLine := int(child.StartPosition().Row) + 1
				endLine := int(child.EndPosition().Row) + 1

				*symbols = append(*symbols, models.Symbol{
					Name:      name,
					Type:      symbolType,
					StartLine: startLine,
					EndLine:   endLine,
				})
			}
		}

		p.walkPythonNode(child, source, lines, symbols, currentClass, classIndent)
	}
}

func (p *TSParser) extractJSSymbolsFromTree(tree *tree_sitter.Tree, content string, lines []string) []models.Symbol {
	var symbols []models.Symbol
	root := tree.RootNode()
	source := []byte(content)

	p.walkJSNode(root, source, lines, &symbols)
	return symbols
}

func (p *TSParser) walkJSNode(node *tree_sitter.Node, source []byte, lines []string, symbols *[]models.Symbol) {
	if node == nil {
		return
	}

	count := int(node.ChildCount())
	for i := 0; i < count; i++ {
		child := node.Child(uint(i))
		if child == nil {
			continue
		}

		nodeType := child.Kind()

		if nodeType == "function_declaration" || nodeType == "generator_function_declaration" {
			nameNode := child.ChildByFieldName("name")
			if nameNode != nil {
				name := nameNode.Utf8Text(source)
				startLine := int(child.StartPosition().Row) + 1
				endLine := int(child.EndPosition().Row) + 1

				*symbols = append(*symbols, models.Symbol{
					Name:      name,
					Type:      "function",
					StartLine: startLine,
					EndLine:   endLine,
				})
			}
		}

		if nodeType == "class_declaration" {
			nameNode := child.ChildByFieldName("name")
			if nameNode != nil {
				name := nameNode.Utf8Text(source)
				startLine := int(child.StartPosition().Row) + 1
				endLine := int(child.EndPosition().Row) + 1

				*symbols = append(*symbols, models.Symbol{
					Name:      name,
					Type:      "class",
					StartLine: startLine,
					EndLine:   endLine,
				})
			}
		}

		if nodeType == "variable_declaration" {
			declCount := int(child.ChildCount())
			for j := 0; j < declCount; j++ {
				decl := child.Child(uint(j))
				if decl == nil || decl.Kind() != "variable_declarator" {
					continue
				}
				nameNode := decl.ChildByFieldName("name")
				valueNode := decl.ChildByFieldName("value")
				if nameNode != nil && valueNode != nil {
					valueType := valueNode.Kind()
					if valueType == "arrow_function" || valueType == "function" {
						name := nameNode.Utf8Text(source)
						startLine := int(child.StartPosition().Row) + 1
						endLine := int(child.EndPosition().Row) + 1

						*symbols = append(*symbols, models.Symbol{
							Name:      name,
							Type:      "function",
							StartLine: startLine,
							EndLine:   endLine,
						})
					}
				}
			}
		}

		p.walkJSNode(child, source, lines, symbols)
	}
}

func (p *TSParser) extractGoSymbolsFromTree(tree *tree_sitter.Tree, content string, lines []string) []models.Symbol {
	var symbols []models.Symbol
	root := tree.RootNode()
	source := []byte(content)

	p.walkGoNode(root, source, lines, &symbols)
	return symbols
}

func (p *TSParser) walkGoNode(node *tree_sitter.Node, source []byte, lines []string, symbols *[]models.Symbol) {
	if node == nil {
		return
	}

	count := int(node.ChildCount())
	for i := 0; i < count; i++ {
		child := node.Child(uint(i))
		if child == nil {
			continue
		}

		nodeType := child.Kind()

		if nodeType == "function_declaration" {
			nameNode := child.ChildByFieldName("name")
			if nameNode != nil {
				name := nameNode.Utf8Text(source)
				startLine := int(child.StartPosition().Row) + 1
				endLine := int(child.EndPosition().Row) + 1

				*symbols = append(*symbols, models.Symbol{
					Name:      name,
					Type:      "function",
					StartLine: startLine,
					EndLine:   endLine,
				})
			}
		}

		if nodeType == "method_declaration" {
			nameNode := child.ChildByFieldName("name")
			if nameNode != nil {
				name := nameNode.Utf8Text(source)
				startLine := int(child.StartPosition().Row) + 1
				endLine := int(child.EndPosition().Row) + 1

				*symbols = append(*symbols, models.Symbol{
					Name:      name,
					Type:      "method",
					StartLine: startLine,
					EndLine:   endLine,
				})
			}
		}

		if nodeType == "type_declaration" {
			specCount := int(child.ChildCount())
			for j := 0; j < specCount; j++ {
				spec := child.Child(uint(j))
				if spec == nil || spec.Kind() != "type_spec" {
					continue
				}
				nameNode := spec.ChildByFieldName("name")
				typeNode := spec.ChildByFieldName("type")
				if nameNode != nil && typeNode != nil && typeNode.Kind() == "struct_type" {
					name := nameNode.Utf8Text(source)
					startLine := int(child.StartPosition().Row) + 1
					endLine := int(child.EndPosition().Row) + 1

					*symbols = append(*symbols, models.Symbol{
						Name:      name,
						Type:      "struct",
						StartLine: startLine,
						EndLine:   endLine,
					})
				}
			}
		}

		p.walkGoNode(child, source, lines, symbols)
	}
}

func (p *TSParser) findPythonBlockEnd(lines []string, start int) int {
	if start >= len(lines) {
		return len(lines)
	}

	startIndent := len(lines[start]) - len(strings.TrimLeft(lines[start], " \t"))

	for i := start + 1; i < len(lines); i++ {
		line := lines[i]
		if strings.TrimSpace(line) == "" {
			continue
		}

		currentIndent := len(line) - len(strings.TrimLeft(line, " \t"))
		if currentIndent <= startIndent {
			return i
		}
	}

	return len(lines)
}

func (p *TSParser) extractImportsFromTree(tree *tree_sitter.Tree, content string, language models.Language) []string {
	source := []byte(content)
	root := tree.RootNode()

	switch language {
	case models.LanguagePython:
		return p.extractPythonImports(root, source)
	case models.LanguageJavaScript, models.LanguageTypeScript:
		return p.extractJSImports(root, source)
	case models.LanguageGo:
		return p.extractGoImports(root, source)
	default:
		return []string{}
	}
}

func (p *TSParser) extractPythonImports(root *tree_sitter.Node, source []byte) []string {
	var imports []string
	count := int(root.ChildCount())

	for i := 0; i < count; i++ {
		child := root.Child(uint(i))
		if child == nil {
			continue
		}
		nodeType := child.Kind()
		if nodeType == "import_statement" || nodeType == "import_from_statement" {
			imports = append(imports, strings.TrimSpace(child.Utf8Text(source)))
		}
	}

	return imports
}

func (p *TSParser) extractJSImports(root *tree_sitter.Node, source []byte) []string {
	var imports []string
	count := int(root.ChildCount())

	for i := 0; i < count; i++ {
		child := root.Child(uint(i))
		if child == nil {
			continue
		}
		if child.Kind() == "import_statement" {
			imports = append(imports, strings.TrimSpace(child.Utf8Text(source)))
		}
	}

	return imports
}

func (p *TSParser) extractGoImports(root *tree_sitter.Node, source []byte) []string {
	var imports []string
	count := int(root.ChildCount())

	for i := 0; i < count; i++ {
		child := root.Child(uint(i))
		if child == nil {
			continue
		}
		if child.Kind() == "import_declaration" {
			imports = append(imports, strings.TrimSpace(child.Utf8Text(source)))
		}
	}

	return imports
}

func (p *TSParser) CalculateComplexity(content string, language models.Language) models.ComplexityMetrics {
	parser, ok := p.parsers[language]
	if !ok {
		fallback := New()
		return fallback.CalculateComplexity(content)
	}

	source := []byte(content)
	tree := parser.Parse(source, nil)
	if tree == nil {
		fallback := New()
		return fallback.CalculateComplexity(content)
	}
	defer tree.Close()

	metrics := models.ComplexityMetrics{
		LinesOfCode: len(strings.Split(content, "\n")),
	}

	root := tree.RootNode()
	metrics.CyclomaticComplexity = p.calculateCyclomaticComplexity(root, language, source)
	metrics.CognitiveComplexity = p.calculateCognitiveComplexity(root, language, 0)

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

func (p *TSParser) calculateCyclomaticComplexity(node *tree_sitter.Node, language models.Language, source []byte) int {
	complexity := 1

	decisionNodes := p.getDecisionNodeTypes(language)
	for _, decisionType := range decisionNodes {
		complexity += p.countNodesOfType(node, decisionType)
	}

	// Count logical operators
	logicalOperators := []string{"&&", "||", " and ", " or "}
	for _, op := range logicalOperators {
		complexity += strings.Count(string(source), op)
	}

	return complexity
}

func (p *TSParser) calculateCognitiveComplexity(node *tree_sitter.Node, language models.Language, nesting int) int {
	complexity := 0

	nodeType := node.Kind()
	nestingTypes := p.getNestingTypes(language)

	isNesting := false
	for _, t := range nestingTypes {
		if nodeType == t {
			isNesting = true
			break
		}
	}

	if isNesting {
		complexity += 1 + nesting
		nesting++
	}

	incrementTypes := p.getComplexityIncrementTypes(language)
	for _, t := range incrementTypes {
		if nodeType == t && !isNesting {
			complexity++
		}
	}

	count := int(node.ChildCount())
	for i := 0; i < count; i++ {
		child := node.Child(uint(i))
		complexity += p.calculateCognitiveComplexity(child, language, nesting)
	}

	return complexity
}

func (p *TSParser) getDecisionNodeTypes(language models.Language) []string {
	switch language {
	case models.LanguagePython:
		return []string{"if_statement", "elif_clause", "for_statement", "while_statement", "except_clause", "with_statement"}
	case models.LanguageJavaScript, models.LanguageTypeScript:
		return []string{"if_statement", "else_clause", "for_statement", "while_statement", "switch_statement", "case_clause", "try_statement", "catch_clause"}
	case models.LanguageGo:
		return []string{"if_statement", "else_clause", "for_statement", "switch_statement", "case_clause", "select_statement", "comm_clause", "type_case"}
	default:
		return []string{}
	}
}

func (p *TSParser) getComplexityIncrementTypes(language models.Language) []string {
	return p.getDecisionNodeTypes(language)
}

func (p *TSParser) getNestingTypes(language models.Language) []string {
	switch language {
	case models.LanguagePython:
		return []string{"if_statement", "for_statement", "while_statement", "with_statement", "try_statement"}
	case models.LanguageJavaScript, models.LanguageTypeScript:
		return []string{"if_statement", "for_statement", "while_statement", "switch_statement", "try_statement", "function_declaration"}
	case models.LanguageGo:
		return []string{"if_statement", "for_statement", "switch_statement", "select_statement", "block"}
	default:
		return []string{}
	}
}

func (p *TSParser) countNodesOfType(node *tree_sitter.Node, nodeType string) int {
	count := 0
	if node.Kind() == nodeType {
		count++
	}
	nodeCount := int(node.ChildCount())
	for i := 0; i < nodeCount; i++ {
		child := node.Child(uint(i))
		count += p.countNodesOfType(child, nodeType)
	}
	return count
}

func (p *TSParser) Close() {
	for _, parser := range p.parsers {
		if parser != nil {
			parser.Close()
		}
	}
	p.parsers = nil
}
