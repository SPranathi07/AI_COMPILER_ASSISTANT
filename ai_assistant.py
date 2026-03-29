import os

EXPLANATIONS = {
    "MISSING_SEMICOLON": {
        "title":       "Missing Semicolon",
        "explanation": "You forgot to put a semicolon (;) at the end of a statement. In C every statement must end with a semicolon.",
        "fix":         "Add a semicolon ; at the end of the line.",
        "example":     "Change:  int x = 5\nTo:      int x = 5;"
    },
    "UNMATCHED_LBRACE": {
        "title":       "Missing Closing Brace",
        "explanation": "You opened a curly brace { but never closed it with }. Every opening brace needs a matching closing brace.",
        "fix":         "Add a closing brace } at the end of the block.",
        "example":     "Change:  if (x > 0) {\n             return x;\nTo:      if (x > 0) {\n             return x;\n         }"
    },
    "UNMATCHED_RBRACE": {
        "title":       "Extra Closing Brace",
        "explanation": "You have a closing brace } that has no matching opening brace {.",
        "fix":         "Remove the extra } or add a matching { earlier.",
        "example":     "Remove the extra } on this line."
    },
    "UNMATCHED_LPAREN": {
        "title":       "Missing Closing Parenthesis",
        "explanation": "You opened a parenthesis ( but never closed it with ). Every ( needs a matching ).",
        "fix":         "Add a closing parenthesis ) to match the opening.",
        "example":     "Change:  if (x > 0\nTo:      if (x > 0)"
    },
    "UNMATCHED_RPAREN": {
        "title":       "Extra Closing Parenthesis",
        "explanation": "You have a closing parenthesis ) with no matching opening parenthesis (.",
        "fix":         "Remove the extra ) or add a matching ( earlier.",
        "example":     "Remove the extra ) on this line."
    },
    "ASSIGNMENT_IN_CONDITION": {
        "title":       "Assignment Instead of Comparison",
        "explanation": "You used = (assignment) inside a condition. You probably meant == (comparison). In C = sets a value while == checks if two values are equal.",
        "fix":         "Change = to == inside the if or while condition.",
        "example":     "Change:  if (x = 0)\nTo:      if (x == 0)"
    },
    "DEFAULT": {
        "title":       "Syntax Error",
        "explanation": "The compiler found a syntax error. The code does not follow the rules of C.",
        "fix":         "Check the line mentioned and review the C syntax rules.",
        "example":     "Review the code around the reported line."
    }
}

AUTOCOMPLETE = {
    "KEYWORD(int)":    ["IDENTIFIER", "LPAREN"],
    "KEYWORD(float)":  ["IDENTIFIER", "LPAREN"],
    "KEYWORD(void)":   ["IDENTIFIER", "LPAREN"],
    "KEYWORD(char)":   ["IDENTIFIER", "LPAREN"],
    "KEYWORD(if)":     ["LPAREN"],
    "KEYWORD(while)":  ["LPAREN"],
    "KEYWORD(for)":    ["LPAREN"],
    "KEYWORD(return)": ["IDENTIFIER", "INT_LITERAL", "SEMICOLON"],
    "IDENTIFIER":      ["ASSIGN", "LPAREN", "SEMICOLON", "LBRACKET"],
    "ASSIGN":          ["INT_LITERAL", "FLOAT_LITERAL", "IDENTIFIER", "LPAREN"],
    "INT_LITERAL":     ["SEMICOLON", "PLUS", "MINUS", "RPAREN"],
    "FLOAT_LITERAL":   ["SEMICOLON", "PLUS", "MINUS", "RPAREN"],
    "LPAREN":          ["IDENTIFIER", "INT_LITERAL", "KEYWORD(int)"],
    "RPAREN":          ["SEMICOLON", "LBRACE", "RPAREN"],
    "LBRACE":          ["KEYWORD(int)", "IDENTIFIER", "RBRACE"],
    "RBRACE":          ["KEYWORD(int)", "IDENTIFIER", "EOF"],
    "SEMICOLON":       ["KEYWORD(int)", "KEYWORD(if)", "IDENTIFIER", "RBRACE"],
    "PLUS":            ["IDENTIFIER", "INT_LITERAL", "FLOAT_LITERAL"],
    "MINUS":           ["IDENTIFIER", "INT_LITERAL", "FLOAT_LITERAL"],
    "EQ":              ["IDENTIFIER", "INT_LITERAL", "FLOAT_LITERAL"],
    "COMMA":           ["IDENTIFIER", "INT_LITERAL", "KEYWORD(int)"],
    "LTE":             ["IDENTIFIER", "INT_LITERAL"],
    "GTE":             ["IDENTIFIER", "INT_LITERAL"],
    "LT":              ["IDENTIFIER", "INT_LITERAL"],
    "GT":              ["IDENTIFIER", "INT_LITERAL"],
}


class ErrorClassifier:

    def __init__(self, model_path="model.pkl"):
        pass

    def classify(self, token_sequence):
        return "DEFAULT"

    def is_correct(self, token_sequence):
        return None


class ExplanationEngine:

    def explain(self, error_type, line, column, token=""):
        info = EXPLANATIONS.get(error_type, EXPLANATIONS["DEFAULT"])
        out  = []
        out.append("=" * 55)
        out.append(f"  ERROR: {info['title']}")
        out.append("=" * 55)
        out.append(f"  Location : Line {line}, Column {column}")
        if token:
            out.append(f"  Near     : '{token}'")
        out.append("")
        out.append(f"  What went wrong:")
        out.append(f"  {info['explanation']}")
        out.append("")
        out.append(f"  How to fix it:")
        out.append(f"  {info['fix']}")
        out.append("")
        out.append(f"  Example:")
        for ex_line in info["example"].split("\n"):
            out.append(f"    {ex_line}")
        out.append("=" * 55)
        return "\n".join(out)

    def suggest(self, token_sequence):
        if not token_sequence:
            return ["KEYWORD(int)", "KEYWORD(void)", "IDENTIFIER"]
        last = token_sequence[-1]
        return AUTOCOMPLETE.get(last, ["SEMICOLON", "RBRACE"])


class AIAssistant:

    def __init__(self):
        self.classifier = ErrorClassifier()
        self.explainer  = ExplanationEngine()

    def analyze(self, errors, token_sequence=None):
        try:
            out = []

            if not errors:
                out.append("✓ No errors detected. Code looks correct!")
                if token_sequence:
                    suggestions = self.explainer.suggest(token_sequence)
                    out.append(f"\nAutocomplete — next likely tokens:")
                    out.append(f"  {suggestions}")
                return "\n".join(out)

            out.append(f"Found {len(errors)} error(s):\n")

            for i, error in enumerate(errors, 1):
                line    = error.get("line",    0)
                column  = error.get("column",  0)
                message = error.get("message", "")
                token   = error.get("token",   "")

                error_type = self._classify(message, token_sequence)

                out.append(f"Error {i} of {len(errors)}:")
                out.append(self.explainer.explain(
                    error_type, line, column, token
                ))

            if token_sequence:
                suggestions = self.explainer.suggest(token_sequence)
                out.append(f"\nAutocomplete — next likely tokens: {suggestions}")

            return "\n".join(out)

        except Exception as e:
            return f"AI Analysis: Error detected in your code.\nDetails: {str(e)}"

    def _classify(self, message, token_sequence):
        msg = message.lower()

        if "semicolon" in msg or "';'" in msg:
            return "MISSING_SEMICOLON"

        if "'{'" in msg:
            return "UNMATCHED_LBRACE"

        if "'}'" in msg:
            return "UNMATCHED_RBRACE"

        if "'('" in msg:
            return "UNMATCHED_LPAREN"

        if "')'" in msg:
            return "UNMATCHED_RPAREN"

        if "expected ';'" in msg:
            return "MISSING_SEMICOLON"

        return "DEFAULT"


if __name__ == "__main__":
    assistant = AIAssistant()
    test_errors = [
        {"error": True, "line": 2, "column": 14,
         "message": "expected ';'", "token": "int"},
        {"error": True, "line": 17, "column": 5,
         "message": "expected ';'", "token": "}"}
    ]
    test_tokens = ["KEYWORD(int)", "IDENTIFIER", "LPAREN", "RPAREN", "LBRACE"]
    print(assistant.analyze(test_errors, test_tokens))


