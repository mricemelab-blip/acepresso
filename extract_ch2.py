import zipfile
import xml.etree.ElementTree as ET
import re
import os
import shutil
import copy

docx_path = "/Coze/Drive/Arise/ACEpresso教辅_合订本v4.1(3)_1790770742723_5bgi.docx"
output_dir = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"
images_dir = os.path.join(output_dir, "images")
os.makedirs(images_dir, exist_ok=True)

# Namespace map
nsmap = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'v': 'urn:schemas-microsoft-com:vml',
    'o': 'urn:schemas-microsoft-com:office:office',
}
w = nsmap['w']

def wn(tag):
    return f'{{{w}}}{tag}'

with zipfile.ZipFile(docx_path, 'r') as z:
    # Load relationships for images
    rels = {}
    try:
        with z.open('word/_rels/document.xml.rels') as rf:
            rtree = ET.parse(rf)
            rroot = rtree.getroot()
            ns_rels = 'http://schemas.openxmlformats.org/package/2006/relationships'
            for rel in rroot.findall(f'{{{ns_rels}}}Relationship'):
                rid = rel.get('Id')
                target = rel.get('Target')
                rtype = rel.get('Type', '')
                rels[rid] = {'target': target, 'type': rtype}
    except:
        pass

    with z.open('word/document.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()

body = root.find(wn('body'))

# Collect all body-level elements
elements = list(body)

# Find chapter boundaries
ch2_start = None
ch3_start = None
for i, el in enumerate(elements):
    tag = el.tag.split('}')[-1]
    if tag == 'p':
        pPr = el.find(wn('pPr'))
        if pPr is not None:
            pStyle = pPr.find(wn('pStyle'))
            if pStyle is not None:
                sv = pStyle.get(wn('val'), '')
                if sv == '3':
                    text = ''.join(t.text or '' for t in el.findall('.//' + wn('t')))
                    if text.strip().startswith('第2章'):
                        ch2_start = i
                    elif text.strip().startswith('第3章'):
                        ch3_start = i

print(f"Ch2: {ch2_start} -> {ch3_start}")

# Helper: get paragraph text
def get_text(el):
    return ''.join(t.text or '' for t in el.findall('.//' + wn('t'))).strip()

# Helper: get paragraph style
def get_style(el):
    pPr = el.find(wn('pPr'))
    if pPr is not None:
        pStyle = pPr.find(wn('pStyle'))
        if pStyle is not None:
            return pStyle.get(wn('val'), '')
    return ''

# Helper: extract images from a paragraph/table element
def extract_images(el, fig_counter):
    images = []
    # w:drawing elements
    for drawing in el.findall('.//' + wn('drawing')):
        for blip in drawing.findall('.//' + '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
            rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if rid and rid in rels:
                images.append(rid)
    # w:pict elements
    for pict in el.findall('.//' + wn('pict')):
        for img_data in pict.findall('.//' + '{urn:schemas-microsoft-com:vml}imagedata'):
            rid = img_data.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if rid and rid in rels:
                images.append(rid)
    return images

# Helper: save image from docx zip
def save_image(rid, fig_num):
    if rid not in rels:
        return None
    target = rels[rid]['target']
    # Target is like "media/image1.png"
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
        print(f"  Error saving image {rid} ({img_path}): {e}")
        return None

# Process table element
def process_table(tbl_el, fig_counter):
    rows = []
    for tr in tbl_el.findall(wn('tr')):
        cells = []
        for tc in tr.findall(wn('tc')):
            cell_text = []
            for p in tc.findall(wn('p')):
                t = get_text(p)
                if t:
                    cell_text.append(t)
            # Check for images in cell
            cell_images = extract_images(tc, fig_counter)
            cells.append({'text': '\n'.join(cell_text), 'images': cell_images})
            fig_counter += len(cell_images)
        rows.append(cells)
    return rows, fig_counter

# Skip patterns
skip_markers = [
    '学员预习专用', '学员课后复习专用', '学员复习专用',
    '本章总结', '全章重点汇总', '常见误区', '全章小结',
    '复习与自测', '思考与练习', '自测题',
    '本章收口总结', '本章核心回顾', '知识结构', '重点内容',
    '行为改变评估自检清单', '知识衔接', '章末复习',
    '本章核心知识点', '核心板块速览', '必背关键数字',
    '名词与缩写', '名词缩写', '预习思考',
]

def should_skip_section(text):
    """Check if this paragraph starts a section that should be entirely skipped"""
    for m in skip_markers:
        if text.startswith(m):
            return True
    return False

def is_question_paragraph(text):
    """Check if paragraph is a question/quiz item"""
    # Q1, Q2 patterns
    if re.match(r'^[Qq]\d+[\s.:：]', text):
        return True
    if re.match(r'^答案[\s提示：]', text) or text == '答案':
        return True
    if re.match(r'^答案提示', text):
        return True
    if re.match(r'^[A-D][\s.:：．]', text):
        return True
    if re.match(r'^[（\(][A-D][）\)]', text):
        return True
    # Standalone "A." "B." etc
    if re.match(r'^[A-D]\.\s', text):
        return True
    return False

def is_scaffold_only(text):
    """Check if paragraph is an empty scaffold marker"""
    patterns = ['📚 记忆技巧', '🎯 教练小Tips', '💡 关键思考', '💡 章节小节']
    for p in patterns:
        if text.strip() == p or text.strip().startswith(p):
            return True
    return False

# Main extraction
ch2_elements = elements[ch2_start:ch3_start]

# Classify content blocks
content_blocks = []  # list of dicts: type, text, style, html, etc.
fig_counter = 1
in_skip_section = False
skip_section_style = None

# Track headings for TOC
headings = []  # (level, text, id)

# Track tables
table_count = 0
image_count = 0
image_map = {}  # rid -> filename

i = 0
while i < len(ch2_elements):
    el = ch2_elements[i]
    tag = el.tag.split('}')[-1]
    
    if tag == 'tbl':
        # Process table
        rows, fig_counter = process_table(el, fig_counter)
        # Save any images found in table
        for row in rows:
            for cell in row:
                for rid in cell.get('images', []):
                    if rid not in image_map:
                        fname = save_image(rid, len(image_map) + 1)
                        if fname:
                            image_map[rid] = fname
                            image_count += 1
        content_blocks.append({'type': 'table', 'rows': rows})
        table_count += 1
        in_skip_section = False
        i += 1
        continue
    
    if tag != 'p':
        i += 1
        continue
    
    text = get_text(el)
    style = get_style(el)
    
    # Extract images from paragraph
    para_images = extract_images(el, fig_counter)
    for rid in para_images:
        if rid not in image_map:
            fname = save_image(rid, len(image_map) + 1)
            if fname:
                image_map[rid] = fname
                image_count += 1
    fig_counter += len(para_images)
    
    # Handle skip sections
    if in_skip_section:
        # Check if we've left the skip section (new heading at same or higher level)
        if style in ['3', '4', '5']:
            # Check if this is a new section we should NOT skip
            if not should_skip_section(text) and not is_question_paragraph(text):
                # Check if this is "正文部分" or a numbered section heading
                if style == '4' and (re.match(r'^\d+\s', text) or text == '正文部分'):
                    in_skip_section = False
                elif style == '3':
                    in_skip_section = False
                elif style == '5' and re.match(r'^[\d一二三四五六七八九十]', text):
                    in_skip_section = False
                else:
                    i += 1
                    continue
            else:
                i += 1
                continue
        else:
            i += 1
            continue
    
    # Check if this starts a skip section
    if should_skip_section(text):
        in_skip_section = True
        i += 1
        continue
    
    # Check for question paragraphs
    if is_question_paragraph(text):
        i += 1
        continue
    
    # Check for empty scaffold markers
    if is_scaffold_only(text):
        i += 1
        continue
    
    # Check for 💡 章节小节 markers
    if '💡 章节小节' in text:
        i += 1
        continue
    
    # Check for ✍️小节回顾 markers
    if '✍️小节回顾' in text or '✍️ 小节回顾' in text:
        i += 1
        continue
    
    # Empty paragraph
    if not text and not para_images:
        i += 1
        continue
    
    # Build content block
    block = {'type': 'text', 'text': text, 'style': style, 'images': para_images}
    
    # Classify headings
    if style == '3':  # H3 -> h2
        hid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text).strip('-').lower()
        block['heading_level'] = 2
        block['heading_id'] = hid
        headings.append((2, text, hid))
    elif style == '4':  # H4 -> h3
        hid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text).strip('-').lower()
        # Deduplicate
        existing_ids = [h[2] for h in headings]
        base_id = hid
        counter = 2
        while hid in existing_ids:
            hid = f"{base_id}-{counter}"
            counter += 1
        block['heading_id'] = hid
        block['heading_level'] = 3
        headings.append((3, text, hid))
    elif style == '5':  # H5 -> h4
        hid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text).strip('-').lower()
        existing_ids = [h[2] for h in headings]
        base_id = hid
        counter = 2
        while hid in existing_ids:
            hid = f"{base_id}-{counter}"
            counter += 1
        block['heading_id'] = hid
        block['heading_level'] = 4
        headings.append((4, text, hid))
    elif style == '6':  # H6 -> h5
        hid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text).strip('-').lower()
        existing_ids = [h[2] for h in headings]
        base_id = hid
        counter = 2
        while hid in existing_ids:
            hid = f"{base_id}-{counter}"
            counter += 1
        block['heading_id'] = hid
        block['heading_level'] = 5
        headings.append((5, text, hid))
    
    content_blocks.append(block)
    i += 1

print(f"Content blocks: {len(content_blocks)}")
print(f"Tables: {table_count}")
print(f"Images: {image_count}")
print(f"Headings: {len(headings)}")

# Save intermediate data for HTML generation
import json
data = {
    'content_blocks': content_blocks,
    'headings': headings,
    'table_count': table_count,
    'image_count': image_count,
    'image_map': image_map,
}
with open(os.path.join(output_dir, '_ch2_data.json'), 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Data saved to _ch2_data.json")

# Print some stats
heading_counts = {}
for h in headings:
    heading_counts[h[0]] = heading_counts.get(h[0], 0) + 1
print(f"Heading distribution: {heading_counts}")

# Print first 20 content blocks for verification
print("\n--- First 20 content blocks ---")
for i, b in enumerate(content_blocks[:20]):
    if b['type'] == 'table':
        print(f"  [{i}] TABLE ({len(b['rows'])} rows)")
    else:
        t = b.get('text', '')[:80]
        print(f"  [{i}] style={b.get('style','')} heading={b.get('heading_level','')} \"{t}\"")

