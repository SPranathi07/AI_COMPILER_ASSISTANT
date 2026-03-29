"""
Week 11: Optimization Module + Security Analysis
AI-Powered Mini C Compiler Project
"""

import re
from dataclasses import dataclass, field
from typing import List


# ─────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────

@dataclass
class OptimizationHint:
    category:    str
    severity:    str          # "LOW" | "MEDIUM" | "HIGH"
    line:        int
    description: str
    suggestion:  str
    example:     str = ""

@dataclass
class SecurityIssue:
    category:    str
    severity:    str          # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    line:        int
    description: str
    suggestion:  str
    cwe:         str = ""     # CWE reference e.g. "CWE-119"


# ─────────────────────────────────────────────
#  Optimization Analyser
# ─────────────────────────────────────────────

class OptimizationAnalyser:
    """Identifies inefficient code patterns in C source."""

    def analyse(self, source: str) -> List[OptimizationHint]:
        hints = []
        lines = source.split("\n")
        hints.extend(self._check_nested_loops(lines))
        hints.extend(self._check_repeated_computation(lines))
        hints.extend(self._check_unused_variables(lines))
        hints.extend(self._check_magic_numbers(lines))
        hints.extend(self._check_redundant_condition(lines))
        hints.extend(self._check_unnecessary_return(lines))
        return hints

    # -- individual checks --------------------------------------------------

    def _check_nested_loops(self, lines: List[str]) -> List[OptimizationHint]:
        hints = []
        loop_depth = 0
        loop_start_lines = []
        loop_kw = re.compile(r'\b(for|while)\b')
        lbrace   = re.compile(r'\{')
        rbrace   = re.compile(r'\}')
        open_cnt = 0

        for i, line in enumerate(lines, 1):
            if loop_kw.search(line):
                loop_depth += 1
                loop_start_lines.append(i)
                if loop_depth == 2:
                    hints.append(OptimizationHint(
                        category="NESTED_LOOP",
                        severity="HIGH",
                        line=i,
                        description=(
                            "Nested loop detected. Two loops inside each other create "
                            "O(n²) time complexity, which becomes very slow for large inputs."
                        ),
                        suggestion=(
                            "Consider refactoring: precompute values before the outer loop, "
                            "use a hash map/lookup table, or restructure the algorithm to "
                            "reduce the inner loop's work."
                        ),
                        example=(
                            "Bad:  for(i=0;i<n;i++) for(j=0;j<n;j++) sum+=a[i]*b[j];\n"
                            "Good: Precompute sumA and sumB outside the loops."
                        )
                    ))
            open_cnt  += lbrace.subn("", line)[1]
            close_cnt  = rbrace.subn("", line)[1]
            open_cnt  -= close_cnt
            if close_cnt and loop_depth and open_cnt <= 0:
                loop_depth = max(0, loop_depth - 1)
        return hints

    def _check_repeated_computation(self, lines: List[str]) -> List[OptimizationHint]:
        hints = []
        inside_loop = False
        loop_kw  = re.compile(r'\b(for|while)\b')
        func_call = re.compile(r'(\b\w+\s*\([^)]*\))')

        for i, line in enumerate(lines, 1):
            if loop_kw.search(line):
                inside_loop = True
            if inside_loop:
                calls = func_call.findall(line)
                if len(calls) >= 2:
                    hints.append(OptimizationHint(
                        category="REPEATED_COMPUTATION",
                        severity="MEDIUM",
                        line=i,
                        description=(
                            f"Multiple function calls found inside a loop at line {i}. "
                            "Calling the same function repeatedly in a loop wastes CPU cycles."
                        ),
                        suggestion=(
                            "Store the result in a variable before the loop "
                            "and reuse it inside."
                        ),
                        example=(
                            "Bad:  while(i < strlen(str))\n"
                            "Good: int len = strlen(str);\n      while(i < len)"
                        )
                    ))
                    break   # report once
        return hints

    def _check_unused_variables(self, lines: List[str]) -> List[OptimizationHint]:
        hints = []
        declared   = {}   # varname -> line number
        used_names = set()
        decl_pat   = re.compile(r'\b(int|float|char|double)\s+(\w+)\s*[=;,]')
        ident_pat  = re.compile(r'\b([a-zA-Z_]\w*)\b')

        for i, line in enumerate(lines, 1):
            for m in decl_pat.finditer(line):
                declared[m.group(2)] = i

        for line in lines:
            for m in ident_pat.finditer(line):
                used_names.add(m.group(1))

        for var, decl_line in declared.items():
            # count how many times the name appears across the whole source
            occurrences = sum(1 for l in lines if re.search(rf'\b{re.escape(var)}\b', l))
            if occurrences == 1:   # declared but never used elsewhere
                hints.append(OptimizationHint(
                    category="UNUSED_VARIABLE",
                    severity="LOW",
                    line=decl_line,
                    description=(
                        f"Variable '{var}' declared at line {decl_line} "
                        "appears to never be used. Unused variables waste memory."
                    ),
                    suggestion=f"Remove the declaration of '{var}' if it is not needed.",
                    example=f"Remove: int {var} = ...;"
                ))
        return hints

    def _check_magic_numbers(self, lines: List[str]) -> List[OptimizationHint]:
        hints = []
        magic_pat = re.compile(r'\b([2-9]\d{1,})\b')  # numbers >= 20
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("#"):
                continue
            for m in magic_pat.finditer(line):
                val = m.group(1)
                hints.append(OptimizationHint(
                    category="MAGIC_NUMBER",
                    severity="LOW",
                    line=i,
                    description=(
                        f"Magic number '{val}' found at line {i}. "
                        "Hard-coded numbers make code hard to read and maintain."
                    ),
                    suggestion=(
                        f"Define a named constant: #define MAX_SIZE {val}  "
                        f"and use MAX_SIZE instead of {val}."
                    ),
                    example=(
                        f"Bad:  for(i = 0; i < {val}; i++)\n"
                        f"Good: #define MAX_SIZE {val}\n      for(i = 0; i < MAX_SIZE; i++)"
                    )
                ))
                break   # one per line is enough
        return hints[:3]  # cap at 3 to avoid noise

    def _check_redundant_condition(self, lines: List[str]) -> List[OptimizationHint]:
        hints = []
        red_pat = re.compile(r'if\s*\(\s*(\w+)\s*==\s*true\s*\)|if\s*\(\s*(\w+)\s*==\s*1\s*\)')
        for i, line in enumerate(lines, 1):
            if red_pat.search(line):
                hints.append(OptimizationHint(
                    category="REDUNDANT_CONDITION",
                    severity="LOW",
                    line=i,
                    description=(
                        "Redundant comparison in condition at line {i}. "
                        "Comparing a boolean/flag to 1 or true is unnecessary."
                    ),
                    suggestion="Use the variable directly as the condition.",
                    example="Bad: if(flag == 1)\nGood: if(flag)"
                ))
        return hints

    def _check_unnecessary_return(self, lines: List[str]) -> List[OptimizationHint]:
        hints = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == "return;" and i > 1:
                prev = lines[i - 2].strip()
                if prev.endswith("}"):
                    hints.append(OptimizationHint(
                        category="UNNECESSARY_RETURN",
                        severity="LOW",
                        line=i,
                        description=(
                            f"Unnecessary 'return;' at line {i}. "
                            "A return at the very end of a void function is redundant."
                        ),
                        suggestion="Remove the unnecessary return statement.",
                        example="Void functions automatically return at the closing }."
                    ))
        return hints


# ─────────────────────────────────────────────
#  Security Analyser
# ─────────────────────────────────────────────

class SecurityAnalyser:
    """Detects insecure coding patterns in C source."""

    UNSAFE_FUNCTIONS = {
        "gets":    ("BUFFER_OVERFLOW",  "CRITICAL", "CWE-119",
                    "gets() does not check buffer size — any input can overflow the buffer and corrupt memory.",
                    "Use fgets(buf, sizeof(buf), stdin) instead of gets()."),
        "strcpy":  ("BUFFER_OVERFLOW",  "HIGH",     "CWE-120",
                    "strcpy() copies without checking destination buffer size, risking buffer overflow.",
                    "Use strncpy(dest, src, sizeof(dest)-1) or strlcpy() instead."),
        "strcat":  ("BUFFER_OVERFLOW",  "HIGH",     "CWE-120",
                    "strcat() appends without checking buffer bounds.",
                    "Use strncat(dest, src, sizeof(dest)-strlen(dest)-1) instead."),
        "sprintf": ("FORMAT_STRING",    "HIGH",     "CWE-134",
                    "sprintf() can overflow the destination buffer if the formatted string is too long.",
                    "Use snprintf(buf, sizeof(buf), ...) to limit output size."),
        "scanf":   ("BUFFER_OVERFLOW",  "MEDIUM",   "CWE-119",
                    "scanf() with %s reads without a width limit and can overflow the buffer.",
                    "Use scanf(\"%255s\", buf) with an explicit width limit."),
        "printf":  ("FORMAT_STRING",    "MEDIUM",   "CWE-134",
                    "If user input is passed directly as the format string, an attacker can leak memory.",
                    "Always use printf(\"%s\", user_input) — never printf(user_input)."),
        "malloc":  ("NULL_DEREF",       "MEDIUM",   "CWE-476",
                    "malloc() can return NULL if allocation fails. Using the result without checking causes a crash.",
                    "Always check: if(ptr == NULL) { /* handle error */ }"),
        "system":  ("COMMAND_INJECTION","CRITICAL",  "CWE-78",
                    "system() executes a shell command. If any argument comes from user input, command injection is possible.",
                    "Avoid system(). Use execv() with a fixed path and no shell interpretation."),
        "atoi":    ("INPUT_VALIDATION", "LOW",      "CWE-20",
                    "atoi() silently returns 0 on invalid input with no error indication.",
                    "Use strtol() which sets errno and reports where parsing stopped."),
    }

    def analyse(self, source: str) -> List[SecurityIssue]:
        issues = []
        lines  = source.split("\n")
        issues.extend(self._check_unsafe_functions(lines))
        issues.extend(self._check_hardcoded_credentials(lines))
        issues.extend(self._check_null_check_after_malloc(source, lines))
        issues.extend(self._check_integer_overflow(lines))
        issues.extend(self._check_array_bounds(lines))
        return issues

    def _check_unsafe_functions(self, lines: List[str]) -> List[SecurityIssue]:
        issues = []
        for i, line in enumerate(lines, 1):
            for func, (cat, sev, cwe, desc, fix) in self.UNSAFE_FUNCTIONS.items():
                if re.search(rf'\b{func}\s*\(', line):
                    issues.append(SecurityIssue(
                        category=cat, severity=sev, line=i,
                        description=f"Unsafe function '{func}()' used at line {i}. {desc}",
                        suggestion=fix, cwe=cwe
                    ))
        return issues

    def _check_hardcoded_credentials(self, lines: List[str]) -> List[SecurityIssue]:
        issues = []
        patterns = [
            re.compile(r'(password|passwd|pwd|secret|api_key|token)\s*=\s*"[^"]+"', re.I),
            re.compile(r'(password|passwd)\s*\[\]\s*=\s*"[^"]+"', re.I),
        ]
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            for pat in patterns:
                if pat.search(line):
                    issues.append(SecurityIssue(
                        category="HARDCODED_CREDENTIAL",
                        severity="CRITICAL",
                        line=i,
                        description=(
                            f"Hardcoded credential or secret found at line {i}. "
                            "Storing passwords in source code exposes them to anyone who reads the code."
                        ),
                        suggestion=(
                            "Read credentials from environment variables or a secure config file. "
                            "Never commit secrets to version control."
                        ),
                        cwe="CWE-798"
                    ))
        return issues

    def _check_null_check_after_malloc(self, source: str, lines: List[str]) -> List[SecurityIssue]:
        issues = []
        malloc_lines = {}
        for i, line in enumerate(lines, 1):
            m = re.search(r'(\w+)\s*=\s*malloc\s*\(', line)
            if m:
                malloc_lines[m.group(1)] = i

        for var, decl_line in malloc_lines.items():
            # look for a NULL check within 5 lines after malloc
            window = "\n".join(lines[decl_line : min(decl_line + 5, len(lines))])
            if not re.search(rf'\b{re.escape(var)}\s*==\s*NULL|NULL\s*==\s*{re.escape(var)}', window):
                issues.append(SecurityIssue(
                    category="NULL_DEREF",
                    severity="MEDIUM",
                    line=decl_line,
                    description=(
                        f"malloc() result stored in '{var}' at line {decl_line} "
                        "is never checked for NULL. If allocation fails your program will crash."
                    ),
                    suggestion=(
                        f"Add immediately after: if ({var} == NULL) {{ fprintf(stderr, \"Out of memory\"); exit(1); }}"
                    ),
                    cwe="CWE-476"
                ))
        return issues

    def _check_integer_overflow(self, lines: List[str]) -> List[SecurityIssue]:
        issues = []
        pat = re.compile(r'\b(int)\s+\w+\s*\*\s*\w+|\b(int)\s+\w+\s*\+\s*\w+')
        for i, line in enumerate(lines, 1):
            if re.search(r'malloc\s*\(\s*\w+\s*\*\s*\w+', line):
                issues.append(SecurityIssue(
                    category="INTEGER_OVERFLOW",
                    severity="HIGH",
                    line=i,
                    description=(
                        f"Potential integer overflow in malloc size calculation at line {i}. "
                        "Multiplying two ints can overflow before the result is passed to malloc."
                    ),
                    suggestion=(
                        "Use size_t for sizes and check for overflow: "
                        "if (n > SIZE_MAX / sizeof(type)) { /* overflow */ }"
                    ),
                    cwe="CWE-190"
                ))
        return issues

    def _check_array_bounds(self, lines: List[str]) -> List[SecurityIssue]:
        issues = []
        arr_decl = re.compile(r'\b\w+\s+(\w+)\s*\[(\d+)\]')
        arr_access = re.compile(r'(\w+)\s*\[([^\]]+)\]')
        declared_sizes = {}

        for i, line in enumerate(lines, 1):
            for m in arr_decl.finditer(line):
                declared_sizes[m.group(1)] = (int(m.group(2)), i)

        for i, line in enumerate(lines, 1):
            for m in arr_access.finditer(line):
                name, idx = m.group(1), m.group(2)
                if name in declared_sizes and idx.strip().isdigit():
                    size, _ = declared_sizes[name]
                    if int(idx.strip()) >= size:
                        issues.append(SecurityIssue(
                            category="OUT_OF_BOUNDS",
                            severity="CRITICAL",
                            line=i,
                            description=(
                                f"Array '{name}' declared with size {size} but accessed "
                                f"at index {idx} (line {i}) — this is out of bounds!"
                            ),
                            suggestion=(
                                f"Valid indices for '{name}' are 0 to {size - 1}. "
                                "Add a bounds check before accessing the array."
                            ),
                            cwe="CWE-125"
                        ))
        return issues


# ─────────────────────────────────────────────
#  Report formatter
# ─────────────────────────────────────────────

SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

def format_optimization_report(hints: List[OptimizationHint]) -> str:
    if not hints:
        return "✓ No optimization issues found. Code looks efficient!\n"
    out = []
    out.append("=" * 60)
    out.append("  OPTIMIZATION HINTS")
    out.append("=" * 60)
    hints_sorted = sorted(hints, key=lambda h: SEV_ORDER.get(h.severity, 9))
    for idx, h in enumerate(hints_sorted, 1):
        out.append(f"\n  [{idx}] {h.category}  |  Severity: {h.severity}  |  Line: {h.line}")
        out.append(f"  {h.description}")
        out.append(f"  → Fix: {h.suggestion}")
        if h.example:
            for ex_line in h.example.split("\n"):
                out.append(f"    {ex_line}")
    out.append("\n" + "=" * 60)
    return "\n".join(out)


def format_security_report(issues: List[SecurityIssue]) -> str:
    if not issues:
        return "✓ No security issues detected.\n"
    out = []
    out.append("=" * 60)
    out.append("  SECURITY ANALYSIS REPORT")
    out.append("=" * 60)
    issues_sorted = sorted(issues, key=lambda s: SEV_ORDER.get(s.severity, 9))
    for idx, s in enumerate(issues_sorted, 1):
        out.append(f"\n  [{idx}] {s.category}  |  Severity: {s.severity}  |  Line: {s.line}")
        if s.cwe:
            out.append(f"  Reference: {s.cwe}")
        out.append(f"  {s.description}")
        out.append(f"  → Fix: {s.suggestion}")
    out.append("\n" + "=" * 60)
    return "\n".join(out)


# ─────────────────────────────────────────────
#  Quick demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sample_code = r"""
#include <stdio.h>
#include <string.h>

int main() {
    char buf[64];
    char password[] = "admin123";
    int n = 100;
    char* ptr = malloc(n * sizeof(char));

    gets(buf);
    strcpy(buf, "hello world this could overflow");
    system("ls -la");

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            buf[i] = buf[j];
        }
    }

    int unused_var;
    return 0;
}
"""
    opt   = OptimizationAnalyser()
    sec   = SecurityAnalyser()
    hints  = opt.analyse(sample_code)
    issues = sec.analyse(sample_code)

    print(format_optimization_report(hints))
    print()
    print(format_security_report(issues))