import sys
import os
import pickle
import ai_assistant
from run_compiler import run_compiler, build_compiler
from ai_assistant import AIAssistant
from optimization_module import (
    OptimizationAnalyser, SecurityAnalyser,
    format_optimization_report, format_security_report
)


class TokenFeatureExtractor:
    def __init__(self):
        self.vectorizer = None

    def transform(self, data):
        if hasattr(self, 'vectorizer') and self.vectorizer is not None:
            return self.vectorizer.transform(data)
        for attr_value in self.__dict__.values():
            if hasattr(attr_value, 'transform'):
                return attr_value.transform(data)
        raise AttributeError("No transformable vectorizer found in loaded model.")

ai_assistant.TokenFeatureExtractor = TokenFeatureExtractor


def compile_and_explain(source_file):
    print(f"\n{'='*55}")
    print(f"  AI-Powered Mini C Compiler")
    print(f"  Analyzing: {source_file}")
    print(f"{'='*55}\n")

    if not os.path.exists(source_file):
        print(f"Error: File '{source_file}' not found.")
        return

    compiler_exists = (os.path.exists("compiler") or os.path.exists("compiler.exe"))
    if not compiler_exists:
        success = build_compiler()
        if not success:
            return

    try:
        with open(source_file) as f:
            source_code = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    result         = run_compiler(source_file)
    errors         = result["errors"]
    token_sequence = result["tokens"]

    if token_sequence:
        print(f"Tokens ({len(token_sequence)} total):")
        print(f"  {' '.join(token_sequence[:10])}")
        if len(token_sequence) > 10:
            print(f"  ... and {len(token_sequence) - 10} more")
        print()

    # SECTION 1: Syntax errors
    print("=" * 55)
    print("  SECTION 1: Syntax Analysis")
    print("=" * 55)
    try:
        assistant   = AIAssistant()
        explanation = assistant.analyze(errors, token_sequence)
        print(explanation)
    except Exception as e:
        print(f"AI Assistant Error: {e}")

    if errors:
        print("\nYour source code:")
        print("-" * 55)
        try:
            lines = source_code.splitlines()
            for i, line in enumerate(lines, 1):
                marker = "  <- ERROR HERE" if any(e.get("line") == i for e in errors) else ""
                print(f"  {i:3}: {line}{marker}")
        except Exception:
            pass
        print("-" * 55)

    # SECTION 2: Optimization
    print("\n" + "=" * 55)
    print("  SECTION 2: Optimization Analysis")
    print("=" * 55)
    hints = []
    try:
        opt_analyser = OptimizationAnalyser()
        hints        = opt_analyser.analyse(source_code)
        print(format_optimization_report(hints))
    except Exception as e:
        print(f"Optimization Analysis Error: {e}")

    # SECTION 3: Security
    print("\n" + "=" * 55)
    print("  SECTION 3: Security Analysis")
    print("=" * 55)
    issues = []
    try:
        sec_analyser = SecurityAnalyser()
        issues       = sec_analyser.analyse(source_code)
        print(format_security_report(issues))
    except Exception as e:
        print(f"Security Analysis Error: {e}")

    # Summary
    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    n_errors  = len(errors)
    n_hints   = len(hints)
    n_issues  = len(issues)
    criticals = sum(1 for s in issues if s.severity == "CRITICAL")

    print(f"  Syntax errors     : {n_errors}")
    print(f"  Optimization hints: {n_hints}")
    print(f"  Security issues   : {n_issues}  ({criticals} CRITICAL)")

    if n_errors == 0 and n_hints == 0 and n_issues == 0:
        print("\n  ✓ Code looks clean — no issues detected!")
    elif n_errors == 0:
        print("\n  ✓ Code compiles correctly.")
        if criticals > 0:
            print(f"  ⚠ Fix {criticals} CRITICAL security issue(s) before deploying.")
    else:
        print(f"\n  ✗ Fix {n_errors} syntax error(s) before the code can run.")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <source_file.c>")
        sys.exit(1)
    compile_and_explain(sys.argv[1])