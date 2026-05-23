
filepath = r"webnet\EntertainmentNet\game_mode\game_memory_manager.py"
with open(filepath, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

lines = content.split("\n")
fixed_count = 0

for i, line in enumerate(lines):
    stripped = line.rstrip()
    if not stripped:
        continue

    # Fix triple-quoted docstrings ending with ?" instead of """
    if stripped.lstrip().startswith('"""'):
        clean = stripped.rstrip()
        if clean.endswith('?""') and not clean.endswith('?"""'):
            lines[i] = stripped.rstrip()[:-2] + '"""'
            fixed_count += 1
            print(f"FIXED line {i + 1}: docstring closing")
            continue

    # Fix single-quoted strings ending with ? instead of '
    # Look for patterns like ='...?...' or ('...?' or , '...?'
    import re

    # Case: 'something?) - missing closing quote before )
    m = re.match(r"^(.*\bsave_name=data\.get\('save_name',\s*)'([^']*)\?(,?\s*\)?\s*)$", clean)
    if m:
        lines[i] = m.group(1) + "'" + m.group(2) + "'" + m.group(3)
        fixed_count += 1
        print(f"FIXED line {i + 1}: save_name string")
        continue

# Write back
with open(filepath, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))

print(f"\nTotal fixes: {fixed_count}")
