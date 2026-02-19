"""
Utility for creating synthetic test repositories with known issues.
"""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict


class RepositoryBuilder:
    """Create synthetic test repositories with known issues for testing."""
    
    def __init__(self, root: Path, with_git: bool = False):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True, parents=True)
        self.has_git = False
        
        if with_git:
            self._init_git()
    
    def _init_git(self):
        """Initialize git repository."""
        subprocess.run(
            ["git", "init"],
            cwd=self.root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.root,
            check=True,
            capture_output=True
        )
        self.has_git = True
    
    def create_file(self, filename: str, content: str):
        """Create a file in the repository."""
        file_path = self.root / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    
    def create_duplicate_validation_blocks(self):
        """Create two files with semantically identical validation logic."""
        auth_code = '''
def validate_email(email):
    if not email:
        raise ValueError("Email required")
    if '@' not in email:
        raise ValueError("Invalid email format")
    if len(email) > 255:
        raise ValueError("Email too long")
    return email.lower().strip()

def validate_password(password):
    if not password:
        raise ValueError("Password required")
    if len(password) < 8:
        raise ValueError("Password too short")
    return password
'''
        (self.root / "auth.py").write_text(auth_code)
        
        user_code = '''
def check_email_address(email_addr):
    if not email_addr:
        raise Exception("Email is required")
    if '@' not in email_addr:
        raise Exception("Email format is invalid")
    if len(email_addr) > 255:
        raise Exception("Email address too long")
    return email_addr.lower().strip()

def verify_password(pwd):
    if not pwd:
        raise Exception("Password is required")
    if len(pwd) < 8:
        raise Exception("Password is too short")
    return pwd
'''
        (self.root / "user.py").write_text(user_code)
    
    def create_non_idiomatic_python(self):
        """Create non-Pythonic code for idiomatization tests."""
        code = '''
# Non-idiomatic list filtering
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
evens = []
for num in numbers:
    if num % 2 == 0:
        evens.append(num)

# Non-idiomatic string formatting
name = "Alice"
age = 30
message = "Hello, " + name + "! You are " + str(age) + " years old."

# Non-idiomatic file reading
file = open("data.txt", "r")
try:
    content = file.read()
finally:
    file.close()

# Non-idiomatic dictionary building
result = {}
for item in items:
    if item.value > 0:
        result[item.key] = item.value
'''
        (self.root / "non_idiomatic.py").write_text(code)
    
    def create_complex_conditional_nesting(self):
        """Create complex if-else for pattern injection tests."""
        code = '''
def process_payment(payment_type, amount, currency):
    if payment_type == "credit_card":
        if currency == "USD":
            if amount > 10000:
                return process_high_value_cc_usd()
            else:
                return process_standard_cc_usd()
        elif currency == "EUR":
            if amount > 9000:
                return process_high_value_cc_eur()
            else:
                return process_standard_cc_eur()
    elif payment_type == "paypal":
        if currency == "USD":
            return process_paypal_usd()
        elif currency == "EUR":
            return process_paypal_eur()
    elif payment_type == "bank_transfer":
        if currency == "USD":
            if amount > 50000:
                return process_wire_usd()
            else:
                return process_ach_usd()
    else:
        raise ValueError("Unsupported payment type")

def process_high_value_cc_usd():
    pass

def process_standard_cc_usd():
    pass

def process_high_value_cc_eur():
    pass

def process_standard_cc_eur():
    pass

def process_paypal_usd():
    pass

def process_paypal_eur():
    pass

def process_wire_usd():
    pass

def process_ach_usd():
    pass
'''
        (self.root / "complex.py").write_text(code)
    
    def create_multi_language_project(self):
        """Create a multi-language project."""
        python_code = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total
'''
        (self.root / "src" / "calculator.py").write_text(python_code)
        
        js_code = '''
function calculateTotal(items) {
    let total = 0;
    for (let item of items) {
        total += item.price * item.quantity;
    }
    return total;
}
'''
        (self.root / "src" / "calculator.js").write_text(js_code)
    
    def create_interdependent_modules(self):
        """Create modules with import dependencies."""
        utils_code = '''
from typing import List

def format_output(data: dict) -> str:
    return str(data)

def validate_input(items: List[str]) -> bool:
    return len(items) > 0
'''
        (self.root / "utils.py").write_text(utils_code)
        
        main_code = '''
from utils import format_output, validate_input

def process_items(items):
    if validate_input(items):
        result = {"items": items, "count": len(items)}
        return format_output(result)
    return "No items"
'''
        (self.root / "main.py").write_text(main_code)
    
    def create_code_with_varying_similarity(self):
        """Create code blocks with different similarity levels."""
        high_similarity = '''
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
'''
        (self.root / "high_sim.py").write_text(high_similarity)
        
        medium_similarity = '''
def compute_total(values):
    result = 0
    for value in values:
        result = result + value
    return result
'''
        (self.root / "medium_sim.py").write_text(medium_similarity)
        
        low_similarity = '''
def aggregate_data(data_points):
    accumulator = 0
    index = 0
    while index < len(data_points):
        accumulator += data_points[index]
        index += 1
    return accumulator
'''
        (self.root / "low_sim.py").write_text(low_similarity)
    
    def create_file_with_tests(self, module_name: str, test_name: str):
        """Create a module with corresponding test file."""
        module_code = '''
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
'''
        (self.root / module_name).write_text(module_code)
        
        test_code = f'''
import pytest
from {module_name.replace(".py", "")} import add, multiply

def test_add():
    assert add(2, 3) == 5

def test_multiply():
    assert multiply(2, 3) == 6
'''
        (self.root / test_name).write_text(test_code)
    
    def commit(self, message: str):
        """Create a git commit."""
        if not self.has_git:
            raise RuntimeError("Git not initialized. Use with_git=True")
        
        subprocess.run(
            ["git", "add", "."],
            cwd=self.root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.root,
            check=True,
            capture_output=True
        )
    
    def make_uncommitted_change(self, filename: str, content: str):
        """Make uncommitted changes for safety tests."""
        file_path = self.root / filename
        existing = file_path.read_text() if file_path.exists() else ""
        file_path.write_text(existing + "\n" + content)
    
    def get_committed_content(self, filename: str) -> str:
        """Get content of file from last commit."""
        if not self.has_git:
            raise RuntimeError("Git not initialized")
        
        result = subprocess.run(
            ["git", "show", f"HEAD:{filename}"],
            cwd=self.root,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        if not self.has_git:
            return False
        
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.root,
            capture_output=True,
            text=True
        )
        return len(result.stdout.strip()) > 0
    
    def get_commits(self) -> List[Dict[str, str]]:
        """Get list of commits."""
        if not self.has_git:
            return []
        
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H|%s"],
            cwd=self.root,
            capture_output=True,
            text=True
        )
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                hash_val, message = line.split('|', 1)
                commits.append({"hash": hash_val, "message": message})
        
        return commits
