import zipfile
import xml.etree.ElementTree as ET
import re
import os
import json

docx_path = "/Coze/Drive/Arise/ACEpresso教辅_合订本v4.1(3)_1790770742723_5bgi.docx"
output_dir = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"
images_dir = os.path.join(output_dir, "images")
os.makedirs(images_dir, exist_ok=True)

nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
w = nsmap['w']
def wn(tag): return f'{{{w}}}{tag}'

with zipfile.ZipFile(docx_path, 'r') as z:
    rels = {}
    with z.open('word/_rels/document.xml.rels') as rf:
        rtree = ET.parse(rf)
        rroot = rtree.getroot()
        ns_rels = 'http://schemas.openxmlformats.org/package/2006/relationships'
        for rel in rroot.findall(f'{{{ns_rels}}}Relationship'):
            rels[rel.get('Id')] = {'target': rel.get('Target')}
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

def save_image(rid, fig_num):
    if rid not in rels: return None
    target = rels[rid]['target']
    img_path = 'word/' + target.replace('\\', '/')
    ext = os.path.splitext(target)[1]
    fname = f"ch2_fig{fig_num}{ext}"
    out_path = os.path.join(images_dir, fname)
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            data = z.read(img_path)
        with open(out_path, 'wb') as dst:
            dst.write(data)
        return fname
    except:
        return None

def extract_images(el, image_map):
    images = []
    for drawing in el.findall('.//' + wn('drawing')):
        for blip in drawing.findall('.//' + '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
            rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if rid and rid in rels:
                if rid not in image_map:
                    fname = save_image(rid, len(image_map) + 1)
                    if fname:
                        image_map[rid] = fname
                if rid in image_map:
                    images.append(image_map[rid])
    for pict in el.findall('.//' + wn('pict')):
        for img_data in pict.findall('.//' + '{urn:schemas-microsoft-com:vml}imagedata'):
            rid = img_data.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if rid and rid in rels:
                if rid not in image_map:
                    fname = save_image(rid, len(image_map) + 1)
                    if fname:
                        image_map[rid] = fname
                if rid in image_map:
                    images.append(image_map[rid])
    return images

def process_table(tbl_el, image_map):
    rows = []
    for tr in tbl_el.findall(wn('tr')):
        cells = []
        for tc in tr.findall(wn('tc')):
            cell_parts = []
            for p in tc.findall(wn('p')):
                t = get_text(p)
                if t:
                    cell_parts.append(t)
            cells.append('\n'.join(cell_parts))
        rows.append(cells)
    return rows

# Find chapter boundaries
ch2_start = ch3_start = None
for i, el in enumerate(elements):
    tag = el.tag.split('}')[-1]
    if tag == 'p' and get_style(el) == '3':
        text = get_text(el)
        if text.startswith('第2章'): ch2_start = i
        elif text.startswith('第3章'): ch3_start = i

ch2_elements = elements[ch2_start:ch3_start]

# Find main content and review boundaries
main_start = review_start = None
for i, el in enumerate(ch2_elements):
    tag = el.tag.split('}')[-1]
    if tag != 'p': continue
    text = get_text(el)
    style = get_style(el)
    if text.strip() == '正文部分' and style == '4':
        main_start = i
    if text.strip() == '学员复习专用' and style == '4':
        review_start = i
        break

main_elements = ch2_elements[main_start:review_start] if review_start else ch2_elements[main_start:]

# Extraction
content_blocks = []
headings = []
table_count = 0
image_map = {}
skip_subsection = False

def make_id(text, existing):
    hid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text).strip('-').lower()
    if not hid: hid = 'section'
    base = hid
    c = 2
    while hid in existing:
        hid = f"{base}-{c}"
        c += 1
    return hid

def is_question(text):
    if re.match(r'^[Qq]\d+[\s.:：]', text): return True
    if text.strip() in ['答案', '答案提示'] or re.match(r'^答案[\s提示：:]', text): return True
    if re.match(r'^[A-D][\s.．:：]', text) and len(text) < 300: return True
    if re.match(r'^[（\(][A-D][）\)]', text): return True
    return False

def is_scaffold(text):
    """Check if this is a scaffold marker (with or without space, any case)"""
    t = text.strip().lower()
    # Normalize: remove spaces for matching
    t_no_space = t.replace(' ', '').replace('\u3000', '')
    patterns = ['📚记忆技巧', '🎯教练小tips', '💡关键思考', '💡章节小节',
                '【记忆技巧】', '记忆技巧', '教练小tips']
    for p in patterns:
        p_no_space = p.replace(' ', '')
        if t_no_space == p_no_space:
            return True  # Empty scaffold
        if t_no_space.startswith(p_no_space) and len(t_no_space) > len(p_no_space) + 2:
            return False  # Has content after marker
    return False

def is_scaffold_empty(text):
    t = text.strip().lower().replace(' ', '').replace('\u3000', '')
    empty_patterns = ['📚记忆技巧', '🎯教练小tips', '💡关键思考', '💡章节小节',
                      '【记忆技巧】', '✍️小节回顾', '✍️小节回顾']
    for p in empty_patterns:
        if t == p:
            return True
    return False

def is_skip_marker_text(text):
    markers = [
        '本章总结', '全章重点汇总', '全章小结', '常见误区',
        '复习与自测', '思考与练习', '自测题',
        '本章收口总结', '本章核心回顾', '知识衔接', '章末复习',
        '行为改变评估自检清单', '知识结构', '重点内容',
        '知识点总结', '练习与应用',
    ]
    for m in markers:
        if text.strip() == m or text.strip().startswith(m):
            return True
    return False

i = 0
while i < len(main_elements):
    el = main_elements[i]
    tag = el.tag.split('}')[-1]
    
    if tag == 'tbl':
        if not skip_subsection:
            rows = process_table(el, image_map)
            content_blocks.append({'type': 'table', 'rows': rows})
            table_count += 1
        i += 1
        continue
    
    if tag != 'p':
        i += 1
        continue
    
    text = get_text(el)
    style = get_style(el)
    
    # Skip markers start subsections to skip
    if style in ['4', '5', '6'] and is_skip_marker_text(text):
        skip_subsection = True
        i += 1
        continue
    
    # In skip mode, resume at new content heading
    if skip_subsection:
        if style == '4' and re.match(r'^\d+\s', text):
            skip_subsection = False
        elif style == '3':
            skip_subsection = False
        elif style == '5' and (re.match(r'^[\d]+[\.、]', text) or re.match(r'^[一二三四五六七八九十]+[、．.]', text)):
            skip_subsection = False
        else:
            i += 1
            continue
    
    # Skip questions
    if is_question(text):
        i += 1
        continue
    
    # Skip empty scaffolds
    if is_scaffold_empty(text):
        i += 1
        continue
    
    # Skip 小节回顾 and its sub-sections
    if '小节回顾' in text:
        skip_subsection = True
        i += 1
        continue
    
    # Skip 💡 章节小节
    if '💡 章节小节' in text or '💡章节小节' in text:
        i += 1
        continue
    
    # Skip sub-section markers within review blocks
    if text.strip() in ['互动考题', '记忆小本', '基本原理']:
        i += 1
        continue
    
    # Empty paragraph (may have images)
    if not text:
        imgs = extract_images(el, image_map)
        if imgs:
            content_blocks.append({'type': 'images_only', 'images': imgs})
        i += 1
        continue
    
    # Extract images
    imgs = extract_images(el, image_map)
    
    # Build block
    block = {'type': 'text', 'text': text, 'style': style, 'images': imgs}
    
    existing_ids = [h[2] for h in headings]
    if style == '3':
        hid = make_id(text, existing_ids)
        block.update({'heading_level': 2, 'heading_id': hid})
        headings.append((2, text, hid))
    elif style == '4':
        # Skip "正文部分" from headings
        if text.strip() == '正文部分':
            block['style'] = '4'  # keep style but don't add heading
        else:
            hid = make_id(text, existing_ids)
            block.update({'heading_level': 3, 'heading_id': hid})
            headings.append((3, text, hid))
    elif style == '5':
        hid = make_id(text, existing_ids)
        block.update({'heading_level': 4, 'heading_id': hid})
        headings.append((4, text, hid))
    elif style == '6':
        hid = make_id(text, existing_ids)
        block.update({'heading_level': 5, 'heading_id': hid})
        headings.append((5, text, hid))
    
    content_blocks.append(block)
    i += 1

# Final verification
print(f"Content blocks: {len(content_blocks)}")
print(f"Tables: {table_count}")
print(f"Images: {len(image_map)}")
print(f"Headings: {len(headings)}")

# Check residuals
residuals = {'💡': 0, '📚': 0, '🎯': 0, '记忆技巧': 0, '教练小Tips': 0, '关键思考': 0, '章节小节': 0}
for b in content_blocks:
    if b['type'] == 'text':
        t = b['text']
        for key in residuals:
            if key in t:
                residuals[key] += 1
print(f"\nResidual check: {residuals}")

# Save
data = {
    'content_blocks': content_blocks,
    'headings': headings,
    'table_count': table_count,
    'image_count': len(image_map),
    'image_map': image_map,
}
with open(os.path.join(output_dir, '_ch2_data.json'), 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# List images
print(f"\nImages saved:")
for rid, fname in image_map.items():
    print(f"  {rid} -> {fname}")

print(f"\nHeadings:")
for h in headings:
    print(f"  H{h[0]}: {h[1]}")

print("\nDone.")
