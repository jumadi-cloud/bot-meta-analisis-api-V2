#!/usr/bin/env python3
"""
ADDITIVE Script: Tambahkan field 'output' tepat setelah 'llm_answer' 
tanpa duplikasi dan tanpa menghapus field lama.
"""

with open('routes/chat_routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

output_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    output_lines.append(line)
    
    # Cek jika ini line dengan "llm_answer": llm_answer,
    if '"llm_answer": llm_answer,' in line:
        # Cek apakah line berikutnya sudah punya "output":
        if i + 1 < len(lines) and '"output":' not in lines[i + 1]:
            # Hitung indentasi
            indent = len(line) - len(line.lstrip())
            # Tambahkan line output dengan indentasi yang sama
            output_lines.append(' ' * indent + '"output": llm_answer,  # ADDITIVE: Laravel expects \'output\' key\n')
    
    i += 1

# Tulis kembali
with open('routes/chat_routes.py', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("✅ Berhasil! Field 'output' ditambahkan ke semua return statement")
print("✅ No duplicates, ADDITIVE approach maintained")
