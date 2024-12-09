import json


def to_unicode_escape(text):
    """将中文字符转换为 Unicode 转义字符"""
    return ''.join([f"\\u{ord(c):04x}" for c in text])



def unicode_to_string(encoded_text):
    """将 Unicode 转义字符转换为中文字符"""
    return bytes(encoded_text, "utf-8").decode("unicode_escape")


def text_process(text):
    # 加载 JSON 数据
    with open('src/ocr_data_3.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    # 搜索台词
    results = []
    for item in data['result']:
         if text in item['text']:
            results.append({
                "text": item["text"],
                "episode": item["episode"],
                "frame_start": item["frame_start"],
                "frame_end": item["frame_end"],
            })


    # 返回搜索结果
    return results



if __name__ == '__main__':
    print(text_process("小祥退出"))