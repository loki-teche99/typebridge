"""
TypeBridge Desktop - Java Code Structure & Indentation Engine
============================================================
Parses, sanitizes, and perfectly formats Java source code for typing.

Guarantees:
1. Normalizes line 1 extra spaces and strips common leading margins.
2. Replaces harmful non-breaking spaces (\u00A0) and smart quotes that crash javac.
3. Automatically indents Java blocks ({ ... }) with exact 4-space conventions.
4. Correctly handles closing braces (}) dedenting before typing the line.
5. Preserves blank lines without phantom spaces.
6. Provides target-aware output for both plain text (Notepad, LeetCode, web compilers)
   and auto-indenting IDEs (VS Code, IntelliJ IDEA, Eclipse).
"""
import re

# Dangerous Unicode characters from phone clipboards/web that break javac
UNICODE_SPACES = re.compile(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000\uFEFF]')
SMART_DOUBLE_QUOTES = re.compile(r'[\u201C\u201D\u201E\u201F\u00AB\u00BB]')
SMART_SINGLE_QUOTES = re.compile(r'[\u2018\u2019\u201A\u201B]')


class JavaCodeFormatter:
    """
    Precision formatter and indenter for Java programs.
    """

    @staticmethod
    def sanitize(text: str) -> str:
        """
        Cleans up clipboard artifacts:
        - Normalizes all newline variations (\r\n, \r) to \n
        - Replaces non-breaking spaces and exotic Unicode whitespace with standard ASCII space
        - Replaces typographical curly quotes with ASCII ' and "
        - Expands tabs to 4 spaces
        """
        if not text:
            return ""

        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Replace non-breaking spaces and smart quotes
        text = UNICODE_SPACES.sub(' ', text)
        text = SMART_DOUBLE_QUOTES.sub('"', text)
        text = SMART_SINGLE_QUOTES.sub("'", text)

        # Expand tabs to 4 spaces
        text = text.expandtabs(4)

        return text

    @classmethod
    def strip_leading_margins(cls, text: str) -> str:
        """
        Considers line 1 extra spaces and common leading margins.
        If line 1 has leading spaces from being copied as an indented block on phone,
        normalizes the indentation so line 1 starts at the base margin (column 0).
        """
        text = cls.sanitize(text)
        lines = text.split('\n')
        if not lines:
            return ""

        # Find first non-empty line
        first_non_empty_idx = -1
        first_line_indent = 0
        for idx, l in enumerate(lines):
            stripped = l.lstrip(' ')
            if stripped:
                first_non_empty_idx = idx
                first_line_indent = len(l) - len(stripped)
                break

        if first_non_empty_idx == -1:
            return text  # All blank

        # Calculate minimum leading spaces among all non-empty lines
        min_indent = min(
            (len(l) - len(l.lstrip(' ')))
            for l in lines if l.strip()
        )

        # Base dedent amount: at least the minimum indent, or line 1's indent if line 1 starts a class/package
        first_stripped = lines[first_non_empty_idx].strip()
        is_java_root = any(first_stripped.startswith(kw) for kw in [
            'package', 'import', 'public class', 'class', 'public interface',
            'interface', 'public enum', 'enum', 'public record', 'record',
            '@', '/*'
        ])

        dedent_amount = first_line_indent if is_java_root else min_indent

        out_lines = []
        for l in lines:
            if not l.strip():
                out_lines.append('')
            else:
                current_indent = len(l) - len(l.lstrip(' '))
                strip_count = min(dedent_amount, current_indent)
                out_lines.append(l[strip_count:])

        return '\n'.join(out_lines)

    @classmethod
    def _count_effective_braces(cls, line: str, in_block_comment: bool = False) -> tuple[int, int, bool, bool]:
        """
        State-machine scanner for Java code.
        Counts effective '{' and '}' that alter code structure, strictly ignoring
        braces inside:
        - String literals ("...")
        - Character literals ('...')
        - Single-line comments (//...)
        - Block comments (/* ... */)

        Correctly handles:
        - Escaped characters inside strings/chars (\" or \')
        - // or /* appearing INSIDE string literals (e.g. "https://...", "/* not comment */")
        - Block comments that span multiple lines
        - Determines if the line starts with a closing brace '}'

        Returns: (open_braces, close_braces, starts_with_close, in_block_comment_at_end)
        """
        open_b = 0
        close_b = 0
        in_string = False
        in_char = False
        escaped = False
        first_effective_char = ''

        i = 0
        n = len(line)
        while i < n:
            c = line[i]

            # Inside multi-line block comment /* ... */
            if in_block_comment:
                if c == '*' and i + 1 < n and line[i + 1] == '/':
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            # Inside string literal "..."
            if in_string:
                if escaped:
                    escaped = False
                    i += 1
                    continue
                if c == '\\':
                    escaped = True
                    i += 1
                    continue
                if c == '"':
                    in_string = False
                    i += 1
                    continue
                i += 1
                continue

            # Inside char literal '...'
            if in_char:
                if escaped:
                    escaped = False
                    i += 1
                    continue
                if c == '\\':
                    escaped = True
                    i += 1
                    continue
                if c == "'":
                    in_char = False
                    i += 1
                    continue
                i += 1
                continue

            # Normal code outside comments and strings
            if c == '/' and i + 1 < n:
                next_c = line[i + 1]
                if next_c == '/':
                    # Single-line comment //: rest of the line is a comment
                    break
                elif next_c == '*':
                    # Start of block comment /*
                    in_block_comment = True
                    i += 2
                    continue

            if c == '"':
                in_string = True
                i += 1
                continue

            if c == "'":
                in_char = True
                i += 1
                continue

            if not c.isspace():
                if not first_effective_char:
                    first_effective_char = c
                if c == '{':
                    open_b += 1
                elif c == '}':
                    close_b += 1

            i += 1

        starts_with_close = (first_effective_char == '}')
        return open_b, close_b, starts_with_close, in_block_comment

    @classmethod
    def _analyze_line_braces(cls, line: str) -> tuple[int, int, bool]:
        """Convenience wrapper around _count_effective_braces."""
        open_b, close_b, starts_with_close, _ = cls._count_effective_braces(line, False)
        return open_b, close_b, starts_with_close

    @classmethod
    def format_java_structure(cls, text: str, indent_size: int = 4) -> str:
        """
        Formats Java code with mathematically perfect 4-space syntax indentation.
        Correctly balances braces, case/default statements, annotations, and comments.
        """
        clean = cls.strip_leading_margins(text)
        lines = clean.split('\n')
        if not lines:
            return ""

        formatted_lines = []
        level = 0
        indent_str = ' ' * indent_size
        in_multiline_comment = False

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                formatted_lines.append('')
                continue

            # If already inside a multi-line comment from a previous line
            if in_multiline_comment:
                comment_indent = (indent_str * level) + (' ' if line.startswith('*') else '')
                formatted_lines.append(comment_indent + line)
                _, _, _, in_multiline_comment = cls._count_effective_braces(line, in_block_comment=True)
                continue

            # Analyze line using character-by-character state-machine scanner
            open_b, close_b, starts_with_close, in_multiline_comment = cls._count_effective_braces(
                line, in_block_comment=False
            )

            # If line starts with a closing brace (e.g. '}', '} else {', '} catch (...) {')
            # dedent for THIS line
            effective_level = level
            if starts_with_close:
                effective_level = max(0, level - 1)
            elif line.startswith('case ') or line.startswith('default:'):
                # case and default inside switch are indented 1 level less than their body
                effective_level = max(0, level - 1) if level > 0 else 0

            # Indent this line
            formatted_lines.append((indent_str * effective_level) + line)

            # Update nesting level for following lines
            level = max(0, level + (open_b - close_b))

        return '\n'.join(formatted_lines)

    @classmethod
    def prepare_for_ide_mode(cls, text: str, indent_size: int = 4) -> str:
        """
        Prepares code for code editors and web IDEs (HackerEarth, LeetCode, HackerRank, Monaco, Ace, VS Code).
        Code editors automatically retain the previous line's indentation upon Enter, and add 1 level after '{'.
        This algorithm calculates the editor's cursor position on each newline and compensates:
        - If the editor already has the required indentation, 0 spaces are typed (no drift / staircase).
        - If the editor has fewer spaces, only the delta is typed.
        - If the line starts with '}', editors auto-dedent by 1 level upon typing '}'.
        - If the line needs to dedent without '}', backspaces are typed to align.
        """
        formatted = cls.format_java_structure(text, indent_size)
        lines = formatted.split('\n')
        if len(lines) <= 1:
            return formatted

        out_lines = []
        prev_target_indent = 0
        prev_open_b = 0
        prev_close_b = 0

        for idx, line in enumerate(lines):
            if idx == 0:
                out_lines.append(line)
                prev_target_indent = len(line) - len(line.lstrip(' '))
                prev_open_b, prev_close_b, _, _ = cls._count_effective_braces(line)
                continue

            stripped = line.lstrip(' ')
            if not stripped:
                out_lines.append('')
                continue

            target_indent = len(line) - len(stripped)
            curr_open_b, curr_close_b, starts_with_close, _ = cls._count_effective_braces(stripped)

            # Calculate the editor's expected cursor indentation
            if prev_open_b > prev_close_b:
                editor_indent = prev_target_indent + ((prev_open_b - prev_close_b) * indent_size)
            else:
                editor_indent = prev_target_indent

            if starts_with_close:
                # Editor auto-dedents by 1 level upon typing '}'
                effective_editor_indent = max(0, editor_indent - indent_size)
                spaces_needed = max(0, target_indent - effective_editor_indent)
                adjusted_line = (' ' * spaces_needed) + stripped
            else:
                if target_indent > editor_indent:
                    spaces_needed = target_indent - editor_indent
                    adjusted_line = (' ' * spaces_needed) + stripped
                elif target_indent < editor_indent:
                    backspaces_needed = editor_indent - target_indent
                    adjusted_line = ('\b' * backspaces_needed) + stripped
                else:
                    adjusted_line = stripped

            out_lines.append(adjusted_line)
            prev_target_indent = target_indent
            prev_open_b = curr_open_b
            prev_close_b = curr_close_b

        return '\n'.join(out_lines)
