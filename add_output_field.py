"""
Script untuk menambahkan field 'output' ke semua return jsonify() dalam chat_routes.py
ADDITIVE: Tidak menghapus field lama, hanya menambahkan 'output'
"""

import re

# Baca file
with open('routes/chat_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern untuk mencari return jsonify yang sudah punya llm_answer
pattern = r'(return jsonify\(\{[^}]*"llm_answer":\s*llm_answer(?!,\s*"output":))'

# Function untuk menambahkan output field setelah llm_answer
def add_output(match):
    original = match.group(1)
    # Tambahkan output field setelah llm_answer
    modified = original.replace('"llm_answer": llm_answer', '"llm_answer": llm_answer,\n        "output": llm_answer  # ADDITIVE: Laravel expects \'output\' key')
    return modified

# Replace semua occurrence
new_content = re.sub(pattern, add_output, content)

# Tulis kembali
with open('routes/chat_routes.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Berhasil menambahkan field 'output' ke semua return statement!")
print("Field lama tetap ada (ADDITIVE approach)")
