"""
Unit tests for Python models.
"""

import pytest
from datetime import datetime
from ai_sidecar.models import (
    AnalyzeRequest,
    RefactorPlan,
    FileChange,
    ComplexityMetrics,
    DuplicateGroup,
    CodeBlock,
    Language,
    FileInfo,
    Symbol,
    APIResponse,
)


class TestFileInfo:
    """Test FileInfo model."""
    
    def test_file_info_creation(self):
        """Test creating FileInfo instance."""
        info = FileInfo(
            path="test.py",
            content="print('hello')",
            hash="abc123"
        )
        
        assert info.path == "test.py"
        assert info.content == "print('hello')"
        assert info.hash == "abc123"
    
    def test_file_info_optional_hash(self):
        """Test that hash is optional."""
        info = FileInfo(path="test.py", content="pass")
        
        assert info.hash is None


class TestSymbol:
    """Test Symbol model."""
    
    def test_symbol_creation(self):
        """Test creating Symbol instance."""
        symbol = Symbol(
            name="my_function",
            type="function",
            file="main.py",
            start_line=10,
            end_line=20,
            signature="def my_function(x: int) -> str",
            references=["utils.py", "handler.py"]
        )
        
        assert symbol.name == "my_function"
        assert symbol.type == "function"
        assert symbol.start_line == 10
        assert len(symbol.references) == 2
    
    def test_symbol_defaults(self):
        """Test Symbol default values."""
        symbol = Symbol(
            name="test",
            type="function",
            file="test.py",
            start_line=1,
            end_line=5
        )
        
        assert symbol.signature is None
        assert symbol.references == []


class TestComplexityMetrics:
    """Test ComplexityMetrics model."""
    
    def test_metrics_defaults(self):
        """Test default metric values."""
        metrics = ComplexityMetrics()
        
        assert metrics.cyclomatic_complexity == 0
        assert metrics.cognitive_complexity == 0
        assert metrics.lines_of_code == 0
        assert metrics.maintainability_index == 0.0
        assert metrics.halstead_difficulty == 0.0
    
    def test_metrics_json_serialization(self):
        """Test complete JSON serialization."""
        metrics = ComplexityMetrics(
            cyclomatic_complexity=10,
            cognitive_complexity=15,
            lines_of_code=100,
            maintainability_index=65.5,
            halstead_difficulty=12.3
        )
        
        json_data = metrics.model_dump()
        
        assert json_data == {
            "cyclomatic_complexity": 10,
            "cognitive_complexity": 15,
            "lines_of_code": 100,
            "maintainability_index": 65.5,
            "halstead_difficulty": 12.3
        }


class TestCodeBlock:
    """Test CodeBlock model."""
    
    def test_code_block_creation(self, sample_complexity_metrics):
        """Test creating CodeBlock instance."""
        block = CodeBlock(
            id="block-1",
            file="main.py",
            start_line=10,
            end_line=20,
            content="def foo(): pass",
            language=Language.PYTHON,
            symbol_type="function",
            symbol_name="foo",
            metrics=sample_complexity_metrics
        )
        
        assert block.id == "block-1"
        assert block.language == Language.PYTHON
        assert block.embedding is None
    
    def test_code_block_with_embedding(self, sample_complexity_metrics):
        """Test CodeBlock with embedding."""
        embedding = [0.1, 0.2, 0.3, 0.4]
        block = CodeBlock(
            id="block-2",
            file="app.py",
            start_line=1,
            end_line=5,
            content="x = 1",
            language=Language.PYTHON,
            symbol_type="variable",
            symbol_name="x",
            metrics=sample_complexity_metrics,
            embedding=embedding
        )
        
        assert block.embedding == embedding


class TestDuplicateGroup:
    """Test DuplicateGroup model."""
    
    def test_duplicate_group_creation(self, sample_code_block):
        """Test creating DuplicateGroup instance."""
        group = DuplicateGroup(
            id="dup-1",
            blocks=[sample_code_block, sample_code_block],
            similarity=0.92,
            suggested_fix="Extract to utils.py"
        )
        
        assert group.id == "dup-1"
        assert len(group.blocks) == 2
        assert group.similarity == 0.92
        assert group.suggested_fix == "Extract to utils.py"
    
    def test_duplicate_group_optional_fix(self, sample_code_block):
        """Test that suggested_fix is optional."""
        group = DuplicateGroup(
            id="dup-2",
            blocks=[sample_code_block],
            similarity=0.85
        )
        
        assert group.suggested_fix is None


class TestFileChange:
    """Test FileChange model."""
    
    def test_file_change_creation(self):
        """Test creating FileChange instance."""
        change = FileChange(
            path="main.py",
            original="def old(): pass",
            modified="def new(): pass",
            description="Rename function"
        )
        
        assert change.path == "main.py"
        assert change.original == "def old(): pass"
        assert change.modified == "def new(): pass"


class TestRefactorPlan:
    """Test RefactorPlan model."""
    
    def test_refactor_plan_creation(self):
        """Test creating RefactorPlan instance."""
        change = FileChange(
            path="test.py",
            original="x = 1",
            modified="x = 2",
            description="Update value"
        )
        
        plan = RefactorPlan(
            session_id="session-123",
            changes=[change],
            description="Test refactor"
        )
        
        assert plan.session_id == "session-123"
        assert len(plan.changes) == 1
        assert plan.description == "Test refactor"
        assert plan.pattern is None
        assert isinstance(plan.created_at, datetime)
    
    def test_refactor_plan_with_pattern(self):
        """Test RefactorPlan with pattern."""
        plan = RefactorPlan(
            session_id="session-456",
            changes=[],
            description="Apply factory pattern",
            pattern="factory"
        )
        
        assert plan.pattern == "factory"


class TestAnalyzeRequest:
    """Test AnalyzeRequest model."""
    
    def test_analyze_request_defaults(self):
        """Test that optional fields use defaults."""
        req = AnalyzeRequest(path="/test")
        
        assert req.path == "/test"
        assert req.files == []
        assert req.config == {}
    
    def test_analyze_request_with_files(self):
        """Test AnalyzeRequest with files."""
        file_info = FileInfo(path="test.py", content="pass")
        req = AnalyzeRequest(
            path="/project",
            files=[file_info],
            config={"language": "python"}
        )
        
        assert len(req.files) == 1
        assert req.config["language"] == "python"


class TestAPIResponse:
    """Test APIResponse model."""
    
    def test_success_response(self):
        """Test successful API response."""
        data = {"total_files": 10}
        response = APIResponse(status="success", data=data)
        
        assert response.status == "success"
        assert response.data == data
        assert response.error is None
    
    def test_error_response(self):
        """Test error API response."""
        response = APIResponse(
            status="error",
            data=None,
            error="File not found"
        )
        
        assert response.status == "error"
        assert response.error == "File not found"


class TestLanguage:
    """Test Language enum."""
    
    def test_language_values(self):
        """Test Language enum values."""
        assert Language.PYTHON == "python"
        assert Language.JAVASCRIPT == "javascript"
        assert Language.TYPESCRIPT == "typescript"
        assert Language.GO == "go"
        assert Language.UNKNOWN == "unknown"
    
    def test_language_from_string(self):
        """Test creating Language from string."""
        assert Language("python") == Language.PYTHON
        assert Language("javascript") == Language.JAVASCRIPT


@pytest.fixture
def sample_complexity_metrics():
    """Sample complexity metrics for testing."""
    return ComplexityMetrics(
        cyclomatic_complexity=5,
        cognitive_complexity=8,
        lines_of_code=20,
        maintainability_index=70.5,
        halstead_difficulty=10.0
    )


@pytest.fixture
def sample_code_block(sample_complexity_metrics):
    """Sample code block for testing."""
    return CodeBlock(
        id="test-block",
        file="test.py",
        start_line=1,
        end_line=10,
        content="def test(): pass",
        language=Language.PYTHON,
        symbol_type="function",
        symbol_name="test",
        metrics=sample_complexity_metrics
    )
