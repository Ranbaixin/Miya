"""
Fix all syntax errors in game_memory_manager.py caused by garbled UTF-8.
The file has corrupted Chinese characters where some bytes turned into ? (0x3F),
breaking Python string literals.

This script fixes:
1. Docstrings: already fixed by _fix_mojibake.py
2. Single-quoted strings: '...?), -> '...'),
3. Double-quoted strings: "...?) -> "...")
4. f-strings: f"...{expr?)} -> f"...{expr)}"
"""


filepath = r"webnet\EntertainmentNet\game_mode\game_memory_manager.py"
with open(filepath, "rb") as f:
    content = f.read()

lines = content.split(b"\n")
fixed = 0

for i, line in enumerate(lines):
    if not line:
        continue
    new_line = bytearray(line)

    # Pattern: garbled_byte?followed_by_closing_char
    # Where closing_char is ) or , or " or }
    # The ? should be replaced with the appropriate closing quote
    idx = 0
    while idx < len(new_line):
        # Find ? at position idx
        qpos = new_line.find(0x3F, idx)  # 0x3F = ?
        if qpos == -1:
            break

        # Check if preceded by high-byte (non-ASCII) character
        # This indicates the ? is inside garbled text
        prev_byte = new_line[qpos - 1] if qpos > 0 else 0
        if prev_byte < 0x80:
            # ? is not preceded by garbled text, skip
            idx = qpos + 1
            continue

        # Check what follows ?
        next_byte = new_line[qpos + 1] if qpos + 1 < len(new_line) else 0

        if next_byte == 0x22:  # ?"
            # This might be: "...?" " where ? replaced closing logic
            # Check if this is inside a string context
            # Safest: only fix when preceded by garbled and followed by )
            pass_idx = qpos + 2
            if pass_idx < len(new_line) and new_line[pass_idx] == 0x29:  # ?")
                # Pattern: ...?") -> ...")
                # The ? should just be removed
                pass  # leaving it for now
            elif pass_idx < len(new_line) and new_line[pass_idx] == 0x2C:  # ?"),
                pass

        elif next_byte == 0x29:  # ?)
            # Check for f-string context: detect { before ?)
            # Look backwards from ? for { without matching }
            open_brace_pos = new_line.rfind(0x7B, 0, qpos)  # {
            if open_brace_pos != -1:
                close_brace_pos = new_line.find(0x7D, open_brace_pos, qpos)  # }
                if close_brace_pos == -1 or close_brace_pos > qpos:
                    # { found but no } before ? -> f-string expression expected }
                    # Replace ? with }
                    new_line[qpos] = 0x7D  # }
                    fixed += 1
                    print(f"FIXED line {i + 1}: ? -> }} in f-string expr")
                    idx = qpos + 1
                    continue

            # Pattern: ...?) at end - missing closing string delimiter
            # Check if this is preceded by a " or ' without closing
            # Look for opening " before the garbled bytes
            open_quote_pos = -1
            for ch_byte in [0x22, 0x27]:  # " or '
                pos = new_line.rfind(ch_byte, 0, qpos)
                if pos != -1:
                    # Found opening quote, check if there's a matching closing one
                    # between pos+1 and qpos
                    if new_line.find(ch_byte, pos + 1, qpos) == -1:
                        open_quote_pos = pos
                        open_quote_byte = ch_byte
                        break

            if open_quote_pos != -1:
                # Replace ? with the closing quote character
                new_line[qpos] = open_quote_byte  # ' or "
                fixed += 1
                print(f"FIXED line {i + 1}: ? -> {chr(open_quote_byte)} closing string")
            else:
                # If we can't find an opening quote, just ignore
                pass

        elif next_byte in (0x20, 0x7D):  # ?<space> or ?}
            # ? followed by space or } - likely missing closing string delimiter
            open_quote_pos = -1
            for ch_byte in [0x22, 0x27]:
                pos = new_line.rfind(ch_byte, 0, qpos)
                if pos != -1:
                    if new_line.find(ch_byte, pos + 1, qpos) == -1:
                        open_quote_pos = pos
                        open_quote_byte = ch_byte
                        break
            if open_quote_pos != -1:
                new_line[qpos] = open_quote_byte
                fixed += 1
                print(f"FIXED line {i + 1}: ? -> {chr(open_quote_byte)} closing string (space/brace after)")

        elif next_byte == 0x7D:  # ?}
            # ?} - this might be garbled { in f-string context
            # Check if there's a matching }
            pass

        idx = qpos + 1

    lines[i] = bytes(new_line)

content = b"\n".join(lines)
with open(filepath, "wb") as f:
    f.write(content)

print(f"\nTotal fixes: {fixed}")
