with open(r"webnet\EntertainmentNet\game_mode\game_memory_manager.py", "rb") as f:
    content = f.read()

# Fix line 109: 'garbledchinese?),\n -> 'garbledchinese'),\n
# The pattern: some bytes followed by 0x3F (?) followed by ),
# Replace with: same bytes followed by ') (0x27)

# Find specific pattern: \x97?),
old = b"\x97?),"
new = b"\x97'),"
content = content.replace(old, new)

print(f"Found {old!r}: {'yes' if old in content else 'nope'}")

# Also check for other ?), patterns

# For each occurrence of ?), check if it's preceded by a high-byte (0x80+) character on the same line
# This pattern indicates a corrupt closing quote
lines = content.split(b"\n")
fixed = 0
for i, line in enumerate(lines):
    # Find ?), preceded by non-ASCII bytes within a single-quoted context
    # Simple heuristic: if we see '...?...)' then fix
    idx = 0
    new_line = bytearray(line)
    modified = False
    while True:
        pos = new_line.find(b"?),", idx)
        if pos == -1:
            break
        # Check if preceded by high-byte char (to confirm this is inside garbled text)
        if pos > 0 and new_line[pos - 1] >= 0x80:
            new_line[pos] = 0x27  # ' -> '
            fixed += 1
            idx = pos + 1
            modified = True
        else:
            idx = pos + 1
    if modified:
        lines[i] = bytes(new_line)

content = b"\n".join(lines)
print(f"Fixed {fixed} closing quote issues")

with open(r"webnet\EntertainmentNet\game_mode\game_memory_manager.py", "wb") as f:
    f.write(content)

print("Done!")
