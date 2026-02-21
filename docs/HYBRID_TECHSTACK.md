# Tech Stack Specification: The Hybrid Agent Architecture

## 1. Distribution of Responsibilities

The project is divided into two primary layers: the Infrastructure & Analysis Core (Go) and the Agentic Reasoning Layer (Python).

### A. Go: The Infrastructure & Analysis Core

Go is used for the "heavy lifting" where performance and binary portability are critical. It handles the initial user interaction and the scanning of the codebase.

- **CLI Entrypoint:** Using Cobra, Go provides a fast, zero-dependency binary that users can run immediately in any project folder.
- **High-Speed Code Scanning:** Go uses Goroutines to parallelize the scanning of thousands of files across the project. This is significantly faster than Python's thread-based designs.
- **Syntax Tree Extraction:** Go utilizes official Tree-sitter bindings to parse code into a Concrete Syntax Tree (CST).
- **MCP Server Implementation:** The Go core acts as a Model Context Protocol (MCP) server. It provides tools to the Python layer, such as `read_file`, `get_symbols`, and `get_ast_node`.
- **File System & Git Operations:** Go handles the deterministic "Act" phase—writing files to disk and committing changes to Git—ensuring high reliability and low memory footprint.

### B. Python: The Agentic Reasoning Layer

Python is used for the "Brain" of the application, where flexibility and access to the latest AI research are paramount.

- **Agent Orchestration:** Using PydanticAI, Python manages the complex "Plan and Act" loop. It handles the "fuzzy" logic of determining if a code block is "uncommon" or "non-idiomatic."
- **Model Routing:** LiteLLM serves as the gateway to both local models (via Ollama) and remote providers (Anthropic/OpenAI), allowing the user to switch models via simple configuration.
- **Semantic Search & Vector Store:** Python uses ChromaDB or LanceDB to store code embeddings. This is essential for detecting semantically similar logic blocks (deduplication) that might have different variable names.
- **Verification Loop:** Python executes the project's test suite (e.g., pytest, npm test) and analyzes the output to decide if a refactor should be rolled back.

## 2. The Interaction Layer: How They Talk

To ensure the two languages work seamlessly, the application uses the Model Context Protocol (MCP) over Standard Input/Output (STDIO).

1. **The Handshake:** When the user runs the Go CLI, it spawns the Python agent as a child process.
2. **Context Request:** The Python Agent (MCP Client) asks the Go Core (MCP Server) for code context: "Give me all function signatures in auth.go that are longer than 50 lines."
3. **Fast Response:** The Go Core uses Tree-sitter to find these signatures in milliseconds and returns them as structured JSON over STDOUT.
4. **Reasoning:** The Python Agent sends this context to the LLM (local or remote). The LLM suggests a refactor toward a Strategy Pattern.
5. **Execution Order:** The Python Agent sends a command back to the Go Core: "Apply this diff to auth.go and create a git checkpoint."

## 3. Technology Summary Table

| Feature | Preferred Language | Recommended Library/Tool | Reason |
|---------|-------------------|-------------------------|--------|
| CLI & User Input | Go | Cobra | Portability, no-install binary |
| AST Parsing | Go | Tree-sitter | Millisecond parsing, low memory |
| Parallel I/O | Go | Standard Library | Goroutines for concurrent scans |
| Agent Logic | Python | PydanticAI | Typed, reliable agent state management |
| Model Routing | Python | LiteLLM | Supports 100+ local/remote models |
| Vector DB | Python | ChromaDB | Rich ecosystem for semantic RAG |
| Communication | Both | MCP | Standardized, extensible tool protocol |

## 4. Achieving Project Goals via the Hybrid Stack

- **In-Place Editing:** Go's file I/O is used for "surgical" edits to ensure that no metadata or formatting is lost during the rewrite.
- **Local vs. Remote:** Python's LiteLLM allows the user to choose local Ollama models for privacy or remote Claude models for complex architectural changes with a single CLI flag.
- **Repeating Pattern Discovery:** Go extracts the raw patterns, while Python generates embeddings and performs the similarity search in the vector database to identify duplicates.
- **Report Generation:** Go compiles the final metrics (LOC reduction, complexity delta) into a performance-optimized report using its standard library's fast template execution.

By using Go for the "Body" (I/O, parsing, distribution) and Python for the "Brain" (reasoning, model interaction), the project delivers a professional-grade tool that is both incredibly fast and intellectually capable.

---

## 5. Implementation Notes

This section documents implementation decisions and deviations from the specification.

### 5.1 Parser Implementation

**Spec:** Tree-sitter for AST parsing  
**Implementation:** Regex-based parser with Tree-sitter fallback (currently using regex due to API compatibility)

The Tree-sitter bindings are included but the current version uses a regex-based parser as the primary implementation. The `internal/parser/ts_parser.go` file wraps the regex parser for now. Tree-sitter can be re-enabled once the Go bindings API stabilizes.

### 5.2 LSP Integration

**Status:** Complete

LSP (Language Server Protocol) integration is implemented in `internal/lsp/`:
- **manager.go**: LSP manager interface for coordinating multiple language clients
- **protocol.go**: Base client with JSON-RPC over STDIO communication
- **go.go**: gopls client for Go
- **python.go**: pyright/pylsp client for Python
- **typescript.go**: typescript-language-server client for TypeScript/JavaScript

The `find_references` MCP tool now uses LSP to find all references to a symbol across the codebase. LSP clients are lazily initialized when needed.

### 5.3 Communication Flow

**Spec:** MCP over STDIO  
**Implementation:** Verified

The implementation follows the spec exactly:
- Go spawns Python as a child process
- Go acts as MCP Server on piped stdin/stdout
- Python acts as MCP Client calling Go tools
- Results returned via stderr with `RESULT:` prefix

### 5.4 Embedding Service

**Status:** Complete

Uses `sentence-transformers` with `all-MiniLM-L6-v2` model. Falls back to mock embeddings if model unavailable. Integrated with ChromaDB for vector storage.

### 5.5 LLM Router

**Status:** Complete

Uses LiteLLM for unified model access. Supports local (Ollama) and remote (Anthropic, OpenAI) providers. Configuration via environment variables.

### 5.6 Session State

**Implementation:** In-memory in Python

Session state (refactoring plans, etc.) is stored in-memory in Python. This is ephemeral and lost when the sidecar process exits. For persistent sessions, consider adding a state serialization layer.

### 5.7 Error Handling

The implementation uses standard JSON-RPC 2.0 error codes plus custom codes in the `-32xxx` range for domain-specific errors (file not found, parse failure, test failure, git conflict).
