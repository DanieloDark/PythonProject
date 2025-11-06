import re          # Used for matching text patterns (regular expressions)
import json        # Used for reading and writing JSON files
import pathlib     # Used for handling file paths and directories
from collections import Counter   # Used to count how many times items appear


# === SIMPLE Language Lexical Analyzer ===

#LANGUAGE ELEMENT DEFINITIONS
DATA_TYPES = {
    "int", "float", "char", "string", "text", "secure", "bool",
    "time", "date", "timestamp", "array", "collection"
}

KEYWORDS = {
    "if", "do", "end", "next", "to do", "return",
    "global", "local", "get", "show",
    "let", "store", "try", "handle",
    "int", "float", "char", "string", "text", "secure",
    "bool", "time", "date", "timestamp", "array", "collection"
}

RESERVED = {"object", "for", "null", "main", "system", "error"}
NOISE = {"to", "then", "please"}


#TOKEN REGULAR EXPRESSIONS
#Each pattern = Defines token patterns, FA for one token (FA Construction)
TOKEN_SPECIFICATION = [
    ("MULTI_COMMENT", r"/\*[\s\S]*?\*/"),
    ("SINGLE_COMMENT", r"//[^\n]*"),
    ("STRING", r'"([^"\\]|\\.)*"'),
    ("FLOAT", r"\d+\.\d+"),
    ("INT", r"\d+"),
    ("ASSIGN_OP", r"\+=|-=|\*=|/=|%=|~=|="),
    ("REL_OP", r"(<=|>=|==|!=|<|>)"),
    ("EXP_OP", r"\*\*|\^"),
    ("ARITH_OP", r"[+\-*/%]"),
    ("UNARY_OP", r"\+\+|--"),
    ("LOGICAL_OP", r"&&|\|\||!"),
    ("LPAREN", r"\("), ("RPAREN", r"\)"),
    ("LBRACKET", r"\["), ("RBRACKET", r"\]"),
    ("COLON", r":"), ("COMMA", r","),
    ("IDENTIFIER", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("NEWLINE", r"\n"),
    ("WHITESPACE", r"[ \t]+"),
    ("MISMATCH", r"."),
]

# Builds the combined regex machine, combines all small FAs into one big FA (FA simulation)
master_re = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION))


#TOKENIZER FUNCTION
def tokenize(code: str, error_log_path: pathlib.Path):
    tokens = []
    errors = []
    line_num = 1
    line_start = 0

    error_log_path.write_text("", encoding="utf-8")

    # Scans and matches tokens, the FA processes input symbols and accepts/rejects strings
    for mo in master_re.finditer(code):

    # Regex found a match, FA reached accepting state
        kind = mo.lastgroup
        value = mo.group()
        column = mo.start() - line_start + 1
    #(it reads one state at a time)

    # Once a token is accepted (the FA reaches a final state), this code records it
        if kind == "NEWLINE":
            tokens.append({"type": "NEWLINE", "value": "\\n", "line": line_num, "column": column})
            line_num += 1
            line_start = mo.end()
            continue
        elif kind == "WHITESPACE":
            tokens.append({"type": "WHITESPACE", "value": value, "line": line_num, "column": column})
            continue
        elif kind == "MULTI_COMMENT":
            tokens.append({"type": "COMMENT", "value": value, "line": line_num, "column": column})
            line_num += value.count("\n")
            continue
        elif kind == "SINGLE_COMMENT":
            tokens.append({"type": "COMMENT", "value": value, "line": line_num, "column": column})
            continue
        elif kind == "STRING":
            inner = value[1:-1]
            tokens.append({"type": "STRING", "value": inner, "line": line_num, "column": column})
            continue
        elif kind == "IDENTIFIER":
            low = value.lower()
            tok_type = (
                "DATATYPE" if low in DATA_TYPES else
                "KEYWORD" if low in KEYWORDS else
                "RESERVED" if low in RESERVED else
                "NOISE" if low in NOISE else
                "IDENTIFIER"
            )
            tokens.append({"type": tok_type, "value": value, "line": line_num, "column": column})
            continue
        elif kind in ("FLOAT", "INT"):
            tokens.append({"type": "NUMBER", "value": value, "line": line_num, "column": column})
            continue
        elif kind == "MISMATCH": #Detects non-accepted tokens, if non-final states → lexical error (FA rejected input)
            error_msg = f"Invalid token '{value}' at line {line_num}, column {column}"
            errors.append(error_msg)
            tokens.append({"type": "LEXICAL_ERROR", "value": value, "line": line_num, "column": column})
            with error_log_path.open("a", encoding="utf-8") as ef:
                ef.write(error_msg + "\n")
            continue
        else:
            tokens.append({"type": kind, "value": value, "line": line_num, "column": column})

    return tokens, errors

#OUTPUT HANDLER
def save_outputs(tokens, errors, base_name="simple"):
    token_output = pathlib.Path(f"{base_name}_tokens.json")
    with token_output.open("w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)

    output_file = pathlib.Path("Symbol Table.txt")
    with output_file.open("w", encoding="utf-8") as sf:
        sf.write("=== SIMPLE LEXICAL ANALYZER OUTPUT ===\n\n")
        sf.write("------------- SYMBOL TABLE -------------\n")
        sf.write(f"{'Line':>5} | {'Col':>5} | {'Token':<15} | Lexeme\n")
        sf.write("-" * 55 + "\n")

        # Exclude WHITESPACE and NEWLINE from symbol table display
        for t in tokens:
            if t["type"] not in ("WHITESPACE", "NEWLINE"):
                sf.write(f"{t['line']:>5} | {t['column']:>5} | {t['type']:<15} | {t.get('value', '')}\n")

        # --- Token Summary ---
        sf.write("\n--- Token Summary ---\n")
        counts = Counter(t["type"] for t in tokens)
        for ttype, count in counts.items():
            sf.write(f"{ttype:<12}: {count}\n")

        total_all = sum(counts.values())
        total_excl_ws = sum(count for ttype, count in counts.items()
                            if ttype not in ("WHITESPACE", "NEWLINE"))
        sf.write(f"\nTotal tokens (including whitespace/newlines): {total_all}\n")
        sf.write(f"Total tokens (excluding whitespace/newlines): {total_excl_ws}\n")

        # --- Error Section ---
        if errors:
            sf.write(f"\nErrors ({len(errors)}):\n")
            for e in errors[:10]:
                sf.write("  - " + e + "\n")
        else:
            sf.write("\nNo lexical errors detected.\n")

    print(f"Symbol Table saved to {output_file.resolve()}")


#MAIN DRIVER
def main():
    print("\n=== SIMPLE Lexical Analyzer ===\n")
    source_file = input("Enter SIMPLE source file: ").strip()
    file_path = pathlib.Path(source_file)

    if file_path.suffix != ".simple":
        print("Invalid file type. Only .simple files are allowed.")
        return
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    code = file_path.read_text(encoding="utf-8")
    error_log_path = pathlib.Path(f"{file_path.stem}_lexer_errors.txt")
    tokens, errors = tokenize(code, error_log_path)

    save_outputs(tokens, errors, base_name=file_path.stem)
    print("Analysis complete. Check 'Symbol Table.txt' and error log for real-time updates.")

if __name__ == "__main__":
    main()
