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
    except Exception as e:
        print(f"  Error saving {rid}: {e}")
        return None

def extract_images(el, image_map):
    images = []
    for drawing in el.findall('.//' + wn('drawing')):
        for blip in drawing.findall('.//' + '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
            rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if rid and rid in rels and rid not in image_map:
                fname = save_image(rid, len(image_map) + 1)
                if fname:
                    image_map[rid] = fname
                    images.append(fname)
            elif rid and rid in image_map:
                images.append(image_map[rid])
    for pict in el.findall('.//' + wn('pict')):
        for img_data in pict.findall('.//' + '{urn:schemas-microsoft-com:vml}imagedata'):
            rid = img_data.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if rid and rid in rels and rid not in image_map:
                fname = save_image(rid, len(image_map) + 1)
                if fname:
                    image_map[rid] = fname
                    images.append(fname)
            elif rid and rid in image_map:
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
                imgs = extract_images(p, image_map)
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

# Phase 1: Find key section boundaries
main_content_start = None
review_start = None
for i, el in enumerate(ch2_elements):
    tag = el.tag.split('}')[-1]
    if tag != 'p': continue
    text = get_text(el)
    style = get_style(el)
    if text.strip() == '正文部分' and style == '4':
        main_content_start = i
    if text.strip() == '学员复习专用' and style == '4':
        review_start = i
        break

print(f"Main content starts at: {main_content_start}")
print(f"Review section starts at: {review_start}")

# Only process main content
main_elements = ch2_elements[main_content_start:review_start] if review_start else ch2_elements[main_content_start:]

# Phase 2: Extract content with skip logic
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

def is_skip_marker_text(text):
    """These markers start sections that should be entirely skipped"""
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

def is_scaffold_empty(text):
    """Empty scaffold markers with no real content"""
    patterns = ['📚 记忆技巧', '🎯 教练小Tips', '💡 关键思考', '💡 章节小节']
    for p in patterns:
        if text.strip() == p:
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
    
    # Check for skip markers (these start subsections to skip)
    if style in ['4', '5', '6'] and is_skip_marker_text(text):
        skip_subsection = True
        i += 1
        continue
    
    # Resume skip: check if we've hit a new content heading
    if skip_subsection:
        if style == '4' and re.match(r'^\d+\s', text):
            skip_subsection = False
        elif style == '3':
            skip_subsection = False
        elif style == '5' and re.match(r'^[\d一二三四五六七]+[\.、]', text):
            skip_subsection = False
        elif style == '5' and re.match(r'^[一二三四五六七八九十]+[、．.]', text):
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
    
    # Skip "✍️小节回顾" and everything after until next major section
    if '小节回顾' in text:
        skip_subsection = True
        i += 1
        continue
    
    # Skip 💡 章节小节
    if '💡 章节小节' in text:
        i += 1
        continue
    
    # Skip "互动考题" "记忆小本" sub-sections within 小节回顾
    if text.strip() in ['互动考题', '记忆小本', '基本原理']:
        i += 1
        continue
    
    # Empty paragraph
    if not text:
        imgs = extract_images(el, image_map)
        if imgs:
            content_blocks.append({'type': 'images_only', 'images': imgs})
        i += 1
        continue
    
    # Extract images from paragraph
    imgs = extract_images(el, image_map)
    
    # Build block
    block = {'type': 'text', 'text': text, 'style': style, 'images': imgs}
    
    existing_ids = [h[2] for h in headings]
    if style == '3':
        hid = make_id(text, existing_ids)
        block.update({'heading_level': 2, 'heading_id': hid})
        headings.append((2, text, hid))
    elif style == '4':
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

print(f"\nFinal stats:")
print(f"  Content blocks: {len(content_blocks)}")
print(f"  Tables: {table_count}")
print(f"  Images: {len(image_map)}")
print(f"  Headings: {len(headings)}")
h_counts = {}
for h in headings:
    h_counts[h[0]] = h_counts.get(h[0], 0) + 1
print(f"  Heading distribution: {h_counts}")

# Print all headings
print("\n--- All headings ---")
for level, text, hid in headings:
    print(f"  H{level}: {text}")

# Print first/last blocks
print("\n--- First 15 blocks ---")
for i, b in enumerate(content_blocks[:15]):
    if b['type'] == 'table':
        print(f"  [{i}] TABLE ({len(b['rows'])} rows)")
    elif b['type'] == 'images_only':
        print(f"  [{i}] IMAGES ({b['images']})")
    else:
        t = b.get('text', '')[:70]
        hl = b.get('heading_level', '-')
        imgs = len(b.get('images', []))
        print(f"  [{i}] H{hl} imgs={imgs} \"{t}\"")

print("\n--- Last 10 blocks ---")
for i, b in enumerate(content_blocks[-10:]):
    idx = len(content_blocks) - 10 + i
    if b['type'] == 'table':
        print(f"  [{idx}] TABLE ({len(b['rows'])} rows)")
    elif b['type'] == 'images_only':
        print(f"  [{idx}] IMAGES ({b['images']})")
    else:
        t = b.get('text', '')[:70]
        hl = b.get('heading_level', '-')
        imgs = len(b.get('images', []))
        print(f"  [{idx}] H{hl} imgs={imgs} \"{t}\"")

# Check for residual issues
residual_issues = []
for b in content_blocks:
    if b['type'] == 'text':
        t = b['text']
        if any(x in t for x in ['💡', '📚', '🎯']):
            residual_issues.append(t[:60])
        if '记忆技巧' in t and len(t) < 20:
            residual_issues.append(f"SHORT_MEM: {t}")
        if '教练小Tips' in t and len(t) < 20:
            residual_issues.append(f"SHORT_TIP: {t}")

if residual_issues:
    print(f"\n--- Residual issues ({len(residual_issues)}) ---")
    for r in residual_issues[:10]:
        print(f"  {r}")

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

print("\nDone. Data saved.")
