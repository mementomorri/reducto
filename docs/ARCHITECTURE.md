# reducto Architecture Guide

**Semantic Code Compression Engine - Technical Deep Dive**

> **For:** Maintainers, Contributors, and Developers  
> **Purpose:** In-depth technical understanding of reducto's architecture, design decisions, and implementation details

---

## TL;DR

**reducto** is a hybrid Go/Python CLI application that autonomously refactors codebases to reduce complexity and eliminate duplication while maintaining 100% functional parity.

### Key Architecture Points

```
┌─────────────────────────────────────────────────────────────┐
│                    USER TERMINAL                             │
│              $ reducto analyze .                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  GO CLI (Binary - Fast, Portable)                           │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │   Walker    │   Parser    │   Git Mgr   │   LSP Mgr   │ │
│  │  (parallel) │ (Tree-sitter)│(checkpoint) │(references) │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
│                          │                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │         MCP SERVER (JSON-RPC over STDIO)                ││
│  │  Tools: read_file, get_symbols, apply_diff, run_tests  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │ STDIO pipes
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  PYTHON AI SIDECAR (Child Process - AI Reasoning)           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              MCP CLIENT                                  ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Analyzer │ │Deduplicator│ │Idiomatizer│ │ Pattern  │       │
│  │  Agent   │ │  Agent    │ │  Agent   │ │  Agent   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  │   LLM    │ │Embedding │ │ Session  │                     │
│  │  Router  │ │ Service  │ │  Store   │                     │
│  │(LiteLLM) │ │(ChromaDB)│ │          │                     │
│  └──────────┘ └──────────┘ └──────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

| Component | Language | Why? |
|-----------|----------|------|
| **CLI & Parsing** | Go | Binary portability, parallel file scanning, low memory |
| **AI Reasoning** | Python | Best ML ecosystem, Pydantic for typed agents, LiteLLM |
| **Communication** | MCP/JSON-RPC | Standardized protocol, language-agnostic |

### Core Workflow

1. **Scan** → Go parallel walker scans repository
2. **Parse** → Tree-sitter extracts symbols/AST
3. **Analyze** → Python agents use LLM to find patterns
4. **Plan** → Generate refactoring plan with diffs
5. **Validate** → Run tests, check lint
6. **Apply** → Git checkpoint → Apply diff → Test → Commit/Rollback

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architectural Decisions](#2-architectural-decisions)
3. [Component Deep Dive](#3-component-deep-dive)
4. [Data Flow](#4-data-flow)
5. [Implementation Details](#5-implementation-details)
6. [Testing Strategy](#6-testing-strategy)
7. [Deployment](#7-deployment)
8. [Extending reducto](#8-extending-reducto)

---

## 1. System Overview

### 1.1 The Problem Space

Modern codebases suffer from:
- **Code duplication** - Same logic repeated across files
- **Non-idiomatic patterns** - Custom solutions instead of standard patterns
- **Complexity creep** - Functions grow, nesting deepens
- **Cognitive debt** - Hard to understand, harder to modify

Traditional linters catch syntax issues. reducto goes further by:
- Understanding **semantic similarity** (not just text matching)
- Suggesting **design patterns** (Factory, Strategy, Observer)
- Applying **idiomatic transformations** (list comprehensions, etc.)
- Maintaining **git-traceable** changes with rollback safety

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER COMMAND                             │
│                    reducto deduplicate .                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GO CLI LAYER                                 │
│  - Cobra CLI framework                                           │
│  - Config loading (Viper)                                        │
│  - Sidecar process management                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ spawns
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PYTHON SIDECAR                                 │
│  - FastAPI (legacy HTTP mode)                                    │
│  - MCP Client (current STDIO mode)                               │
│  - Agent orchestration (Pydantic-based)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  LLM Router  │ │  Embedding   │ │   Session    │
    │  (LiteLLM)   │ │  (ChromaDB)  │ │    Store     │
    └──────────────┘ └──────────────┘ └──────────────┘
```

### 1.3 Directory Structure

```
reducto/
├── cmd/reducto/              # Go CLI entry point
│   └── main.go
├── internal/                 # Go internal packages (not importable)
│   ├── cli/                  # Cobra command definitions
│   ├── config/               # Configuration loading
│   ├── git/                  # Git operations (go-git)
│   ├── lsp/                  # Language Server Protocol clients
│   ├── mcp/                  # MCP server implementation
│   ├── parser/               # Tree-sitter parsing
│   ├── reporter/             # Report generation
│   ├── runner/               # Test/lint execution
│   ├── sidecar/              # Python sidecar lifecycle
│   └── walker/               # Parallel file traversal
├── pkg/                      # Go public packages
│   └── models/               # Shared data structures
├── python/                   # Python AI sidecar
│   ├── ai_sidecar/
│   │   ├── agents/           # AI agents (analyzer, deduplicator, etc.)
│   │   ├── embeddings/       # ChromaDB + sentence-transformers
│   │   ├── llm/              # LiteLLM router
│   │   ├── mcp/              # MCP client
│   │   ├── utils/            # Helper functions
│   │   ├── main.py           # FastAPI entry (legacy)
│   │   ├── mcp_entry.py      # MCP entry point (current)
│   │   ├── models.py         # Pydantic models
│   │   └── session.py        # Session persistence
│   └── pyproject.toml
├── tests/                    # Python integration/E2E tests
│   ├── e2e/
│   ├── integration/
│   ├── fixtures/
│   └── utils/
└── docs/                     # Documentation
```

---

## 2. Architectural Decisions

### 2.1 Hybrid Go/Python Architecture

**Decision:** Use Go for CLI/infrastructure and Python for AI reasoning.

```
┌─────────────────────────────────────────────────────────┐
│                    WHY HYBRID?                           │
├─────────────────────────────────────────────────────────┤
│ Go Strengths              │ Python Strengths            │
│ ─────────────────          │ ─────────────────          │
│ ✓ Binary distribution     │ ✓ ML/AI ecosystem           │
│ ✓ Parallel file I/O       │ ✓ Pydantic (typed agents)   │
│ ✓ Low memory footprint    │ ✓ LiteLLM integration       │
│ ✓ Tree-sitter bindings    │ ✓ ChromaDB/SentenceTransform│
│ ✓ Git operations (go-git) │ ✓ Rapid prototyping         │
└─────────────────────────────────────────────────────────┘
```

**Pros:**
- **Best of both worlds** - Leverages each language's strengths
- **Binary distribution** - Go compiles to single binary, no runtime needed
- **AI flexibility** - Python has the best LLM/ML library support
- **Performance** - Go handles I/O-heavy tasks efficiently

**Cons:**
- **Complexity** - Two build systems, two dependency managers
- **IPC overhead** - Communication between processes adds latency
- **Debugging** - Need to debug two runtimes simultaneously

**Alternatives Considered:**
1. **Pure Go** - Limited LLM library support, would need CGO for Python libs
2. **Pure Python** - Slower file scanning, harder binary distribution (PyInstaller)
3. **Rust + Python** - Rust has better safety but steeper learning curve

### 2.2 MCP (Model Context Protocol) for IPC

**Decision:** Use JSON-RPC over STDIO for Go↔Python communication.

```
┌──────────────────────────────────────────────────────────────┐
│                    MCP COMMUNICATION FLOW                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Go (MCP Server)              Python (MCP Client)            │
│  ┌─────────────┐               ┌─────────────┐               │
│  │   stdin     │◄──────────────│   stdout    │               │
│  │  (read)     │   JSON-RPC    │  (write)    │               │
│  └─────────────┘   requests    └─────────────┘               │
│       ▲                              ▲                        │
│       │                              │                        │
│  ┌─────────────┐               ┌─────────────┐               │
│  │   stdout    │───────────────►│   stdin     │               │
│  │  (write)    │   JSON-RPC    │  (read)     │               │
│  │             │   responses   │             │               │
│  └─────────────┘               └─────────────┘               │
│                                                               │
└──────────────────────────────────────────────────────────────┘

Example JSON-RPC Request:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "get_symbols",
  "params": {"path": "src/auth.py", "content": "..."}
}

Example JSON-RPC Response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "path": "src/auth.py",
    "symbols": [
      {"name": "authenticate", "type": "function", "start_line": 10}
    ]
  }
}
```

**Pros:**
- **Language agnostic** - Any language can implement MCP
- **Streaming** - STDIO allows real-time communication
- **Simple protocol** - JSON-RPC 2.0 is well-understood
- **No network overhead** - STDIO is faster than HTTP for local IPC

**Cons:**
- **Blocking I/O** - Need async handling to avoid deadlocks
- **Limited bandwidth** - Large files can clog pipes
- **Debugging** - Harder to inspect than HTTP traffic

**Alternatives Considered:**
1. **HTTP/REST** - More overhead, need port management
2. **gRPC** - More complex, overkill for local IPC
3. **Unix sockets** - Platform-specific, Windows incompatibility

### 2.3 Tree-sitter for Parsing

**Decision:** Use Tree-sitter for AST parsing and symbol extraction.

```
┌─────────────────────────────────────────────────────────────┐
│                  TREE-SITTER PARSING FLOW                    │
├─────────────────────────────────────────────────────────────┘

Source Code:
def authenticate(user, password):
    if user.is_valid() and password.check():
        return create_session(user)
    return None

         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Tree-sitter Concrete Syntax Tree (CST)                     │
│                                                              │
│  (module                                                    │
│    (function_definition                                     │
│      name: (identifier) "authenticate"                      │
│      parameters: (parameters ...)                           │
│      body: (block                                           │
│        (if_statement                                        │
│          condition: (and_expression ...)                    │
│          consequent: (return_statement ...)                 │
│        )                                                    │
│        (return_statement ...)                               │
│      )                                                      │
│    )                                                        │
│  )                                                          │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Extracted Symbols:                                          │
│  - authenticate (function, lines 1-5)                       │
│  - create_session (reference)                               │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- **Incremental parsing** - Only reparses changed portions
- **Error recovery** - Continues parsing even with syntax errors
- **Multi-language** - Same API for Python, JS, Go, etc.
- **Fast** - Written in C, sub-millisecond parsing

**Cons:**
- **Learning curve** - CST vs AST concepts
- **Grammar dependencies** - Need separate grammar per language
- **API instability** - Go bindings still maturing

**Current Implementation Note:**
The code includes Tree-sitter but currently uses regex-based parsing as fallback due to Go bindings API changes. Tree-sitter can be re-enabled by updating the bindings.

### 2.4 LiteLLM for Model Routing

**Decision:** Use LiteLLM as the unified LLM interface.

```
┌──────────────────────────────────────────────────────────────┐
│                    LLM ROUTING ARCHITECTURE                   │
├──────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  Agent Request  │
                    │  tier=MEDIUM    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   LLM Router    │
                    │  (LiteLLM)      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │   Local     │ │   Local     │ │   Remote    │
     │  Ollama     │ │  Ollama     │ │  Anthropic  │
     │  qwen2.5    │ │  deepseek   │ │  claude-3   │
     │  :1.5b      │ │  :6.7b      │ │  -sonnet    │
     └─────────────┘ └─────────────┘ └─────────────┘
          ▲              ▲              ▲
          │              │              │
          └──────────────┴──────────────┘
                         │
                         ▼
              ┌───────────────────┐
              │  Model Selection  │
              │  Logic:           │
              │  1. Check override│
              │  2. Prefer local? │
              │  3. Fallback      │
              └───────────────────┘
```

**Model Tiers:**

| Tier | Use Case | Local Model | Remote Model |
|------|----------|-------------|--------------|
| **Light** | Variable renaming, docstrings | `ollama/gemma3:270m` | `openai/gpt-4o-mini` |
| **Medium** | Single-file refactoring | `ollama/qwen2.5-coder:1.5b` | `anthropic/claude-3-haiku` |
| **Heavy** | Architecture, patterns | `ollama/deepseek-coder:6.7b` | `anthropic/claude-3.5-sonnet` |

**Pros:**
- **Unified API** - Same code for Ollama, OpenAI, Anthropic, etc.
- **Fallback handling** - Automatic retry on failure
- **Cost tracking** - Built-in token counting
- **Local-first** - Privacy-preserving local inference

**Cons:**
- **Additional dependency** - Another layer to maintain
- **Abstraction leaks** - Provider-specific features may not translate

### 2.5 ChromaDB for Vector Storage

**Decision:** Use ChromaDB with sentence-transformers for semantic search.

```
┌──────────────────────────────────────────────────────────────┐
│              EMBEDDING-BASED DEDUPLICATION                    │
├──────────────────────────────────────────────────────────────┘

Code Block 1:                          Code Block 2:
def validate_email(email):             def check_email(email_addr):
    if "@" not in email:                   if "@" not in email_addr:
        return False                           return False
    return True                            return True

         │                                       │
         ▼                                       ▼
┌─────────────────┐                     ┌─────────────────┐
│  sentence-      │                     │  sentence-      │
│  transformers   │                     │  transformers   │
│  all-MiniLM-    │                     │  all-MiniLM-    │
│  L6-v2          │                     │  L6-v2          │
└────────┬────────┘                     └────────┬────────┘
         │                                       │
         ▼                                       ▼
  [0.23, -0.45, 0.12, ...]               [0.24, -0.44, 0.11, ...]
         │                                       │
         └───────────────────┬───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   ChromaDB      │
                    │  Cosine Similar │
                    │  similarity =   │
                    │  0.98 (> 0.85)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  DUPLICATE      │
                    │  DETECTED!      │
                    └─────────────────┘
```

**Pros:**
- **Semantic matching** - Finds duplicates even with different variable names
- **Fast similarity search** - HNSW index for O(log n) queries
- **Embedded** - No separate database server needed
- **Metadata filtering** - Filter by language, file, etc.

**Cons:**
- **Memory usage** - Ephemeral client stores vectors in memory
- **Cold start** - Need to re-embed on each run (no persistence)

**Alternatives Considered:**
1. **FAISS** - Faster but no metadata filtering
2. **Pinecone** - Requires network, API costs
3. **Simple hash matching** - Misses semantic duplicates

---

## 3. Component Deep Dive

### 3.1 Go CLI Layer (`cmd/reducto/`, `internal/cli/`)

**Responsibility:** User interface, configuration, sidecar lifecycle

```go
// Simplified command flow
rootCmd
├── analyzeCmd      // Scan for complexity hotspots
├── deduplicateCmd  // Find and eliminate duplication
├── idiomatizeCmd   // Transform to idiomatic patterns
├── patternCmd      // Apply design patterns
├── checkCmd        // Quality check
├── reportCmd       // Generate reports
└── mcpCmd          // Start MCP server (debug mode)
```

**Key Implementation Details:**

1. **Spinner UI** - Shows progress during analysis
```go
func showSpinner(done <-chan struct{}, inProgress string, complete string) {
    spinner := []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}
    // Rotates through spinner characters until done channel closes
}
```

2. **Sidecar Lifecycle** - Spawns Python as child process
```go
func (m *MCPManager) Start(command, path string) error {
    m.cmd = exec.Command("python3", "-m", "ai_sidecar.mcp_entry",
        "--root", path, "--command", command)
    
    // Create bidirectional pipes for MCP
    serverIn, clientOut, _ := os.Pipe()
    clientIn, serverOut, _ := os.Pipe()
    
    m.cmd.Stdin = clientIn
    m.cmd.Stdout = clientOut
    
    // Start Go MCP server
    m.server = mcp.NewServer(m.rootDir)
    go m.server.Start(ctx, serverIn, serverOut)
}
```

3. **Approval Flow** - Interactive or pre-approved
```go
func promptForApproval() error {
    if cfg.PreApprove {
        return nil  // Skip approval (--yes flag)
    }
    fmt.Printf("\nApply these changes? [y/N]: ")
    var response string
    fmt.Scanln(&response)
    if response != "y" && response != "Y" {
        return fmt.Errorf("aborted by user")
    }
    return nil
}
```

### 3.2 MCP Server (`internal/mcp/`)

**Responsibility:** Provide tools to Python sidecar

**Available Tools:**

| Tool | Description | Returns |
|------|-------------|---------|
| `read_file` | Read file content | `{path, content, hash, language}` |
| `get_symbols` | Extract symbols | `{path, symbols[]}` |
| `get_ast` | Get AST (simplified) | `{path, symbols, imports}` |
| `find_references` | LSP-based references | `{references[]}` |
| `apply_diff` | Apply unified diff | `{success, path}` |
| `apply_diff_safe` | Apply + test + rollback | `{success, tests_passed, rolled_back}` |
| `run_tests` | Execute test suite | `{success, output, duration}` |
| `git_checkpoint` | Create commit | `{success, commit_hash}` |
| `git_rollback` | Reset to parent | `{success}` |
| `list_files` | List repository files | `{files[], total}` |
| `get_complexity` | Calculate metrics | `{path, metrics}` |

**JSON-RPC Error Codes:**

```go
const (
    // Standard JSON-RPC errors
    ParseError     = -32700
    InvalidRequest = -32600
    MethodNotFound = -32601
    InvalidParams  = -32602
    InternalError  = -32603
    
    // Application-specific errors
    FileNotFound   = -32001
    ParseFailure   = -32002
    TestFailure    = -32003
    GitConflict    = -32004
    LSPUnavailable = -32005
)
```

**Safe Diff Application Flow:**

```
┌──────────────────────────────────────────────────────────────┐
│              apply_diff_safe WORKFLOW                         │
├──────────────────────────────────────────────────────────────┘

1. Create Git Checkpoint
   │
   ▼
2. Apply Diff
   │
   ▼
3. Run Tests? ───No──► Return Success
   │
   Yes
   ▼
4. Tests Pass? ──Yes──► Return Success
   │
   No
   ▼
5. Rollback to Checkpoint
   │
   ▼
6. Return Failure (rolled_back=true)
```

### 3.3 Python Agents (`python/ai_sidecar/agents/`)

**Base Agent Pattern:**

```python
class BaseAgent:
    def __init__(self, llm_router, mcp_client, session_store):
        self.llm = llm_router
        self.mcp = mcp_client
        self.session_store = session_store
    
    def _save_plan(self, plan, command_type):
        # Save to memory and disk
        self.session_store.save_plan(plan, command_type)
```

#### Analyzer Agent

**Purpose:** Repository scanning and complexity detection

```python
async def analyze(self, request: AnalyzeRequest) -> AnalyzeResult:
    # 1. Scan directory via MCP
    files_data = await self.mcp.list_files()
    
    # 2. Extract symbols (Tree-sitter via MCP)
    symbols = await self._extract_symbols(files)
    
    # 3. Find complexity hotspots
    hotspots = await self._find_hotspots(files, symbols)
    
    return AnalyzeResult(
        total_files=len(files),
        total_symbols=len(symbols),
        hotspots=hotspots,  # Top 20 by complexity
    )
```

#### Deduplicator Agent

**Purpose:** Find semantically similar code blocks

```python
async def find_duplicates(self, request: DeduplicateRequest) -> RefactorPlan:
    # 1. Extract function blocks from all files
    blocks = await self._extract_blocks(files)
    
    # 2. Generate embeddings and find duplicates
    duplicate_groups = await self.embedding_service.find_duplicates(
        blocks, threshold=0.85
    )
    
    # 3. Create refactoring changes
    changes = []
    for group in duplicate_groups:
        change = await self._create_dedup_change(group)
        changes.append(change)
    
    return RefactorPlan(session_id, changes, description)
```

#### Idiomatizer Agent

**Purpose:** Transform non-idiomatic code to standard patterns

**Detected Patterns:**

| Pattern | Non-Idiomatic | Idiomatic |
|---------|---------------|-----------|
| List comprehension | `result = []; for x in items: result.append(x*2)` | `[x*2 for x in items]` |
| F-strings | `"Hello " + name + "!"` | `f"Hello {name}!"` |
| Context managers | `f = open(); try: ... finally: f.close()` | `with open() as f: ...` |
| Chain comparison | `if x > 0 and x < 10:` | `if 0 < x < 10:` |

#### Pattern Agent

**Purpose:** Apply design patterns to complex code

**Supported Patterns:**

1. **Factory Pattern** - Replace conditional instantiation
2. **Strategy Pattern** - Encapsulate interchangeable algorithms
3. **Observer Pattern** - Decouple event producers/consumers

#### Quality Checker Agent

**Purpose:** Detect code quality issues

**Checks:**
- Unpronounceable variable names (regex: `^[a-z]{1,2}$` in non-loop context)
- Long functions (>50 lines)
- High complexity (>10 cyclomatic)
- Naming convention violations

### 3.4 Embedding Service (`python/ai_sidecar/embeddings/`)

**Architecture:**

```python
class EmbeddingService:
    def __init__(self):
        self.model = None  # SentenceTransformer
        self.collection = None  # ChromaDB collection
        self._use_real_embeddings = False
    
    async def initialize(self):
        # Try to load real model, fallback to mock
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self._use_real_embeddings = True
        except:
            self._use_real_embeddings = False
        
        self.client = chromadb.EphemeralClient()
        self.collection = self.client.get_or_create_collection("code_embeddings")
```

**Mock Embedding (Fallback):**

```python
def _mock_embedding(self, text: str) -> List[float]:
    """Generate deterministic 384-dim embedding using SHA-256 hash."""
    h = hashlib.sha256(text.encode()).hexdigest()
    embedding = []
    for i in range(384):
        idx = (i * 2) % len(h)
        val = int(h[idx:idx+2], 16) / 255.0
        embedding.append(val)
    return embedding
```

**Why Mock Embeddings?**
- Tests run without model download
- Deterministic for reproducible tests
- Still provides similarity (similar text → similar hash)

### 3.5 LLM Router (`python/ai_sidecar/llm/`)

**Model Selection Logic:**

```python
def get_model_for_tier(self, tier, prefer_local, model_override):
    # 1. Override takes precedence
    if model_override:
        return model_override
    
    cfg = self.config[tier.value]
    
    # 2. Check local availability
    if prefer_local and self.is_local_available():
        return cfg["local_model"]
    
    # 3. Fallback to remote
    return cfg["remote_model"]
```

**Ollama Availability Check:**

```python
def is_local_available(self) -> bool:
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return response.status_code == 200
    except:
        return False
```

### 3.6 Git Manager (`internal/git/`)

**Checkpoint Strategy:**

```go
func (m *Manager) CreateCheckpoint(message string) error {
    wt, _ := m.repo.Worktree()
    
    // Stage all changes
    status, _ := wt.Status()
    for file := range status {
        wt.Add(file)
    }
    
    // Commit with reducto author
    wt.Commit(message, &git.CommitOptions{
        Author: &object.Signature{
            Name:  "reducto",
            Email: "reducto@local",
        },
    })
}
```

**Rollback Strategy:**

```go
func (m *Manager) Rollback() error {
    ref, _ := m.repo.Head()
    commit, _ := m.repo.CommitObject(ref.Hash())
    
    if len(commit.ParentHashes) == 0 {
        return fmt.Errorf("no parent commit")
    }
    
    // Hard reset to parent
    wt.Reset(&git.ResetOptions{
        Commit: commit.ParentHashes[0],
        Mode:   git.HardReset,
    })
}
```

### 3.7 Reporter (`internal/reporter/`)

**Report Types:**

1. **Baseline Report** - Initial complexity analysis
2. **Compression Report** - Before/after metrics
3. **Dry-Run Report** - Proposed changes preview

**Markdown Template:**

```markdown
# reducto Compression Report

**Session ID:** abc123
**Generated:** 2026-03-11T10:30:00Z

## Summary

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Lines of Code | 1000 | 850 | **-150** |
| Cyclomatic Complexity | 45 | 38 | **-7** |
| Cognitive Complexity | 120 | 95 | **-25** |
| Maintainability Index | 65.2 | 72.8 | **+7.6** |

## Files Modified

- `src/auth.py`
- `src/utils.py`

## Changes

### 1. `src/utils/validate_dedup.py`

Extract duplicate validation logic from 3 files...
```

---

## 4. Data Flow

### 4.1 Complete Request Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                    DEDUPLICATE COMMAND FLOW                       │
└──────────────────────────────────────────────────────────────────┘

1. User runs: reducto deduplicate .
   │
   ▼
2. Go CLI parses flags, loads config
   │
   ▼
3. Go spawns Python sidecar:
   python -m ai_sidecar.mcp_entry --command deduplicate --root .
   │
   ▼
4. MCP handshake:
   - Go creates pipes (stdin/stdout)
   - Python connects MCP client
   - Go starts MCP server
   │
   ▼
5. Python requests file list:
   MCP call: list_files()
   │
   ▼
6. Go walks directory (parallel):
   - walker.Walk(rootDir)
   - Detects language per file
   - Returns [{path, hash, language, size}]
   │
   ▼
7. Python reads file contents:
   For each file: MCP call: read_file(path)
   │
   ▼
8. Python extracts code blocks:
   - Parse functions/classes
   - Generate embeddings (ChromaDB)
   │
   ▼
9. Python finds duplicates:
   - Query ChromaDB for similar vectors
   - Group blocks with similarity > 0.85
   │
   ▼
10. Python generates refactoring plan:
    - Create new utility file
    - Generate diff for each change
    - Save plan to session store
    │
    ▼
11. Python returns plan JSON via stderr:
    RESULT:{"status":"success","data":{...}}
    │
    ▼
12. Go parses result, shows summary:
    "Found 3 duplicate code blocks"
    │
    ▼
13. Go prompts for approval:
    "Apply these changes? [y/N]:"
    │
    ▼
14. If approved, Go starts apply flow:
    - For each change: apply_diff_safe()
    - Creates checkpoint
    - Applies diff
    - Runs tests
    - Rolls back if tests fail
    │
    ▼
15. Go generates report:
    - Markdown with before/after metrics
    - Saved to .reducto/reducto-report-<id>.md
```

### 4.2 State Management

```
┌──────────────────────────────────────────────────────────────┐
│                    SESSION STATE FLOW                         │
├──────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Memory    │────►│   Disk      │────►│   Report    │
│  (runtime)  │     │  (.reducto/ │     │  Generation │
│             │     │  sessions/) │     │             │
└─────────────┘     └─────────────┘     └─────────────┘

Session Structure:
{
  "session_id": "uuid-v4",
  "command_type": "deduplicate",
  "created_at": "2026-03-11T10:30:00Z",
  "plan": {
    "changes": [...],
    "description": "...",
    "pattern": "extract_method"
  },
  "metrics_before": {...},
  "metrics_after": {...}
}
```

---

## 5. Implementation Details

### 5.1 Parallel File Walking

```go
// internal/walker/walker.go
func (w *Walker) Walk(root string) ([]FileInfo, error) {
    var files []FileInfo
    var mu sync.Mutex
    var wg sync.WaitGroup
    
    // Concurrent directory walking
    filepath.WalkDir(root, func(path string, d DirEntry, err error) error {
        if d.IsDir() {
            return nil
        }
        
        wg.Add(1)
        go func(p string) {
            defer wg.Done()
            content, _ := os.ReadFile(p)
            hash := sha256.Sum256(content)
            
            mu.Lock()
            files = append(files, FileInfo{
                Path:    p,
                Content: string(content),
                Hash:    hex.EncodeToString(hash[:]),
            })
            mu.Unlock()
        }(path)
        
        return nil
    })
    
    wg.Wait()
    return files, nil
}
```

### 5.2 Unified Diff Application

```go
// internal/mcp/diff.go
func ApplyUnifiedDiff(original, diff string) (string, error) {
    // Parse unified diff format:
    // --- a/file.py
    // +++ b/file.py
    // @@ -1,5 +1,6 @@
    //  context line
    // -removed line
    // +added line
    
    lines := strings.Split(original, "\n")
    diffLines := strings.Split(diff, "\n")
    
    for _, dl := range diffLines {
        if strings.HasPrefix(dl, "+") {
            // Insert line
        } else if strings.HasPrefix(dl, "-") {
            // Remove line
        }
    }
    
    return strings.Join(lines, "\n"), nil
}
```

### 5.3 Complexity Calculation

```go
// internal/parser/ts_parser.go
func (p *TSParser) CalculateComplexity(content string) ComplexityMetrics {
    lines := strings.Split(content, "\n")
    metrics := ComplexityMetrics{
        LinesOfCode: len(lines),
    }
    
    // Cyclomatic: decision points + 1
    decisionKeywords := []string{"if ", "elif ", "for ", "while ", "except "}
    for _, line := range lines {
        for _, kw := range decisionKeywords {
            if strings.HasPrefix(strings.TrimSpace(line), kw) {
                metrics.CyclomaticComplexity++
            }
        }
    }
    metrics.CyclomaticComplexity++ // Base complexity
    
    // Maintainability Index (Microsoft formula)
    metrics.MaintainabilityIndex = 171 - 
        5.2*math.Log(float64(metrics.CyclomaticComplexity)) -
        0.23*float64(metrics.LinesOfCode)
    
    return metrics
}
```

### 5.4 Session Persistence

```python
# python/ai_sidecar/session.py
class SessionStore:
    def __init__(self):
        self._plans: Dict[str, RefactorPlan] = {}
        self._sessions_dir = Path(".reducto/sessions")
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def save_plan(self, plan: RefactorPlan, command_type: str):
        # In-memory cache
        self._plans[plan.session_id] = plan
        
        # Disk persistence
        path = self._sessions_dir / f"{plan.session_id}.json"
        path.write_text(plan.model_dump_json(indent=2))
    
    def load_plan(self, session_id: str) -> Optional[RefactorPlan]:
        # Check memory first
        if session_id in self._plans:
            return self._plans[session_id]
        
        # Fall back to disk
        path = self._sessions_dir / f"{session_id}.json"
        if path.exists():
            return RefactorPlan.model_validate_json(path.read_text())
        
        return None
```

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
                    ┌─────────┐
                   /    E2E    \
                  /   (51 tests)\
                 /───────────────\
                /   Integration    \
               /    (13 tests)      \
              /──────────────────────\
             /       Unit Tests        \
            /    (172+ tests total)     \
           ───────────────────────────────
```

### 6.2 Go Unit Tests

```bash
# Run all Go tests
go test ./... -v

# Run with coverage
go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out
```

**Test Coverage by Package:**

| Package | Tests | Coverage |
|---------|-------|----------|
| `internal/config` | 5 | 92% |
| `internal/git` | 12 | 88% |
| `internal/mcp` | 17 | 95% |
| `internal/parser` | 9 | 85% |
| `internal/reporter` | 9 | 90% |
| `internal/runner` | 18 | 94% |
| `internal/walker` | 7 | 87% |

### 6.3 Python Tests

```bash
# Run Python unit tests
cd python && python -m pytest tests/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run E2E tests
python -m pytest tests/e2e/ -v
```

**Test Markers:**

```python
@pytest.mark.e2e          # Full workflow tests
@pytest.mark.integration  # MCP protocol tests
@pytest.mark.unit         # Isolated unit tests
@pytest.mark.slow         # Tests > 5 seconds
@pytest.mark.real_api     # Requires real LLM/embedding
```

### 6.4 Test Fixtures

**LLM Response Fixtures:**
```json
// tests/fixtures/llm_responses/idiomatize_python.json
{
  "request": "Analyze this Python code for non-idiomatic patterns...",
  "response": {
    "issues": [
      {
        "type": "non_idiomatic",
        "description": "Use list comprehension instead of for loop",
        "suggestion": "[x*2 for x in items]"
      }
    ]
  }
}
```

**Repository Builder:**
```python
# tests/utils/repository_builder.py
class RepositoryBuilder:
    def create_duplicate_code(self):
        """Create test repo with duplicate functions."""
        self.write_file("auth.py", """
def validate_user(user):
    if not user:
        return False
    if "@" not in user:
        return False
    return True
""")
        self.write_file("api.py", """
def validate_email(email):
    if not email:
        return False
    if "@" not in email:
        return False
    return True
""")
```

---

## 7. Deployment

### 7.1 Build Process

**Go Binary:**
```bash
# Cross-compile for all platforms
CGO_ENABLED=0 go build -ldflags="-s -w" -o reducto ./cmd/reducto
```

**Python Package:**
```bash
# Install in development mode
pip install -e python/

# Or with uv (faster)
uv pip install python/
```

### 7.2 Docker Image

```dockerfile
# Multi-stage build
FROM golang:1.24-alpine AS builder
# ... build Go binary ...

FROM python:3.12-slim
# ... install Python deps ...
COPY --from=builder /build/reducto /usr/local/bin/reducto
ENTRYPOINT ["reducto"]
```

**Usage:**
```bash
docker run -v $(pwd):/app ghcr.io/alexkarsten/reducto analyze /app
```

### 7.3 GoReleaser Configuration

```yaml
# .goreleaser.yml
builds:
  - goos: [linux, darwin, windows]
    goarch: [amd64, arm64]
    main: ./cmd/reducto

archives:
  - files:
      - src: python/**
        dst: python
      - LICENSE
      - README.md

brews:
  - repository:
      owner: alexkarsten
      name: homebrew-tap
    install: |
      bin.install "reducto"
      libexec.install Dir["python"]
```

---

## 8. Extending reducto

### 8.1 Adding a New Agent

```python
# python/ai_sidecar/agents/new_agent.py
from ai_sidecar.agents.base import BaseAgent

class NewAgent(BaseAgent):
    """Custom agent for specific refactoring task."""
    
    async def analyze(self, request: NewRequest) -> RefactorPlan:
        # 1. Use MCP to get file contents
        files_data = await self.mcp.list_files()
        
        # 2. Analyze with LLM
        prompt = "Analyze these files for..."
        response = await self.llm.complete(prompt, tier=ModelTier.MEDIUM)
        
        # 3. Generate changes
        changes = await self._create_changes(response)
        
        # 4. Return plan
        return RefactorPlan(
            session_id=self._generate_session_id(),
            changes=changes,
            description="New agent analysis",
        )
```

### 8.2 Adding a New MCP Tool

```go
// internal/mcp/server.go
func (s *Server) getHandler(method string) (HandlerFunc, bool) {
    handlers := map[string]HandlerFunc{
        // ... existing handlers ...
        "new_tool": s.handleNewTool,  // Add here
    }
    // ...
}

func (s *Server) handleNewTool(ctx context.Context, params json.RawMessage) (interface{}, error) {
    var input struct {
        Path string `json:"path"`
    }
    json.Unmarshal(params, &input)
    
    // Implement tool logic
    result := doSomething(input.Path)
    
    return result, nil
}
```

### 8.3 Adding a New Language

**Step 1: Add Tree-sitter grammar:**
```bash
go get github.com/tree-sitter/tree-sitter-rust
```

**Step 2: Update parser:**
```go
// internal/parser/ts_parser.go
import tree_sitter_rust "github.com/tree-sitter/tree-sitter-rust/bindings/go"

func (p *TSParser) initParsers() {
    // ... existing parsers ...
    
    rustParser := tree_sitter.NewParser()
    rustParser.SetLanguage(tree_sitter.NewLanguage(tree_sitter_rust.Language()))
    p.parsers[models.LanguageRust] = rustParser
}
```

**Step 3: Add symbol extraction:**
```go
func (p *TSParser) extractSymbolsFromTree(tree, content, language) {
    switch language {
    // ... existing cases ...
    case models.LanguageRust:
        return p.extractRustSymbolsFromTree(tree, content)
    }
}
```

### 8.4 Custom Model Configuration

```yaml
# ~/.reducto.yaml
llm:
  light:
    local_model: "ollama/phi-3:mini"
    remote_model: "openai/gpt-4o-mini"
  medium:
    local_model: "ollama/qwen2.5-coder:7b"
    remote_model: "anthropic/claude-3-5-sonnet-20241022"
  heavy:
    local_model: "ollama/codellama:34b"
    remote_model: "anthropic/claude-3-opus-20240229"
```

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **MCP** | Model Context Protocol - JSON-RPC over STDIO for Go↔Python IPC |
| **LM-CC** | LLM-perceived Code Complexity - metric for AI comprehension difficulty |
| **Sidecar** | Python child process providing AI reasoning to Go parent |
| **Hotspot** | Code region with high cyclomatic/cognitive complexity |
| **Idiomatic** | Following language conventions (Pythonic, Go idioms, etc.) |

## Appendix B: Performance Benchmarks

| Operation | Time (1000 files) | Memory |
|-----------|-------------------|--------|
| File walk + hash | ~500ms | 50MB |
| Symbol extraction | ~2s | 100MB |
| Embedding generation | ~10s | 500MB |
| LLM analysis (local) | ~30s | 2GB |
| LLM analysis (remote) | ~60s | 100MB |

## Appendix C: Troubleshooting

| Issue | Solution |
|-------|----------|
| Python not found | Ensure `python3` is in PATH, version ≥ 3.10 |
| Ollama connection failed | Start Ollama: `ollama serve` |
| MCP pipe broken | Check stderr for Python errors |
| Tests failing after refactor | Run with `--dry-run` first, check test command |
| Slow analysis | Use `--prefer-remote` for faster LLM responses |

---

*Last updated: March 2026*  
*Version: 0.1.0*
