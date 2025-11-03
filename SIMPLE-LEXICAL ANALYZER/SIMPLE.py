import re
import json
import pathlib
from collections import Counter, defaultdict
from colorama import Fore, Back, Style, init

# Initialize colored console output with auto-reset after each print
init(autoreset=True)

# === SIMPLE Language Lexical Analyzer ===
# This program tokenizes a SIMPLE language source file, identifies token types,
# handles errors, prints colored output, and saves results to files.

# --- Language Definitions ---
# Define the categories of words in the SIMPLE language
DATA_TYPES = {
    "int", "float", "char", "string", "text", "secure", "bool",
    "time", "date", "timestamp", "array", "collection"
}

KEYWORDS = {
    "if", "do", "end", "next", "return",
    "global", "local", "get", "show", "let", "store",
    "try", "handle"
}

RESERVED = {"object", "for", "null", "main", "system", "error"}  # Reserved words
NOISE = {"to", "then", "please", "do"}  # Common words with no effect

# --- Token Patterns ---
# Regex patterns for each token type
TOKEN_SPECIFICATION = [
    ("MULTI_COMMENT", r"/\*[\s\S]*?\*/"),  # Matches multi-line comments /* ... */
    ("SINGLE_COMMENT", r"//[^\n]*"),       # Matches single-line comments
    ("STRING", r'"([^"\\]|\\.)*"'),        # Matches string literals with escape sequences
    ("FLOAT", r"\d+\.\d+"),                # Matches floating-point numbers
    ("INT", r"\d+"),                        # Matches integers
    ("ASSIGN_OP", r"\+=|-=|\*=|/=|%=|~=|="), # Assignment operators
    ("REL_OP", r"(<=|>=|==|!=|<|>)"),       # Relational operators
    ("EXP_OP", r"\*\*|\^"),                 # Exponentiation operators
    ("ARITH_OP", r"[+\-*/%]"),              # Arithmetic operators
    ("UNARY_OP", r"\+\+|--"),               # Increment/Decrement operators
    ("LOGICAL_OP", r"&&|\|\||!"),           # Logical operators
    ("LPAREN", r"\("), ("RPAREN", r"\)"),   # Parentheses
    ("LBRACKET", r"\["), ("RBRACKET", r"\]"), # Brackets
    ("COLON", r":"), ("COMMA", r","), ("SEMICOLON", r";"), # Misc symbols
    ("IDENTIFIER", r"[A-Za-z_][A-Za-z0-9_]*"), # Variable/function names
    ("NEWLINE", r"\n"),                      # Line breaks
    ("SKIP", r"[ \t]+"),                     # Whitespace (ignored)
    ("MISMATCH", r"."),                      # Any unmatched character (lexical error)
]

# Compile all regex patterns into one master regex
master_re = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION))

# --- Token Colors ---
# Map token types to distinct colors for console output
TOKEN_COLORS = {
    "KEYWORD": Fore.BLUE + Style.BRIGHT,
    "DATATYPE": Fore.YELLOW + Style.BRIGHT,
    "IDENTIFIER": Fore.GREEN + Style.BRIGHT,
    "NUMBER": Fore.MAGENTA + Style.BRIGHT,
    "STRING": Fore.CYAN + Style.BRIGHT,
    "ASSIGN_OP": Fore.WHITE + Style.BRIGHT,
    "ARITH_OP": Fore.RED + Style.BRIGHT,
    "REL_OP": Fore.BLUE,
    "LOGICAL_OP": Fore.MAGENTA,
    "UNARY_OP": Fore.RED,
    "EXP_OP": Fore.RED + Style.BRIGHT,
    "COMMENT": Fore.LIGHTBLACK_EX,
    "RESERVED": Fore.RED + Style.BRIGHT,
    "NOISE": Fore.CYAN,
    "TO_DO": Fore.MAGENTA + Style.BRIGHT,
    "LEXICAL_ERROR": Fore.WHITE + Back.RED + Style.BRIGHT,
    "WHITESPACE": Fore.RESET,
    "NEWLINE": Fore.RESET,
    "LPAREN": Fore.WHITE,
    "RPAREN": Fore.WHITE,
    "LBRACKET": Fore.WHITE,
    "RBRACKET": Fore.WHITE,
    "COLON": Fore.WHITE,
    "COMMA": Fore.WHITE,
    "SEMICOLON": Fore.WHITE,
}

# --- Tokenizer Function ---
def tokenize(code: str):
    """
    Tokenizes the input SIMPLE source code.
    Returns a list of tokens and a list of lexical errors.
    Each token is a dictionary containing:
        type, value, line, column, and raw (for strings)
    """
    tokens = []
    errors = []
    line_num = 1  # Current line number
    line_start = 0  # Position of start of line

    # Iterate over all regex matches in the code
    for mo in master_re.finditer(code):
        kind = mo.lastgroup  # Token type from regex
        value = mo.group()   # Matched string
        column = mo.start() - line_start + 1  # Column number

        # Handle newlines
        if kind == "NEWLINE":
            tokens.append({"type": "NEWLINE", "value": "\n", "line": line_num, "column": column})
            line_num += 1
            line_start = mo.end()
            continue
        # Handle spaces and tabs
        elif kind == "SKIP":
            tokens.append({"type": "WHITESPACE", "value": value, "line": line_num, "column": column})
            continue
        # Handle multi-line comments
        elif kind == "MULTI_COMMENT":
            tokens.append({"type": "COMMENT", "value": value, "line": line_num, "column": column})
            line_num += value.count("\n")
            if "\n" in value:
                last_nl_index = value.rfind("\n")
                line_start = mo.start() + last_nl_index + 1
            continue
        # Handle single-line comments
        elif kind == "SINGLE_COMMENT":
            tokens.append({"type": "COMMENT", "value": value, "line": line_num, "column": column})
            continue
        # Handle string literals
        elif kind == "STRING":
            raw = value
            inner = value[1:-1]  # Remove quotes
            tokens.append({"type": "STRING", "value": inner, "raw": raw, "line": line_num, "column": column})
            continue
        # Handle identifiers and keywords
        elif kind == "IDENTIFIER":
            low = value.lower()
            tok_type = "IDENTIFIER"

            # Special handling for "to do" phrase
            if low == "to" and len(tokens) > 0:
                next_index = mo.end()
                m2 = re.match(r'\s+do\b', code[next_index:])
                if m2:
                    tok_type = "TO_DO"
                    value = "to do"
                    skip_len = m2.end()
                    line_start += skip_len - 1
            elif low in DATA_TYPES:
                tok_type = "DATATYPE"
            elif low in KEYWORDS:
                tok_type = "KEYWORD"
            elif low in RESERVED:
                tok_type = "RESERVED"
            elif low in NOISE:
                tok_type = "NOISE"
            tokens.append({"type": tok_type, "value": value, "line": line_num, "column": column})
            continue
        # Handle numbers (int or float)
        elif kind in ("FLOAT", "INT"):
            tokens.append({"type": "NUMBER", "value": value, "line": line_num, "column": column})
            continue
        # Handle mismatched/invalid tokens
        elif kind == "MISMATCH":
            errors.append(f"Invalid token '{value}' at line {line_num}, column {column}")
            tokens.append({"type": "LEXICAL_ERROR", "value": value, "line": line_num, "column": column})
            continue
        else:
            # Any other token type from regex
            tokens.append({"type": kind, "value": value, "line": line_num, "column": column})
            continue

    return tokens, errors

# --- Utilities for printing tokens ---
def color_text_for(token):
    """
    Returns a colorized string for the given token for console output.
    Whitespace and newlines are returned as-is.
    """
    ttype = token["type"]
    color = TOKEN_COLORS.get(ttype, Fore.WHITE)
    val = token.get("raw", token.get("value", ""))
    if ttype in ("WHITESPACE", "NEWLINE"):
        return val
    return f"{color}{val}{Style.RESET_ALL}"

# --- Token Summary ---
def show_summary(tokens, errors):
    """
    Prints a summary of all token counts and lexical errors.
    """
    counts = Counter(t["type"] for t in tokens)
    print(Fore.CYAN + "\n--- Token Summary ---" + Style.RESET_ALL)

    # Print counts for each token type
    for ttype, count in counts.items():
        color = TOKEN_COLORS.get(ttype, Fore.WHITE)
        print(f"{color}{ttype:<12}: {count}{Style.RESET_ALL}")

    # Total token statistics
    total_tokens_including_whitespace = sum(counts.values())
    meaningful_tokens = total_tokens_including_whitespace - counts.get("WHITESPACE", 0) - counts.get("NEWLINE", 0)

    print(Fore.MAGENTA + f"\nTotal tokens (including whitespace/newlines): {total_tokens_including_whitespace}" + Style.RESET_ALL)
    print(Fore.MAGENTA + f"Total meaningful tokens (excluding whitespace/newlines): {meaningful_tokens}" + Style.RESET_ALL)

    # Show first 10 lexical errors, if any
    if errors:
        print(Fore.RED + f"\nErrors ({len(errors)}):" + Style.RESET_ALL)
        for e in errors[:10]:
            print(Fore.RED + "  - " + e + Style.RESET_ALL)
    else:
        print(Fore.GREEN + "\nNo lexical errors detected." + Style.RESET_ALL)

# --- Save tokens and errors to files ---
def save_outputs(tokens, errors, base_name="simple"):
    """
    Saves token list to JSON and errors to text file.
    """
    token_output = pathlib.Path(f"{base_name}_tokens.json")
    with token_output.open("w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
    print(Fore.GREEN + f"Tokens saved to {token_output.resolve()}" + Style.RESET_ALL)

    if errors:
        error_output = pathlib.Path(f"{base_name}_lexer_errors.txt")
        with error_output.open("w", encoding="utf-8") as ef:
            ef.write("\n".join(errors))
        print(Fore.RED + f"{len(errors)} lexical errors found. Saved to {error_output.resolve()}" + Style.RESET_ALL)
    else:
        print(Fore.GREEN + "No lexical errors detected." + Style.RESET_ALL)

# --- Main Execution ---
def main():
    """
    Main entry point for the lexical analyzer.
    Prompts user for source file, tokenizes it, saves results, and prints summary.
    """
    print(Fore.CYAN + "\n=== SIMPLE Lexical Analyzer ===\n" + Style.RESET_ALL)
    source_file = input(Fore.YELLOW + "Enter SIMPLE source file: ").strip()
    file_path = pathlib.Path(source_file)

    if not file_path.exists():
        print(Fore.RED + f"File not found: {file_path}")
        return

    # Read file contents
    code = file_path.read_text(encoding="utf-8")
    # Tokenize the code
    tokens, errors = tokenize(code)
    # Save tokens and errors to files
    save_outputs(tokens, errors, base_name=file_path.stem)

    # Print first 40 tokens in colored tabular format
    print()
    print(Fore.LIGHTBLACK_EX + f"{'Row':>5} | {'Col':>5} | {'Token':<15} | Lexeme" + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "-" * 55 + Style.RESET_ALL)
    shown = 0
    for t in tokens:
        if t["type"] in ("WHITESPACE", "NEWLINE"):
            continue
        color = TOKEN_COLORS.get(t["type"], Fore.WHITE)
        print(f"{t['line']:>5} | {t['column']:>5} | {color}{t['type']:<15}{Style.RESET_ALL} | {t.get('raw', t.get('value',''))}")
        shown += 1
        if shown >= 40:
            break

    # Print token summary
    show_summary(tokens, errors)
    print(Fore.CYAN + "Analysis complete.\n" + Style.RESET_ALL)

# Entry point for the program
if __name__ == "__main__":
    main()
