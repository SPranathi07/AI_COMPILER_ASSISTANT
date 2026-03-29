import re
import json
import csv
import argparse
from dataclasses import dataclass, field, asdict
from typing import List
from pathlib import Path
from datetime import datetime

TOKEN_PATTERNS = [
    ("KEYWORD(int)",    r'\bint\b'),
    ("KEYWORD(float)",  r'\bfloat\b'),
    ("KEYWORD(void)",   r'\bvoid\b'),
    ("KEYWORD(if)",     r'\bif\b'),
    ("KEYWORD(else)",   r'\belse\b'),
    ("KEYWORD(while)",  r'\bwhile\b'),
    ("KEYWORD(for)",    r'\bfor\b'),
    ("KEYWORD(return)", r'\breturn\b'),
    ("KEYWORD(char)",   r'\bchar\b'),
    ("IDENTIFIER",      r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ("FLOAT_LITERAL",   r'\b\d+\.\d+\b'),
    ("INT_LITERAL",     r'\b\d+\b'),
    ("EQ",              r'=='),
    ("NEQ",             r'!='),
    ("LTE",             r'<='),
    ("GTE",             r'>='),
    ("AND",             r'&&'),
    ("OR",              r'\|\|'),
    ("ASSIGN",          r'=(?!=)'),
    ("LT",              r'<'),
    ("GT",              r'>'),
    ("PLUS",            r'\+'),
    ("MINUS",           r'-'),
    ("MULTIPLY",        r'\*'),
    ("DIVIDE",          r'/'),
    ("MODULO",          r'%'),
    ("NOT",             r'!'),
    ("SEMICOLON",       r';'),
    ("COMMA",           r','),
    ("LPAREN",          r'\('),
    ("RPAREN",          r'\)'),
    ("LBRACE",          r'\{'),
    ("RBRACE",          r'\}'),
    ("LBRACKET",        r'\['),
    ("RBRACKET",        r'\]'),
    ("WHITESPACE",      r'[ \t\n\r]+'),
    ("UNKNOWN",         r'.'),
]

COMPILED_PATTERNS = [
    (name, re.compile(pat, re.DOTALL))
    for name, pat in TOKEN_PATTERNS
]

@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int
    def to_dict(self):
        return asdict(self)

@dataclass
class ErrorLabel:
    error_type: str
    line: int
    column: int
    description: str
    suggestion: str
    def to_dict(self):
        return asdict(self)

@dataclass
class CodeSample:
    sample_id: str
    source_code: str
    is_correct: bool
    errors: List[ErrorLabel] = field(default_factory=list)
    tokens: List[Token] = field(default_factory=list)
    token_sequence: List[str] = field(default_factory=list)
    category: str = "general"
    difficulty: str = "beginner"
    def to_dict(self):
        return {
            "sample_id":      self.sample_id,
            "source_code":    self.source_code,
            "is_correct":     self.is_correct,
            "errors":         [e.to_dict() for e in self.errors],
            "tokens":         [t.to_dict() for t in self.tokens],
            "token_sequence": self.token_sequence,
            "category":       self.category,
            "difficulty":     self.difficulty,
        }

class Lexer:
    def tokenize(self, source: str) -> List[Token]:
        tokens = []
        pos = 0
        line = 1
        col = 1
        while pos < len(source):
            match = None
            for token_type, pattern in COMPILED_PATTERNS:
                match = pattern.match(source, pos)
                if match:
                    value = match.group(0)
                    if token_type not in ("WHITESPACE", "COMMENT"):
                        tokens.append(Token(type=token_type, value=value, line=line, column=col))
                    newlines = value.count('\n')
                    if newlines:
                        line += newlines
                        col = len(value) - value.rfind('\n')
                    else:
                        col += len(value)
                    pos = match.end()
                    break
            if not match:
                pos += 1
        return tokens

class SyntaxErrorDetector:
    def detect(self, source: str, tokens: List[Token]) -> List[ErrorLabel]:
        errors = []
        errors.extend(self._check_missing_semicolons(source, tokens))
        errors.extend(self._check_unmatched_braces(tokens))
        errors.extend(self._check_unmatched_parens(tokens))
        errors.extend(self._check_assignment_in_condition(tokens))
        return errors

    def _check_missing_semicolons(self, source, tokens) -> List[ErrorLabel]:
        errors = []
        lines = source.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if (stripped and
                not stripped.endswith(';') and
                not stripped.endswith('{') and
                not stripped.endswith('}') and
                not stripped.endswith(')') and
                not stripped.startswith('//') and
                not stripped.startswith('#') and
                re.match(r'^[a-zA-Z_]', stripped) and
                re.search(r'[a-zA-Z0-9_\)"\']$', stripped)):
                if not re.match(r'^(if|else|while|for|void|int|float|char|struct)\s*[\(\{]', stripped):
                    if re.search(r'=\s*.+$', stripped) or re.search(r'\)\s*$', stripped):
                        errors.append(ErrorLabel(
                            error_type="MISSING_SEMICOLON",
                            line=i,
                            column=len(line),
                            description=f"Statement on line {i} appears to be missing a semicolon.",
                            suggestion=f"Add ';' at the end of line {i}: `{stripped};`"
                        ))
        return errors

    def _check_unmatched_braces(self, tokens) -> List[ErrorLabel]:
        stack = []
        errors = []
        for tok in tokens:
            if tok.type == "LBRACE":
                stack.append(tok)
            elif tok.type == "RBRACE":
                if stack:
                    stack.pop()
                else:
                    errors.append(ErrorLabel(
                        error_type="UNMATCHED_RBRACE",
                        line=tok.line, column=tok.column,
                        description=f"Unexpected '}}' at line {tok.line} with no matching '{{'.",
                        suggestion="Remove the extra '}' or add a matching '{' earlier."
                    ))
        for tok in stack:
            errors.append(ErrorLabel(
                error_type="UNMATCHED_LBRACE",
                line=tok.line, column=tok.column,
                description=f"Opening '{{' at line {tok.line} has no matching '}}'.",
                suggestion="Add a closing '}' to close the block opened here."
            ))
        return errors

    def _check_unmatched_parens(self, tokens) -> List[ErrorLabel]:
        stack = []
        errors = []
        for tok in tokens:
            if tok.type == "LPAREN":
                stack.append(tok)
            elif tok.type == "RPAREN":
                if stack:
                    stack.pop()
                else:
                    errors.append(ErrorLabel(
                        error_type="UNMATCHED_RPAREN",
                        line=tok.line, column=tok.column,
                        description=f"Unexpected ')' at line {tok.line}.",
                        suggestion="Remove the extra ')' or add a matching '(' earlier."
                    ))
        for tok in stack:
            errors.append(ErrorLabel(
                error_type="UNMATCHED_LPAREN",
                line=tok.line, column=tok.column,
                description=f"Opening '(' at line {tok.line} has no matching ')'.",
                suggestion="Add a closing ')' to match this parenthesis."
            ))
        return errors

    def _check_assignment_in_condition(self, tokens) -> List[ErrorLabel]:
        errors = []
        i = 0
        while i < len(tokens) - 2:
            if tokens[i].type in ("KEYWORD(if)", "KEYWORD(while)"):
                depth = 0
                j = i + 1
                while j < len(tokens):
                    if tokens[j].type == "LPAREN":
                        depth += 1
                    elif tokens[j].type == "RPAREN":
                        depth -= 1
                        if depth == 0:
                            break
                    elif tokens[j].type == "ASSIGN" and depth > 0:
                        errors.append(ErrorLabel(
                            error_type="ASSIGNMENT_IN_CONDITION",
                            line=tokens[j].line, column=tokens[j].column,
                            description=f"Assignment '=' used inside condition at line {tokens[j].line}. Likely meant '=='.",
                            suggestion="Replace '=' with '==' to compare values instead of assigning."
                        ))
                    j += 1
            i += 1
        return errors

RAW_SAMPLES = [
    {
        "id": "C001", "correct": True,
        "category": "variable_declaration", "difficulty": "beginner",
        "code": "int x = 5;\nint y = 10;\nint sum = x + y;\n"
    },
    {
        "id": "C002", "correct": True,
        "category": "if_statement", "difficulty": "beginner",
        "code": "int a = 3;\nif (a > 0) {\n    return 1;\n} else {\n    return 0;\n}\n"
    },
    {
        "id": "C003", "correct": True,
        "category": "while_loop", "difficulty": "beginner",
        "code": "int i = 0;\nwhile (i < 10) {\n    i = i + 1;\n}\n"
    },
    {
        "id": "C004", "correct": True,
        "category": "for_loop", "difficulty": "intermediate",
        "code": "int sum = 0;\nfor (int i = 0; i < 5; i = i + 1) {\n    sum = sum + i;\n}\n"
    },
    {
        "id": "C005", "correct": True,
        "category": "function", "difficulty": "intermediate",
        "code": "int add(int a, int b) {\n    return a + b;\n}\n"
    },
    {
        "id": "C006", "correct": True,
        "category": "nested_if", "difficulty": "intermediate",
        "code": "int x = 5;\nif (x > 0) {\n    if (x < 10) {\n        int y = x * 2;\n    }\n}\n"
    },
    {
        "id": "C007", "correct": True,
        "category": "array", "difficulty": "intermediate",
        "code": "int arr[5];\narr[0] = 1;\narr[1] = 2;\nint val = arr[0] + arr[1];\n"
    },
    {
        "id": "C008", "correct": True,
        "category": "function", "difficulty": "advanced",
        "code": "int factorial(int n) {\n    if (n == 0) {\n        return 1;\n    }\n    return n * factorial(n - 1);\n}\n"
    },
    {
        "id": "C009", "correct": True,
        "category": "for_if_else", "difficulty": "intermediate",
        "code": "int main() {\n    int x;\n    int y;\n    x = 1;\n    for (int i = 0; i <= x; i = i + 1) {\n        x = x + 1;\n    }\n    if (x >= 1) {\n        y = x + 5;\n    } else {\n        y = x;\n    }\n    return 0;\n}\n"
    },
    {
        "id": "C010", "correct": True,
        "category": "void_function", "difficulty": "beginner",
        "code": "void greet(int x) {\n    int result = x + 1;\n    return;\n}\n"
    },
    {
        "id": "C011", "correct": True,
        "category": "while_loop", "difficulty": "intermediate",
        "code": "int main() {\n    int x = 0;\n    while (x < 5) {\n        x = x + 1;\n    }\n    return x;\n}\n"
    },
    {
        "id": "C012", "correct": True,
        "category": "nested_loop", "difficulty": "advanced",
        "code": "int main() {\n    int sum = 0;\n    for (int i = 0; i < 3; i = i + 1) {\n        for (int j = 0; j < 3; j = j + 1) {\n            sum = sum + i + j;\n        }\n    }\n    return sum;\n}\n"
    },
    {
        "id": "E001", "correct": False,
        "category": "missing_semicolon", "difficulty": "beginner",
        "code": "int x = 5\nint y = 10;\nint sum = x + y;\n"
    },
    {
        "id": "E002", "correct": False,
        "category": "unmatched_brace", "difficulty": "beginner",
        "code": "if (x > 0) {\n    int y = 1;\n"
    },
    {
        "id": "E003", "correct": False,
        "category": "assignment_in_condition", "difficulty": "beginner",
        "code": "int x = 5;\nif (x = 0) {\n    return 1;\n}\n"
    },
    {
        "id": "E004", "correct": False,
        "category": "unmatched_paren", "difficulty": "beginner",
        "code": "int result = (a + b * c;\n"
    },
    {
        "id": "E005", "correct": False,
        "category": "missing_semicolon", "difficulty": "intermediate",
        "code": "int sum = 0\nfor (int i = 0; i < 5; i = i + 1) {\n    sum = sum + i;\n}\n"
    },
    {
        "id": "E006", "correct": False,
        "category": "extra_brace", "difficulty": "intermediate",
        "code": "int x = 5;\nif (x > 0) {\n    return x;\n}\n}\n"
    },
    {
        "id": "E007", "correct": False,
        "category": "assignment_in_condition", "difficulty": "intermediate",
        "code": "int i = 0;\nwhile (i = 10) {\n    i = i + 1;\n}\n"
    },
    {
        "id": "E008", "correct": False,
        "category": "missing_semicolon", "difficulty": "advanced",
        "code": "int factorial(int n) {\n    if (n == 0) {\n        return 1\n    }\n    return n * factorial(n - 1);\n}\n"
    },
    {
        "id": "E009", "correct": False,
        "category": "multiple_errors", "difficulty": "advanced",
        "code": "int add(int a, int b {\n    return a + b\n}\n"
    },
    {
        "id": "E010", "correct": False,
        "category": "unmatched_brace", "difficulty": "beginner",
        "code": "void greet() {\n    int x = 1;\n\n"
    },
    {
        "id": "E011", "correct": False,
        "category": "missing_semicolon", "difficulty": "intermediate",
        "code": "int main() {\n    int x;\n    int y;\n    x = 1;\n    for (int i = 0; i <= x; i = i + 1) {\n        x = x + 1;\n    }\n    if (x >= 1) {\n        y = x + 5;\n    } else {\n        y = x\n    }\n    return 0;\n}\n"
    },
    {
        "id": "E012", "correct": False,
        "category": "assignment_in_condition", "difficulty": "intermediate",
        "code": "int main() {\n    int x = 5;\n    if (x = 1) {\n        return x;\n    }\n    return 0;\n}\n"
    },
    {
        "id": "E013", "correct": False,
        "category": "unmatched_brace", "difficulty": "intermediate",
        "code": "int main() {\n    int x = 0;\n    while (x < 5) {\n        x = x + 1;\n    return x;\n}\n"
    },
]

class DatasetBuilder:
    def __init__(self):
        self.lexer = Lexer()
        self.detector = SyntaxErrorDetector()

    def build(self) -> List[CodeSample]:
        samples = []
        for raw in RAW_SAMPLES:
            tokens = self.lexer.tokenize(raw["code"])
            errors = [] if raw["correct"] else self.detector.detect(raw["code"], tokens)
            sample = CodeSample(
                sample_id=raw["id"],
                source_code=raw["code"],
                is_correct=raw["correct"],
                errors=errors,
                tokens=tokens,
                token_sequence=[t.type for t in tokens],
                category=raw["category"],
                difficulty=raw["difficulty"],
            )
            samples.append(sample)
        return samples

    def save_json(self, samples: List[CodeSample], path: str):
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_samples": len(samples),
                "correct_samples": sum(1 for s in samples if s.is_correct),
                "incorrect_samples": sum(1 for s in samples if not s.is_correct),
                "version": "1.0.0"
            },
            "samples": [s.to_dict() for s in samples]
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ JSON dataset saved → {path}")

    def save_csv(self, samples: List[CodeSample], path: str):
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "sample_id", "is_correct", "category", "difficulty",
                "error_count", "error_types", "token_count",
                "token_sequence", "source_code"
            ])
            for s in samples:
                error_types = "|".join(e.error_type for e in s.errors)
                token_seq   = " ".join(s.token_sequence)
                writer.writerow([
                    s.sample_id, int(s.is_correct), s.category, s.difficulty,
                    len(s.errors), error_types, len(s.tokens),
                    token_seq, s.source_code.replace('\n', '\\n')
                ])
        print(f"✓ CSV dataset saved  → {path}")

    def save_token_sequences(self, samples: List[CodeSample], path: str):
        with open(path, 'w') as f:
            for s in samples:
                label = "CORRECT" if s.is_correct else "INCORRECT"
                seq = " ".join(s.token_sequence)
                f.write(f"{label}\t{seq}\n")
        print(f"✓ Token sequences    → {path}")

    def print_stats(self, samples: List[CodeSample]):
        total   = len(samples)
        correct = sum(1 for s in samples if s.is_correct)
        errors  = {}
        cats    = {}
        for s in samples:
            cats[s.category] = cats.get(s.category, 0) + 1
            for e in s.errors:
                errors[e.error_type] = errors.get(e.error_type, 0) + 1
        print("\n" + "="*50)
        print("  DATASET STATISTICS")
        print("="*50)
        print(f"  Total samples  : {total}")
        print(f"  Correct        : {correct}")
        print(f"  Incorrect      : {total - correct}")
        print(f"\n  Error type distribution:")
        for etype, count in sorted(errors.items(), key=lambda x: -x[1]):
            print(f"    {etype:<35} {count}")
        print(f"\n  Category distribution:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {cat:<35} {count}")
        print("="*50 + "\n")

def main():
    parser = argparse.ArgumentParser(description="AI Compiler Dataset Builder")
    parser.add_argument('--build',    action='store_true')
    parser.add_argument('--tokenize', action='store_true')
    parser.add_argument('--stats',    action='store_true')
    parser.add_argument('--out',      default='.')
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    builder = DatasetBuilder()
    samples = builder.build()

    if args.build or not any([args.build, args.tokenize, args.stats]):
        builder.save_json(samples,            str(out / "dataset.json"))
        builder.save_csv(samples,             str(out / "dataset.csv"))
        builder.save_token_sequences(samples, str(out / "token_sequences.txt"))
        builder.print_stats(samples)
    elif args.tokenize:
        builder.save_token_sequences(samples, str(out / "token_sequences.txt"))
    elif args.stats:
        builder.print_stats(samples)

if __name__ == "__main__":
    main()