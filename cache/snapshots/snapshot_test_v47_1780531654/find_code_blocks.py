import re

input_path = r"C:\Users\User\.gemini\antigravity-ide\scratch\doutor\escopo_doutor_deserialized.md"
output_path = r"C:\Users\User\.gemini\antigravity-ide\scratch\doutor\code_blocks_manifest.txt"

with open(input_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

manifest = []
in_code_block = False
code_block_lang = ""
code_block_start = 0

for i, line in enumerate(lines):
    if line.startswith("```"):
        if not in_code_block:
            in_code_block = True
            code_block_lang = line.strip().replace("```", "")
            code_block_start = i
        else:
            in_code_block = False
            # Look at 10 lines preceding the code block to find file name
            context = []
            start_context = max(0, code_block_start - 10)
            for j in range(start_context, code_block_start):
                context.append(f"{j+1}: {lines[j].strip()}")
            
            manifest.append({
                "lang": code_block_lang,
                "start_line": code_block_start + 1,
                "end_line": i + 1,
                "context": context
            })

with open(output_path, 'w', encoding='utf-8') as f:
    for idx, item in enumerate(manifest):
        f.write(f"=== Code Block {idx} ({item['lang']}) ===\n")
        f.write(f"Lines: {item['start_line']} to {item['end_line']}\n")
        f.write("Preceding Context:\n")
        for ctx in item['context']:
            f.write(f"  {ctx}\n")
        f.write("\n")

print(f"Manifest written to {output_path}")
