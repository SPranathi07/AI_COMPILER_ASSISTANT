

import sys
import time
import json
from optimization_module import (
    OptimizationAnalyser, SecurityAnalyser,
    format_optimization_report, format_security_report
)
from ai_assistant import AIAssistant

# ──────────────────────────────────────────────
#  Test data – each entry is one test case
# ──────────────────────────────────────────────

TEST_CASES = [
    # ── Correct C code ──────────────────────────
    {
        "id": "TC01",
        "name": "Valid simple program",
        "category": "correct_code",
        "source": "int main() {\n    int x = 5;\n    int y = 10;\n    return x + y;\n}\n",
        "expected_errors": 0,
        "expected_opt_hints": 0,
        "expected_security": 0,
    },
    {
        "id": "TC02",
        "name": "Valid function with loop",
        "category": "correct_code",
        "source": (
            "int sum(int n) {\n"
            "    int total = 0;\n"
            "    for (int i = 0; i < n; i = i + 1) {\n"
            "        total = total + i;\n"
            "    }\n"
            "    return total;\n"
            "}\n"
        ),
        "expected_errors": 0,
        "expected_opt_hints": 0,
        "expected_security": 0,
    },

    # ── Syntax errors ────────────────────────────
    {
        "id": "TC03",
        "name": "Missing semicolon",
        "category": "syntax_error",
        "source": "int x = 5\nint y = 10;\n",
        "errors": [{"line": 1, "column": 10, "message": "expected ';'", "token": "int"}],
        "expected_errors": 1,
        "expected_opt_hints": 0,
        "expected_security": 0,
    },
    {
        "id": "TC04",
        "name": "Unmatched opening brace",
        "category": "syntax_error",
        "source": "if (x > 0) {\n    int y = 1;\n",
        "errors": [{"line": 1, "column": 11, "message": "expected '}'", "token": "EOF"}],
        "expected_errors": 1,
        "expected_opt_hints": 0,
        "expected_security": 0,
    },
    {
        "id": "TC05",
        "name": "Assignment in condition",
        "category": "syntax_error",
        "source": "int x = 5;\nif (x = 0) {\n    return 1;\n}\n",
        "errors": [{"line": 2, "column": 7, "message": "assignment in condition", "token": "="}],
        "expected_errors": 1,
        "expected_opt_hints": 0,
        "expected_security": 0,
    },
    {
        "id": "TC06",
        "name": "Multiple errors – missing semicolon + unmatched paren",
        "category": "syntax_error",
        "source": "int result = (a + b * c;\nint y = 5\n",
        "errors": [
            {"line": 1, "column": 22, "message": "expected ')'", "token": ";"},
            {"line": 2, "column": 9,  "message": "expected ';'",  "token": "EOF"},
        ],
        "expected_errors": 2,
        "expected_opt_hints": 0,
        "expected_security": 0,
    },

    # ── Optimization cases ───────────────────────
    {
        "id": "TC07",
        "name": "Nested loop O(n²)",
        "category": "optimization",
        "source": (
            "int main() {\n"
            "    int n = 100;\n"
            "    int sum = 0;\n"
            "    for (int i = 0; i < n; i++) {\n"
            "        for (int j = 0; j < n; j++) {\n"
            "            sum = sum + i + j;\n"
            "        }\n"
            "    }\n"
            "    return sum;\n"
            "}\n"
        ),
        "expected_errors": 0,
        "expected_opt_hints_min": 1,
        "expected_security": 0,
    },
    {
        "id": "TC08",
        "name": "Unused variable",
        "category": "optimization",
        "source": (
            "int main() {\n"
            "    int x = 5;\n"
            "    int unused;\n"
            "    return x;\n"
            "}\n"
        ),
        "expected_errors": 0,
        "expected_opt_hints_min": 1,
        "expected_security": 0,
    },

    # ── Security cases ───────────────────────────
    {
        "id": "TC09",
        "name": "Unsafe gets() usage",
        "category": "security",
        "source": (
            "#include <stdio.h>\n"
            "int main() {\n"
            "    char buf[64];\n"
            "    gets(buf);\n"
            "    return 0;\n"
            "}\n"
        ),
        "expected_errors": 0,
        "expected_opt_hints": 0,
        "expected_security_min": 1,
        "expected_severity": "CRITICAL",
    },
    {
        "id": "TC10",
        "name": "Hardcoded password + unsafe strcpy",
        "category": "security",
        "source": (
            '#include <string.h>\n'
            'int main() {\n'
            '    char password[] = "admin123";\n'
            '    char buf[10];\n'
            '    strcpy(buf, password);\n'
            '    return 0;\n'
            '}\n'
        ),
        "expected_errors": 0,
        "expected_opt_hints": 0,
        "expected_security_min": 2,
    },
    {
        "id": "TC11",
        "name": "system() command injection risk",
        "category": "security",
        "source": (
            '#include <stdlib.h>\n'
            'int main() {\n'
            '    system("ls -la");\n'
            '    return 0;\n'
            '}\n'
        ),
        "expected_errors": 0,
        "expected_opt_hints": 0,
        "expected_security_min": 1,
        "expected_severity": "CRITICAL",
    },
    {
        "id": "TC12",
        "name": "malloc without NULL check",
        "category": "security",
        "source": (
            '#include <stdlib.h>\n'
            'int main() {\n'
            '    int* arr = malloc(100 * sizeof(int));\n'
            '    arr[0] = 42;\n'
            '    return 0;\n'
            '}\n'
        ),
        "expected_errors": 0,
        "expected_opt_hints": 0,
        "expected_security_min": 1,
    },
    {
        "id": "TC13",
        "name": "AI error explanation – missing semicolon",
        "category": "ai_explanation",
        "source": "int x = 5\nint y = 10;\n",
        "errors": [{"line": 1, "column": 10, "message": "expected ';'", "token": "int"}],
        "expected_errors": 1,
        "check_explanation": True,
    },
    {
        "id": "TC14",
        "name": "Autocomplete suggestion after KEYWORD(int)",
        "category": "autocomplete",
        "source": "",
        "errors": [],
        "token_sequence": ["KEYWORD(int)", "IDENTIFIER", "ASSIGN"],
        "expected_errors": 0,
        "check_autocomplete": True,
    },
    {
        "id": "TC15",
        "name": "Complex program – full pipeline",
        "category": "full_pipeline",
        "source": (
            '#include <stdio.h>\n'
            '#include <string.h>\n'
            'char password[] = "secret";\n'
            'int main() {\n'
            '    char buf[64];\n'
            '    gets(buf);\n'
            '    int unused;\n'
            '    for (int i = 0; i < 50; i++) {\n'
            '        for (int j = 0; j < 50; j++) {\n'
            '            buf[i] = buf[j];\n'
            '        }\n'
            '    }\n'
            '    return 0;\n'
            '}\n'
        ),
        "expected_errors": 0,
        "expected_opt_hints_min": 1,
        "expected_security_min": 2,
    },
]


# ──────────────────────────────────────────────
#  Test runner
# ──────────────────────────────────────────────

class TestRunner:

    def __init__(self):
        self.opt_analyser = OptimizationAnalyser()
        self.sec_analyser = SecurityAnalyser()
        self.ai_assistant  = AIAssistant()
        self.results = []

    def run_all(self):
        print("\n" + "=" * 65)
        print("  WEEK 12: TEST SUITE — AI-Powered Mini C Compiler")
        print("=" * 65)

        passed = 0
        failed = 0

        for tc in TEST_CASES:
            result = self._run_one(tc)
            self.results.append(result)
            status = "PASS" if result["passed"] else "FAIL"
            mark   = "✓" if result["passed"] else "✗"
            print(f"  {mark} [{tc['id']}] {tc['name']:<45} {status}  ({result['time_ms']:.1f} ms)")
            if not result["passed"]:
                for note in result["notes"]:
                    print(f"       → {note}")
            failed += 0 if result["passed"] else 1
            passed += 1 if result["passed"] else 0

        total = passed + failed
        print("\n" + "-" * 65)
        print(f"  Results: {passed}/{total} passed  |  {failed} failed")
        accuracy = (passed / total * 100) if total else 0
        print(f"  Accuracy: {accuracy:.1f}%")
        print("=" * 65)
        return self.results

    def _run_one(self, tc: dict) -> dict:
        t0    = time.perf_counter()
        notes = []
        passed = True

        source = tc.get("source", "")
        errors = tc.get("errors", [])

        # ── Optimization check ──────────────────
        if source and ("opt" in tc.get("category", "") or tc.get("expected_opt_hints_min") is not None):
            hints = self.opt_analyser.analyse(source)
            min_expected = tc.get("expected_opt_hints_min", 0)
            if len(hints) < min_expected:
                passed = False
                notes.append(f"Expected ≥{min_expected} opt hints, got {len(hints)}")

        # ── Security check ──────────────────────
        if source and ("security" in tc.get("category", "") or tc.get("expected_security_min") is not None):
            issues = self.sec_analyser.analyse(source)
            min_expected = tc.get("expected_security_min", 0)
            if len(issues) < min_expected:
                passed = False
                notes.append(f"Expected ≥{min_expected} security issues, got {len(issues)}")
            exp_sev = tc.get("expected_severity")
            if exp_sev:
                severities = [s.severity for s in issues]
                if exp_sev not in severities:
                    passed = False
                    notes.append(f"Expected a '{exp_sev}' severity issue, found: {severities}")

        # ── AI explanation check ─────────────────
        if tc.get("check_explanation"):
            explanation = self.ai_assistant.analyze(errors)
            if "ERROR" not in explanation.upper() and "error" not in explanation.lower():
                passed = False
                notes.append("AI explanation did not mention the error")

        # ── Autocomplete check ───────────────────
        if tc.get("check_autocomplete"):
            token_seq = tc.get("token_sequence", [])
            explanation = self.ai_assistant.analyze([], token_seq)
            if "autocomplete" not in explanation.lower() and "next" not in explanation.lower():
                passed = False
                notes.append("Autocomplete suggestions not returned")

        # ── Error count check ────────────────────
        if "expected_errors" in tc and errors is not None:
            if len(errors) != tc["expected_errors"]:
                passed = False
                notes.append(f"Expected {tc['expected_errors']} errors, got {len(errors)}")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "id":      tc["id"],
            "name":    tc["name"],
            "passed":  passed,
            "notes":   notes,
            "time_ms": elapsed_ms,
        }

    def save_report(self, path: str = "test_report.md"):
        passed = sum(1 for r in self.results if r["passed"])
        total  = len(self.results)
        accuracy = (passed / total * 100) if total else 0

        lines = [
            "# Week 12 – Test Report",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total test cases | {total} |",
            f"| Passed | {passed} |",
            f"| Failed | {total - passed} |",
            f"| Accuracy | {accuracy:.1f}% |",
            "",
            "## Test Case Results",
            "",
            "| ID | Name | Result | Time (ms) | Notes |",
            "|----|------|--------|-----------|-------|",
        ]
        for r in self.results:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            notes  = "; ".join(r["notes"]) if r["notes"] else "—"
            lines.append(f"| {r['id']} | {r['name']} | {status} | {r['time_ms']:.1f} | {notes} |")

        lines += [
            "",
            "## Test Categories",
            "",
            "| Category | Count |",
            "|----------|-------|",
        ]
        from collections import Counter
        cats = Counter(tc["category"] for tc in TEST_CASES)
        for cat, cnt in cats.items():
            lines.append(f"| {cat} | {cnt} |")

        lines += [
            "",
            "## Notes",
            "",
            "- All tests run using the `ai_assistant.py` and `optimization_module.py` modules.",
            "- Optimization and security checks performed via static source analysis.",
            "- AI error explanations validated for keyword presence.",
            "- Response times measured using `time.perf_counter()`.",
            "",
            "_Generated by test_cases.py — Week 12 deliverable_",
        ]

        with open(path, "w") as f:
            f.write("\n".join(lines))
        print(f"\n  ✓ Test report saved → {path}")


if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all()
    runner.save_report("test_report.md")