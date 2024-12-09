import json

# 读取 JSON 文件
with open('src/ocr_data_2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 遍历数据并转换 text 部分的 Unicode 字符
for item in data['result']:
    # 将 Unicode 转义字符转换为中文字符
    item['text'] = item['text']

# 将转换后的数据写回原文件
with open('your_file.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

# 可选：打印转换后的结果
for item in data['result']:
    print(item['text'])
