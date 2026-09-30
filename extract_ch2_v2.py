import zipfile
import xml.etree.ElementTree as ET
import re
import os
import json

docx_path = "/Coze/Drive/Arise/ACEpresso教辅_合订本v4.1(3)_1790770742723_5bgi.docx"
output_dir = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"
images_dir = os.path.join(output_dir, "images")
os.makedirs(images_dir, exist_ok=True)

nsmap = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}
w = nsmap['w']

def wn(tag):
    return f'{{{w}}}{tag}'

with zipfile.ZipFile(docx_path, 'r') as z:
    rels = {}
    try:
        with z.open('word/_rels/document.xml.rels') as rf:
            rtree = ET.parse(rf)
            rroot = rtree.getroot()
            ns_rels = 'http://schemas.openxmlformats.org/package/2006/relationships'
            for rel in rroot.findall(f'{{{ns_rels}}}Relationship'):
                rid = rel.get('Id')
                target = rel.get('Target')
                rels[rid] = {'target': target}
    except:
        pass

    with z.open('word/document.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

body = root.find(wn('body'))
elements = list(body)

def get_text(el):
    return ''.join(t.text or '' for t in el.findall('.//' + wn('t'))).strip()

def get_style(el):
    pPr = el.find(wn('pPr'))
    if pPr is not None:
        pStyle = pPr.find(wn('pStyle'))
        if pStyle is not None:
            return pStyle.get(wn('val'), '')
    return ''

def extract_images(el, fig_counter, image_map):
    images = []
    for drawing in el.findall('.//' + wn('drawing')):
        for blip in drawing.findall('.//' + '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
            rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if rid and rid in rels and rid not in image_map:
                fname = save_image(rid, len(image_map) + 1)
                if fname:
                    image_map[rid] = fname
                    images.append(fname)
    for pict in el.findall('.//' + wn('pict')):
        for img_data in pict.findall('.//' + '{urn:schemas-microsoft-com:vml}imagedata'):
            rid = img_data.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if rid and rid in rels and rid not in image_map:
                fname = save_image(rid, len(image_map) + 1)
                if fname:
                    image_map[rid] = fname
                    images.append(fname)
    return images

def save_image(rid, fig_num):
    if rid not in rels:
        return None
    target = rels[rid]['target']
    img_path = 'word/' + target.replace('\\', '/')
    ext = os.path.splitext(target)[1]
    fname = f"ch2_fig{fig_num}{ext}"
    out_path = os.path.join(images_dir, fname)
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            with z.open(img_path) as src:
                data = src.read()
            with open(out_path, 'wb') as dst:
                dst.write(data)
        return fname
    except Exception as e:
        print(f"  Error saving image {rid}: {e}")
        return None

# Find chapter boundaries
ch2_start = None
ch3_start = None
for i, el in enumerate(elements):
    tag = el.tag.split('}')[-1]
    if tag == 'p':
        style = get_style(el)
        if style == '3':
            text = get_text(el)
            if text.startswith('第2章'):
                ch2_start = i
            elif text.startswith('第3章'):
                ch3_start = i

ch2_elements = elements[ch2_start:ch3_start]

# State machine for section tracking
# States: PREVIEW, MAIN_CONTENT, REVIEW
state = 'PREVIEW'  # starts in preview mode

content_blocks = []
headings = []
table_count = 0
image_count = 0
image_map = {}

def process_table(tbl_el):
    global table_count, image_count
    rows = []
    for tr in tbl_el.findall(wn('tr')):
        cells = []
        for tc in tr.findall(wn('tc')):
            cell_texts = []
            for p in tc.findall(wn('p')):
                t = get_text(p)
                imgs = extract_images(p, image_count, image_map)
                if imgs:
                    image_count += len(imgs)
                if t:
                    cell_texts.append(t)
                if imgs:
                    cell_texts.extend([f'[IMG:{img}]' for img in imgs])
            cells.append({'text': '\n'.join(cell_texts), 'has_images': any('[IMG:' in c for c in cell_texts)})
        rows.append(cells)
    table_count += 1
    return rows

def make_heading_id(text, existing_ids):
    hid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text).strip('-').lower()
    if not hid:
        hid = 'section'
    base_id = hid
    counter = 2
    while hid in existing_ids:
        hid = f"{base_id}-{counter}"
        counter += 1
    return hid

def classify_card(text):
    """Classify text into card types"""
    if text.startswith('要点：') or text.startswith('要点:'):
        content = text.split('：', 1)[1] if '：' in text else text.split(':', 1)[1]
        return 'tip', '要点', content
    if text.startswith('❌ 错误做法') or text.startswith('❌错误做法'):
        content = text.split('：', 1)[1] if '：' in text else text.split('：', 1)[1] if '：' in text else text[6:]
        return 'wrong', '✗ 错误', content
    if text.startswith('✓ 正确做法') or text.startswith('✓正确做法'):
        content = text.split('：', 1)[1] if '：' in text else text[6:]
        return 'right', '✓ 正确', content
    if text.startswith('常见误区：') or text.startswith('常见误区:') or text.startswith('误区：') or text.startswith('误区:'):
        content = text.split('：', 1)[1] if '：' in text else text.split(':', 1)[1]
        return 'warn', '⚠ 误区', content
    if text.startswith('场景：') or text.startswith('场景:'):
        content = text.split('：', 1)[1] if '：' in text else text.split(':', 1)[1]
        return 'scene', '📋 场景', content
    if text.startswith('记忆提示：') or text.startswith('记忆口诀：') or text.startswith('记忆提示:') or text.startswith('记忆口诀:'):
        content = text.split('：', 1)[1] if '：' in text else text.split(':', 1)[1]
        return 'memory', '🧠 记忆', content
    if '记忆' in text and len(text) < 200 and ('：' in text or ':' in text):
        # Short paragraph with memory keyword and colon
        return 'memory', '🧠 记忆', text
    return None, None, text

def is_question(text):
    if re.match(r'^[Qq]\d+[\s.:：]', text):
        return True
    if re.match(r'^答案[\s提示：:]', text) or text.strip() == '答案':
        return True
    if re.match(r'^答案提示', text):
        return True
    if re.match(r'^[A-D][\s.．:：]', text) and len(text) < 200:
        return True
    if re.match(r'^[（\(][A-D][）\)]', text):
        return True
    return False

def is_skip_marker(text):
    """Check if text is a marker for a section to skip entirely"""
    skip_starts = [
        '学员预习专用', '学员课后复习专用', '学员复习专用',
        '本章总结', '全章重点汇总', '全章小结',
        '复习与自测', '思考与练习', '自测题',
        '本章收口总结', '本章核心回顾', '知识衔接', '章末复习',
        '行为改变评估自检清单', '预习思考与练习',
        '本章核心知识点', '预习思考',
    ]
    for s in skip_starts:
        if text.strip().startswith(s):
            return True
    return False

def is_skip_heading(text, style):
    """Check if this heading starts a skip section"""
    if is_skip_marker(text):
        return True
    # Specific patterns that indicate skip sections
    skip_headings = [
        '知识结构', '重点内容', '重点内容表', '关键数字', '名词与缩写', '名词缩写表',
        '核心板块速览', '必背关键数字', '一图速记', '学习路线',
        '本章核心', '学习目标', '本章内容',
        '知识点总结', '练习与应用',
    ]
    for s in skip_headings:
        if text.strip() == s or text.strip().startswith(s):
            return True
    return False

# Process elements
i = 0
skip_until_next_major = False
skip_level = None

while i < len(ch2_elements):
    el = ch2_elements[i]
    tag = el.tag.split('}')[-1]
    
    if tag == 'tbl':
        if not skip_until_next_major and state == 'MAIN_CONTENT':
            rows = process_table(el)
            content_blocks.append({'type': 'table', 'rows': rows})
        i += 1
        continue
    
    if tag != 'p':
        i += 1
        continue
    
    text = get_text(el)
    style = get_style(el)
    
    # State transitions
    if text.strip() == '正文部分' and style == '4':
        state = 'MAIN_CONTENT'
        skip_until_next_major = False
        i += 1
        continue
    
    if text.strip() in ['学员复习专用', '学员课后复习专用'] or text.strip().startswith('学员复习专用') or text.strip().startswith('学员课后复习专用'):
        state = 'REVIEW'
        skip_until_next_major = True
        i += 1
        continue
    
    if text.strip() in ['本章总结', '本章总结', '全章小结'] and style in ['3', '4']:
        state = 'REVIEW'
        skip_until_next_major = True
        i += 1
        continue
    
    # Skip everything outside MAIN_CONTENT
    if state != 'MAIN_CONTENT':
        i += 1
        continue
    
    # Skip question paragraphs
    if is_question(text):
        i += 1
        continue
    
    # Skip scaffold markers
    scaffold_patterns = ['📚 记忆技巧', '🎯 教练小Tips', '💡 关键思考', '💡 章节小节', '✍️小节回顾', '✍️ 小节回顾']
    if any(text.strip().startswith(p) for p in scaffold_patterns):
        # Check if there's actual content after the marker (in same paragraph)
        for p in scaffold_patterns:
            if text.strip().startswith(p) and len(text.strip()) > len(p) + 2:
                # Has content after marker - keep it but remove the marker prefix
                pass  # Will be processed as normal text below
            elif text.strip() == p or text.strip().startswith(p + '\n') or text.strip() == p:
                # Empty scaffold marker - skip
                i += 1
                continue
    
    # Skip empty paragraphs
    if not text:
        # Check for images
        imgs = extract_images(el, image_count, image_map)
        if imgs:
            image_count += len(imgs)
            content_blocks.append({'type': 'image', 'images': imgs})
        i += 1
        continue
    
    # Skip "小节回顾" sections and their content
    if '小节回顾' in text:
        skip_until_next_major = True
        i += 1
        continue
    
    # Skip "知识点总结" and "练习与应用" sections within MAIN_CONTENT
    if text.strip() in ['知识点总结', '练习与应用']:
        skip_until_next_major = True
        i += 1
        continue
    
    # Check if heading starts a skip sub-section
    if style in ['4', '5'] and is_skip_heading(text, style):
        skip_until_next_major = True
        i += 1
        continue
    
    # If we're in skip mode, check if we've reached a new content heading
    if skip_until_next_major:
        # Resume at numbered sections (1 xxx, 2 xxx, 3 xxx) or new major section
        if style == '4' and re.match(r'^\d+\s', text):
            skip_until_next_major = False
        elif style == '3':
            skip_until_next_major = False
        else:
            i += 1
            continue
    
    # Extract images
    imgs = extract_images(el, image_count, image_map)
    if imgs:
        image_count += len(imgs)
    
    # Build content block
    block = {'type': 'text', 'text': text, 'style': style, 'images': imgs}
    
    # Handle headings
    existing_ids = [h[2] for h in headings]
    if style == '3':
        hid = make_heading_id(text, existing_ids)
        block['heading_level'] = 2
        block['heading_id'] = hid
        headings.append((2, text, hid))
    elif style == '4':
        hid = make_heading_id(text, existing_ids)
        block['heading_level'] = 3
        block['heading_id'] = hid
        headings.append((3, text, hid))
    elif style == '5':
        hid = make_heading_id(text, existing_ids)
        block['heading_level'] = 4
        block['heading_id'] = hid
        headings.append((4, text, hid))
    elif style == '6':
        hid = make_heading_id(text, existing_ids)
        block['heading_level'] = 5
        block['heading_id'] = hid
        headings.append((5, text, hid))
    
    content_blocks.append(block)
    i += 1

print(f"Content blocks: {len(content_blocks)}")
print(f"Tables: {table_count}")
print(f"Images: {image_count}")
print(f"Headings: {len(headings)}")
h_counts = {}
for h in headings:
    h_counts[h[0]] = h_counts.get(h[0], 0) + 1
print(f"Heading distribution: {h_counts}")

# Print all headings
print("\n--- All headings ---")
for level, text, hid in headings:
    print(f"  H{level}: {text} (id={hid})")

# Print first 30 blocks
print("\n--- First 30 content blocks ---")
for i, b in enumerate(content_blocks[:30]):
    if b['type'] == 'table':
        print(f"  [{i}] TABLE ({len(b['rows'])} rows)")
    elif b['type'] == 'image':
        print(f"  [{i}] IMAGE ({b['images']})")
    else:
        t = b.get('text', '')[:80]
        hl = b.get('heading_level', '-')
        print(f"  [{i}] style={b.get('style','-')} H{hl} \"{t}\"")

# Print last 10 blocks
print("\n--- Last 10 content blocks ---")
for i, b in enumerate(content_blocks[-10:]):
    idx = len(content_blocks) - 10 + i
    if b['type'] == 'table':
        print(f"  [{idx}] TABLE ({len(b['rows'])} rows)")
    elif b['type'] == 'image':
        print(f"  [{idx}] IMAGE ({b['images']})")
    else:
        t = b.get('text', '')[:80]
        hl = b.get('heading_level', '-')
        print(f"  [{idx}] style={b.get('style','-')} H{hl} \"{t}\"")

# Save data
data = {
    'content_blocks': content_blocks,
    'headings': headings,
    'table_count': table_count,
    'image_count': image_count,
    'image_map': image_map,
}
with open(os.path.join(output_dir, '_ch2_data.json'), 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\nData saved.")
