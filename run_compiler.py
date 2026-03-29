import subprocess
import json
import os

def build_compiler():
    result = subprocess.run(
        ["gcc", "Lexer.c", "Parser.c", "-o", "compiler"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return True
    else:
        print(result.stderr)
        return False

def run_compiler(source_file):
    errors = []
    token_sequence = []

    compiler_path = "compiler.exe" if os.name == "nt" else "./compiler"

    if not os.path.exists(compiler_path) and not os.path.exists("compiler"):
        success = build_compiler()
        if not success:
            return {"errors": [], "tokens": []}

    if os.name == "nt":
        run_cmd = ["compiler.exe", source_file]
    else:
        run_cmd = ["./compiler", source_file]

    try:
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True
        )

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith('{'):
                try:
                    data = json.loads(line)
                    if "tokens" in data:
                        token_sequence = data["tokens"].split()
                    elif data.get("error") == True:
                        errors.append(data)
                except json.JSONDecodeError:
                    pass

    except FileNotFoundError:
        print("Error: compiler not found.")
        print("Run: gcc Lexer.c Parser.c -o compiler")

    return {
        "errors": errors,
        "tokens": token_sequence
    }

if __name__ == "__main__":
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else "test.c"
    result = run_compiler(test_file)
    print(f"Tokens: {result['tokens']}")
    print(f"Errors: {len(result['errors'])}")
    for e in result["errors"]:
        print(f"  Line {e.get('line')}: {e.get('message')} (got '{e.get('token')}')")