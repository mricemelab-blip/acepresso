
import json
import re
import os

output_dir = '/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso'
images_dir = os.path.join(output_dir, 'images')

with open(os.path.join(output_dir, '_ch2_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

content_blocks = data['content_blocks']
headings = data['headings']
table_count = data['table_count']
image_count = data['image_count']

def html_escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def classify_card(text):
    if text.startswith('要点：') or text.startswith('要点:'):
        sep = '：' if '：' in text[:5] else ':'
        content = text.split(sep, 1)[1]
        return 'card-tip', '要点', content
    if re.match(r'^❌\s*错误做法', text):
        content = re.split(r'[：:]', text, 1)[1] if re.search(r'[：:]', text) else text
        return 'card-wrong', '✗ 错误', content
    if re.match(r'^✓\s*正确做法', text):
        content = re.split(r'[：:]', text, 1)[1] if re.search(r'[：:]', text) else text
        return 'card-right', '✓ 正确', content
    if re.match(r'^(常见)?误区[：:]', text):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-warn', '⚠ 误区', content
    if text.startswith('场景：') or text.startswith('场景:'):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-scene', '📋 场景', content
    if re.match(r'^记忆(提示|口诀)[：:]', text):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-memory', '🧠 记忆', content
    if re.match(r'^🎯\s*教练小[Ｔt]ips[：:]', text):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-tip', '💡 教练提示', content
    return None, None, text

print('Script loaded successfully')
