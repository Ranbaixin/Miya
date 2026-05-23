with open(r"webnet\EntertainmentNet\game_mode\game_memory_manager.py", "rb") as f:
    content = f.read()

lines = content.split(b"\n")
fixed = 0

for i, line in enumerate(lines):
    if b"summary_lines.append" not in line and b"logger." not in line:
        continue

    # Pattern: "...garbled?)  - missing closing " before )
    # Find "somebytes?) with no closing "
    stripped = line.lstrip()

    # Find index of the opening " after .append( or similar
    idx_start = 0
    while True:
        quote_pos = stripped.find(b'"', idx_start)
        if quote_pos == -1:
            break

        # Scan forward to find matching closing )
        # Check if there's a ) before a closing "
        after_open = stripped[quote_pos + 1 :]
        close_paren_pos = after_open.find(b")")

        if close_paren_pos == -1:
            idx_start = quote_pos + 1
            continue

        # String content between " and )
        string_content = after_open[:close_paren_pos]

        # Check if this looks like garbled text (contains non-ASCII bytes)
        has_high_bytes = any(b >= 0x80 for b in string_content)

        if has_high_bytes:
            # Count " in string_content - if none, closing " is missing
            quote_count = string_content.count(b'"')
            if quote_count == 0:
                # Fix: insert " before )
                full_line_before_fix = stripped
                insert_pos = quote_pos + 1 + close_paren_pos
                new_line = bytearray(stripped)
                new_line.insert(insert_pos, 0x22)  # Insert "
                stripped = bytes(new_line)
                fixed += 1
                print(f'FIXED line {i + 1}: added closing " before )')

        idx_start = quote_pos + 1

    lines[i] = lines[i].replace(line.lstrip(), stripped, 1) if line.lstrip() != stripped else line.lstrip()

content = b"\n".join(lines)

with open(r"webnet\EntertainmentNet\game_mode\game_memory_manager.py", "wb") as f:
    f.write(content)

print(f"\nTotal fixes: {fixed}")
