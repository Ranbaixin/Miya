import re

filepath = r"webnet\EntertainmentNet\game_mode\game_memory_manager.py"
with open(filepath, "r", encoding="utf-8", errors="surrogateescape") as f:
    content = f.read()

lines = content.split("\n")
fixed_count = 0

for i, line in enumerate(lines):
    stripped = line.rstrip()
    orig = stripped

    # Fix: unterminated single-quoted strings ending with ?), or ?,
    # Pattern: garbled Chinese char followed by ? (instead of ') in a function call
    # Example: '链存椤?' -> '链存椤?'
    # The ? is a corrupt char that replaces the closing '

    # Fix 'garbled?) - single-quoted string with ? instead of closing '
    changed = True
    while changed:
        changed = False
        new = re.sub(
            r"(data\.get\(\s*'[^']*?)(\?(,\s*))",
            r"\1'\3",
            stripped,
        )
        if new != stripped:
            stripped = new
            changed = True
            fixed_count += 1
            continue

        # Fix just '..., garbled?' with closing paren/bracket
        new = re.sub(
            r"(=)(\s*)('[^']*\?)(\s*[,\)])",
            lambda m: m.group(1) + m.group(2) + m.group(3).rstrip("?") + m.group(4),
            stripped,
        )
        if new != stripped:
            stripped = new
            changed = True
            fixed_count += 1
            continue

        # Fix f-string with garbled ? inside: f"...some garbled?)"
        new = re.sub(
            r"(f\"[^\"]*?\?)(\",?)",
            r"\1\"\2",
            stripped,
        )
        if new != stripped:
            stripped = new
            changed = True
            fixed_count += 1
            continue

    if stripped != orig:
        if orig.strip():
            print(f"FIXED line {i + 1}: {orig.strip()[:60]}... -> {stripped.strip()[:60]}...")
        lines[i] = lines[i].replace(orig, stripped, 1) if orig in lines[i] else stripped

# Write back
with open(filepath, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))

print(f"\nTotal fixes: {fixed_count}")
