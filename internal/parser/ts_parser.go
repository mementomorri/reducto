package parser

import (
	"github.com/alexkarsten/reducto/pkg/models"
)

type TSParser struct {
	fallback *Parser
}

func NewTSParser() *TSParser {
	return &TSParser{
		fallback: New(),
	}
}

func (p *TSParser) Parse(content string, language models.Language) (*ParseResult, error) {
	return p.fallback.Parse(content, language)
}

func (p *TSParser) CalculateComplexity(content string, language models.Language) models.ComplexityMetrics {
	return p.fallback.CalculateComplexity(content)
}

func (p *TSParser) Close() {
}
