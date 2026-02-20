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
