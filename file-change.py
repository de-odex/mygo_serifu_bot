import json

# 讀取未格式化的 JSON 檔案
input_file = "src/ocr_data.json"   # 輸入檔案名
output_file = "src/new.json"  # 輸出檔案名

# 讀取原始 JSON 串
with open(input_file, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# 格式化 JSON，寫入新檔案
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(raw_data, f, ensure_ascii=False, indent=4)

print("JSON 格式化完成，結果已儲存至:", output_file)