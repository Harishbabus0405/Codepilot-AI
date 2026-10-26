import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PythonSecurityVisitor(ast.NodeVisitor):
    """
    AST visitor that scans Python source code for high-risk security patterns
    without executing any untrusted code.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.findings: List[Dict[str, Any]] = []

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = f"{getattr(node.func.value, 'id', '')}.{node.func.attr}"

        # 1. Arbitrary code execution (eval, exec)
        if func_name in ["eval", "exec"]:
            self.findings.append({
                "finding_type": "static_check",
                "severity": "critical",
                "category": "security_vulnerability",
                "file_path": self.file_path,
                "line_number": node.lineno,
                "is_verified": True,
                "evidence": f"Call to dangerous builtin '{func_name}()'",
                "explanation": f"Using {func_name}() can allow arbitrary remote code execution when handling dynamic inputs.",
                "suggested_remediation": "Replace dynamic evaluation with explicit parsing or a safe dispatch table.",
                "proposed_code": "# Use safe parsing or explicit dictionary lookup instead",
            })

        # 2. Insecure deserialization (pickle, marshal)
        if func_name in ["pickle.loads", "pickle.load", "marshal.loads", "_pickle.loads"]:
            self.findings.append({
                "finding_type": "static_check",
                "severity": "critical",
                "category": "security_vulnerability",
                "file_path": self.file_path,
                "line_number": node.lineno,
                "is_verified": True,
                "evidence": f"Insecure deserialization via '{func_name}()'",
                "explanation": "Deserializing untrusted pickle streams allows arbitrary code execution via object reduction protocols.",
                "suggested_remediation": "Use safe JSON serialization or cryptographically signed tokens (e.g. itsdangerous, jwt).",
                "proposed_code": "# Use json.loads(payload) instead of pickle",
            })

        # 3. Command injection via shell=True or os.system
        if func_name == "os.system":
            self.findings.append({
                "finding_type": "static_check",
                "severity": "high",
                "category": "security_vulnerability",
                "file_path": self.file_path,
                "line_number": node.lineno,
                "is_verified": True,
                "evidence": "Call to 'os.system()'",
                "explanation": "os.system executes shell commands without argument escaping, creating shell injection risks.",
                "suggested_remediation": "Use subprocess.run with argument list and shell=False.",
                "proposed_code": "subprocess.run(['command', 'arg1'], check=True, shell=False)",
            })

        if "subprocess" in func_name:
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.findings.append({
                        "finding_type": "static_check",
                        "severity": "high",
                        "category": "security_vulnerability",
                        "file_path": self.file_path,
                        "line_number": node.lineno,
                        "is_verified": True,
                        "evidence": f"{func_name}(..., shell=True)",
                        "explanation": "Executing subprocesses with shell=True is prone to shell command injection.",
                        "suggested_remediation": "Set shell=False and pass arguments as a list of strings.",
                        "proposed_code": "shell=False",
                    })

        # 4. SQL Injection in raw queries
        if func_name in ["cursor.execute", "session.execute", "connection.execute", "db.execute"]:
            if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                self.findings.append({
                    "finding_type": "static_check",
                    "severity": "critical",
                    "category": "security_vulnerability",
                    "file_path": self.file_path,
                    "line_number": node.lineno,
                    "is_verified": True,
                    "evidence": "Formatted string or string concatenation in SQL execution",
                    "explanation": "Direct string interpolation into database execution exposes the query to SQL injection.",
                    "suggested_remediation": "Use parameterized queries or ORM query abstractions (e.g., text('SELECT ... WHERE id = :id'), {'id': val}).",
                    "proposed_code": 'session.execute(text("SELECT * FROM items WHERE id = :id"), {"id": item_id})',
                })

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # 5. Hardcoded sensitive credentials
        sensitive_keywords = ["password", "secret_key", "jwt_secret", "api_key", "auth_token", "private_key"]
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                for keyword in sensitive_keywords:
                    if keyword in var_name:
                        # Check if value is a hardcoded non-placeholder string literal
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            val = node.value.value.strip()
                            # Ignore obvious template placeholders
                            if len(val) >= 8 and not val.startswith("your_") and not val.startswith("change_me") and "env" not in val.lower():
                                self.findings.append({
                                    "finding_type": "static_check",
                                    "severity": "high",
                                    "category": "security_vulnerability",
                                    "file_path": self.file_path,
                                    "line_number": node.lineno,
                                    "is_verified": True,
                                    "evidence": f"Hardcoded credential assigned to '{target.id}'",
                                    "explanation": "Hardcoded secrets in source files risk credential exposure in version control and client bundles.",
                                    "suggested_remediation": "Load credentials from environment variables using os.getenv() or a settings manager.",
                                    "proposed_code": f"{target.id} = os.getenv('{target.id.upper()}', '')",
                                })
        self.generic_visit(node)


class StaticCheckService:
    """
    Runs deterministic static analysis, AST security checks, and syntax audits
    on project workspace files without ever executing code directly on the server.
    """

    @classmethod
    def check_file(cls, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Audits an individual source code or configuration file."""
        findings: List[Dict[str, Any]] = []
        lower_path = file_path.lower()

        # 1. Python Analysis
        if lower_path.endswith(".py"):
            try:
                tree = ast.parse(content, filename=file_path)
                visitor = PythonSecurityVisitor(file_path)
                visitor.visit(tree)
                findings.extend(visitor.findings)
            except SyntaxError as e:
                findings.append({
                    "finding_type": "static_check",
                    "severity": "critical",
                    "category": "syntax_error",
                    "file_path": file_path,
                    "line_number": e.lineno,
                    "is_verified": True,
                    "evidence": f"Python SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}",
                    "explanation": f"Source file fails syntax parsing: {e.msg}",
                    "suggested_remediation": "Correct the syntax error according to standard Python grammar.",
                    "proposed_code": None,
                })

        # 2. JSON Configuration Analysis
        elif lower_path.endswith(".json"):
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                findings.append({
                    "finding_type": "static_check",
                    "severity": "high",
                    "category": "syntax_error",
                    "file_path": file_path,
                    "line_number": e.lineno,
                    "is_verified": True,
                    "evidence": f"JSON syntax error at line {e.lineno}: {e.msg}",
                    "explanation": f"JSON parser failed to decode configuration: {e.msg}",
                    "suggested_remediation": "Ensure valid JSON syntax (no trailing commas, double-quoted keys).",
                    "proposed_code": None,
                })

        # 3. JavaScript / TypeScript Analysis
        elif lower_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            lines = content.split("\n")
            for idx, line in enumerate(lines, start=1):
                # eval check
                if re.search(r"\beval\s*\(", line):
                    findings.append({
                        "finding_type": "static_check",
                        "severity": "critical",
                        "category": "security_vulnerability",
                        "file_path": file_path,
                        "line_number": idx,
                        "is_verified": True,
                        "evidence": line.strip()[:100],
                        "explanation": "Direct eval() invocation executes arbitrary client-side script.",
                        "suggested_remediation": "Avoid eval(); use JSON.parse or strict object accessors.",
                        "proposed_code": "// Replace eval with safe parser",
                    })

                # dangerouslySetInnerHTML check
                if "dangerouslySetInnerHTML" in line:
                    findings.append({
                        "finding_type": "static_check",
                        "severity": "high",
                        "category": "security_vulnerability",
                        "file_path": file_path,
                        "line_number": idx,
                        "is_verified": True,
                        "evidence": line.strip()[:100],
                        "explanation": "dangerouslySetInnerHTML bypasses React's XSS sanitization protections.",
                        "suggested_remediation": "Sanitize HTML using DOMPurify before injection or render safe JSX elements.",
                        "proposed_code": "<span>{DOMPurify.sanitize(content)}</span>",
                    })

                # Plain HTTP URLs
                if re.search(r"http://(?!(localhost|127\.0\.0\.1))", line):
                    findings.append({
                        "finding_type": "static_check",
                        "severity": "low",
                        "category": "security_vulnerability",
                        "file_path": file_path,
                        "line_number": idx,
                        "is_verified": True,
                        "evidence": line.strip()[:100],
                        "explanation": "Insecure HTTP URL found. Unencrypted traffic is vulnerable to eavesdropping and MITM attacks.",
                        "suggested_remediation": "Use encrypted HTTPS endpoints.",
                        "proposed_code": line.replace("http://", "https://").strip(),
                    })

        return findings

    @classmethod
    def audit_workspace(cls, files: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Audits all files in the project workspace manifest and checks for missing tests.
        """
        all_findings: List[Dict[str, Any]] = []
        has_tests = False

        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            if "test" in path.lower() or path.startswith("tests/"):
                has_tests = True
            file_findings = cls.check_file(path, content)
            all_findings.extend(file_findings)

        # Check for missing test coverage
        if not has_tests and len(files) > 1:
            all_findings.append({
                "finding_type": "qa_coverage",
                "severity": "medium",
                "category": "missing_test_coverage",
                "file_path": "tests/",
                "line_number": None,
                "is_verified": True,
                "evidence": "No test files (e.g. test_*.py or *.test.tsx) detected in the project workspace.",
                "explanation": "The project lacks automated unit or integration tests, reducing confidence in code correctness.",
                "suggested_remediation": "Generate automated tests to verify core routes, data models, and component rendering.",
                "proposed_code": "# Generate test suite via QA Agent",
            })

        return all_findings


ASTStaticCheckService = StaticCheckService
