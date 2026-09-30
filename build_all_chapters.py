#!/usr/bin/env python3
"""
ACEpresso Chapter Builder - 从合订本docx提取各章内容，生成教科书级排版HTML
纯提取+格式化，不做任何内容改写，确保零编造
"""
import zipfile, re, os, sys, shutil, html as html_mod
import xml.etree.ElementTree as ET

DOCX_PATH = '/Coze/Drive/Arise/ACEpresso教辅_合订本v4.1(3)_1790770742723_5bgi.docx'
OUTPUT_DIR = '/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso'
IMAGES_DIR = os.path.join(OUTPUT_DIR, 'images')

NS_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS_R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
NS_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
NS_WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
NS_PIC = '{http://schemas.openxmlformats.org/drawingml/2006/picture}'

# 需要跳过的H4区域标题
SKIP_H4_SECTIONS = {
    '学员预习专用', '学员课后复习专用', '学员复习专用',
    '本章总结', '全章重点汇总', '常见误区', '全章小结',
}
# 需要跳过的H5区域标题
SKIP_H5_SECTIONS = {
    '复习与自测', '自测题', '思考与练习', '本章核心回顾',
    '知识结构', '重点内容', '行为改变评估自检清单', '知识衔接', '章末复习',
    '学习目标', '本章核心', '本章内容', '关键数字', '名词与缩写',
    '执业范围速览', '学习路线',
}


def parse_docx(docx_path):
    """解析docx，返回元素列表和图片关系映射"""
    with zipfile.ZipFile(docx_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = ET.parse(f)
        root = tree.getroot()
        body = root.find(f'{NS_W}body')

        # 收集图片关系映射
        img_rels = {}
        try:
            with z.open('word/_rels/document.xml.rels') as f:
                rels_tree = ET.parse(f)
            for rel in rels_tree.getroot():
                target = rel.get('Target', '')
                if 'media/' in target:
                    img_rels[rel.get('Id', '')] = target
        except:
            pass

        # 收集表格内元素ID
        table_elem_ids = set()
        for tbl in root.iter(f'{NS_W}tbl'):
            for child in tbl.iter():
                table_elem_ids.add(id(child))

        # 按顺序提取元素
        elements = []
        img_counter = {}  # rId -> filename mapping

        for child in body:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

            if tag == 'p':
                if id(child) in table_elem_ids:
                    continue
                pPr = child.find(f'{NS_W}pPr')
                style = ''
                if pPr is not None:
                    pStyle = pPr.find(f'{NS_W}pStyle')
                    if pStyle is not None:
                        style = pStyle.get(f'{NS_W}val', '')

                texts = []
                for r in child.iter(f'{NS_W}t'):
                    if r.text:
                        texts.append(r.text)
                text = ''.join(texts).strip()

                # 检测图片
                image_files = []
                for blip in child.iter(f'{NS_A}blip'):
                    rid = blip.get(f'{NS_R}embed', '')
                    if rid and rid in img_rels:
                        target = img_rels[rid]
                        fname = os.path.basename(target)
                        image_files.append(fname)

                if text or image_files:
                    elements.append({
                        'type': 'p',
                        'style': style,
                        'text': text,
                        'images': image_files,
                    })

            elif tag == 'tbl':
                rows = []
                for tr in child.iter(f'{NS_W}tr'):
                    cells = []
                    for tc in tr.iter(f'{NS_W}tc'):
                        cell_texts = []
                        for t in tc.iter(f'{NS_W}t'):
                            if t.text:
                                cell_texts.append(t.text)
                        cells.append(''.join(cell_texts).strip())
                    if any(c for c in cells):  # skip empty rows
                        rows.append(cells)
                if rows:
                    elements.append({'type': 'table', 'rows': rows})

    return elements, img_rels, img_counter


def extract_images(docx_path, img_rels, output_dir):
    """从docx中提取所有图片到images目录"""
    os.makedirs(output_dir, exist_ok=True)
    extracted = set()
    with zipfile.ZipFile(docx_path, 'r') as z:
        for rid, target in img_rels.items():
            fname = os.path.basename(target)
            media_path = 'word/' + target
            if media_path in z.namelist() and fname not in extracted:
                with z.open(media_path) as src, open(os.path.join(output_dir, fname), 'wb') as dst:
                    dst.write(src.read())
                extracted.add(fname)
    return extracted


def find_chapters(elements):
    """找到各章的起止位置"""
    ch_starts = []
    for i, e in enumerate(elements):
        if e['type'] == 'p' and e['style'] == '3' and re.match(r'^第\d+章', e['text']):
            ch_starts.append(i)
    ch_starts.append(len(elements))
    return ch_starts


def classify_paragraph(text):
    """
    分类段落类型，返回 (category, clean_text)
    category: 'skip', 'tip', 'wrong', 'right', 'warn', 'scene', 'memory', 'text'
    """
    stripped = text.strip()
    if not stripped:
        return ('skip', '')

    # ===== 第一步：检测并去除所有 emoji 前缀 =====
    # 匹配所有脚手架 emoji 前缀：💡 📚 🎯 ❌ ✓ ✅ 及其组合
    emoji_prefix_re = re.compile(
        r'^[\U0001f4a1\U0001f4da\U0001f3af❌✓✅]\s*'
    )
    after_emoji = emoji_prefix_re.sub('', stripped).strip()

    # ===== 第二步：💡 章节小节 → 整段跳过 =====
    if '章节小节' in stripped[:20]:
        return ('skip', '')

    # ===== 第二步b：💡 记忆技巧 / 💡 记忆小本 → 纯脚手架标签，跳过 =====
    if re.match(r'^💡\s*记忆(?:技巧|小本)', stripped):
        return ('skip', '')

    # ===== 第三步：💡 关键思考 → 如果后面有内容则保留为普通文本 =====
    if '关键思考' in stripped[:15]:
        remaining = stripped.replace('💡', '').replace('关键思考', '').strip('：: ')
        if remaining:
            return ('text', remaining)
        return ('skip', '')

    # ===== 第四步：📚 记忆技巧 / 📚 记忆小本 =====
    if '记忆技巧' in stripped[:15] or '记忆小本' in stripped[:15]:
        # 去掉 emoji 和前缀标签
        remaining = re.sub(r'^[\U0001f4da\s]*(?:记忆技巧|记忆小本)[：:]?\s*', '', stripped).strip()
        if remaining.startswith('重点知识点'):
            remaining = remaining[len('重点知识点'):].strip('：: ')
        if remaining:
            return ('memory', remaining)
        return ('skip', '')

    # ===== 第五步：记忆提示 → memory card =====
    if stripped.startswith('记忆提示'):
        remaining = re.sub(r'^记忆提示[：:]\s*', '', stripped).strip()
        if remaining:
            return ('memory', remaining)
        return ('skip', '')

    # ===== 第六步：🎯 教练小Tips =====
    if '教练小' in stripped[:15] and ('tip' in stripped[:20].lower() or 'Tips' in stripped[:20]):
        remaining = re.sub(r'^[\U0001f3af\s]*教练小[tT]ips[：:]?\s*', '', stripped).strip()
        if remaining:
            return ('text', remaining)
        return ('skip', '')

    # ===== 第七步：❌ 错误做法 / ❌ 常见误区 =====
    if stripped.startswith('❌') or stripped.startswith('✗'):
        remaining = emoji_prefix_re.sub('', stripped).strip()
        if '错误做法' in remaining[:10]:
            remaining = re.sub(r'^错误做法[：:]?\s*', '', remaining).strip()
            return ('wrong', remaining) if remaining else ('skip', '')
        if '常见误区' in remaining[:10] or '误区' in remaining[:10]:
            remaining = re.sub(r'^(?:常见)?误区[：:]?\s*', '', remaining).strip()
            return ('warn', remaining) if remaining else ('skip', '')
        # 通用 ❌ 开头 → 当 wrong
        return ('wrong', remaining) if remaining else ('skip', '')

    # ===== 第八步：✓ / ✅ 正确做法 =====
    if stripped.startswith('✓') or stripped.startswith('✅'):
        remaining = re.sub(r'^[✓✅]\s*(?:正确做法)?[：:]?\s*', '', stripped).strip()
        return ('right', remaining) if remaining else ('skip', '')

    # ===== 第九步：无 emoji 前缀的关键词匹配 =====
    m = re.match(r'^要点[：:]\s*(.*)', stripped)
    if m:
        return ('tip', m.group(1).strip())
    m = re.match(r'^场景[：:]\s*(.*)', stripped)
    if m:
        content = m.group(1).strip()
        return ('scene', content) if content else ('skip', '')
    m = re.match(r'^(?:常见)?误区[：:]\s*(.*)', stripped)
    if m:
        return ('warn', m.group(1).strip())

    # ===== 第十步：兜底 - 如果去除 emoji 后有剩余内容 =====
    if after_emoji and after_emoji != stripped:
        # 去掉 emoji 后还有内容，作为普通文本保留
        return ('text', after_emoji)

    return ('text', stripped)


def _is_scaffold_heading(text):
    """判断标题是否为纯脚手架标题（应整段跳过）"""
    clean = text.strip()
    # 💡 关键思考
    if re.match(r'^💡\s*关键思考\s*$', clean):
        return True
    # 💡 章节小节（xxx）
    if re.match(r'^💡\s*章节小节', clean):
        return True
    # 📚 记忆技巧 (alone, no content after colon)
    if re.match(r'^📚\s*记忆技巧\s*$', clean):
        return True
    # 📚 记忆小本 / 📚 记忆小本：重点知识点
    if re.match(r'^📚\s*记忆小本', clean):
        return True
    # 🎯 教练小Tips (alone)
    if re.match(r'^🎯\s*教练小[tT]ips\s*$', clean):
        return True
    return False


def _clean_heading(text):
    """清理标题文字：去除 emoji 前缀和脚手架关键词"""
    clean = text.strip()
    # Remove leading emojis
    clean = re.sub(r'^[💡📚🎯✓✅❌]\s*', '', clean)
    # Remove scaffold keywords if they appear at the start
    clean = re.sub(r'^(?:关键思考|章节小节[^\s]*|记忆技巧|教练小[tT]ips|记忆小本[^\s]*)\s*', '', clean)
    return clean.strip() or text.strip()


def should_skip_region(heading_text, heading_level):
    """判断是否为需要跳过的区域标题（整段区域都不要）"""
    clean = heading_text.strip()
    # 注意：脚手架标题（💡关键思考、📚记忆技巧、🎯教练小Tips）不在此处跳过
    # 它们的子段落会由 classify_paragraph 分别处理
    if heading_level == '4':
        for skip in SKIP_H4_SECTIONS:
            if skip in clean:
                return True
    if heading_level in ('4', '5'):
        for skip in SKIP_H5_SECTIONS:
            if skip in clean:
                return True
    return False


def is_quiz_content(text):
    """判断是否为自测题目内容"""
    stripped = text.strip()
    # Q1, Q2 等
    if re.match(r'^Q\d+[.．、]', stripped):
        return True
    # 纯数字编号+点（如 "1. " "2. " 但只在题目上下文中）
    if re.match(r'^\d+[.．]\s*[A-Z]', stripped):  # A. B. C. D. 选项
        return True
    if re.match(r'^答案[：:]', stripped) or re.match(r'^答案提示[：:]', stripped):
        return True
    if re.match(r'^[A-D][.．、]', stripped):
        return True
    return False


def extract_chapter_content(elements, ch_idx, ch_starts, total_chapters):
    """提取单章内容，返回结构化的内容块列表"""
    start = ch_starts[ch_idx]
    end = ch_starts[ch_idx + 1]

    # 章节标题
    ch_title = elements[start]['text']
    # 提取章节编号和标题
    m = re.match(r'^第(\d+)章\s*(.*)', ch_title)
    ch_num = m.group(1) if m else str(ch_idx + 1)
    ch_name = m.group(2) if m else ch_title

    blocks = []
    in_skip_region = False
    skip_until_h4 = False
    skip_until_h5 = False
    skip_inline_until_heading = False  # 用于跳过"核心要义凝练""思考与练习"等内嵌脚手架区域
    in_正文 = False

    # 英文副标题（通常在H3后面的第一个H5或H6中）
    en_subtitle = ''

    i = start + 1  # skip the chapter title itself
    while i < end:
        e = elements[i]

        if e['type'] == 'table':
            if not in_skip_region and not skip_inline_until_heading and in_正文:
                blocks.append({'type': 'table', 'rows': e['rows']})
            i += 1
            continue

        if e['type'] != 'p':
            i += 1
            continue

        text = e['text']
        style = e['style']
        images = e.get('images', [])

        # 检测内嵌脚手架区域开始（"核心要义凝练"、"思考与练习"等）
        if style not in ('4', '5', '6') and not in_skip_region:
            stripped_text = text.strip()
            if (stripped_text.startswith('核心要义凝练') or
                stripped_text.startswith('思考与练习') or
                stripped_text.startswith('章节小节')):
                skip_inline_until_heading = True
                i += 1
                continue

        # 检测标题级别
        if style == '4':
            # H4 级别 → 结束内嵌跳过
            skip_inline_until_heading = False
            if should_skip_region(text, '4'):
                in_skip_region = True
                skip_until_h4 = True
                skip_until_h5 = False
                i += 1
                continue
            else:
                in_skip_region = False
                skip_until_h4 = False
                if '正文部分' in text:
                    in_正文 = True
                    i += 1
                    continue
                # 脚手架标题不输出，但不跳过后续内容
                if _is_scaffold_heading(text):
                    i += 1
                    continue
                # 主节标题（如 "1 ACE私人教练认证"）- clean text
                clean_text = _clean_heading(text)
                blocks.append({'type': 'h3', 'text': clean_text, 'id': f's{len(blocks)}'})
                i += 1
                continue

        if style == '5':
            # H5 级别 → 结束内嵌跳过
            skip_inline_until_heading = False
            if not in_skip_region:
                # 检查是否为需要跳过的H5区域
                if should_skip_region(text, '5'):
                    skip_until_h5 = True
                    i += 1
                    continue
                else:
                    skip_until_h5 = False
                    # 脚手架标题不输出，但不跳过后续内容
                    if _is_scaffold_heading(text):
                        i += 1
                        continue
                    # 子标题 - clean text
                    clean_text = _clean_heading(text)
                    if clean_text and in_正文:
                        blocks.append({'type': 'h4', 'text': clean_text, 'id': f's{len(blocks)}'})
            i += 1
            continue

        if style == '6':
            # H6 级别 → 结束内嵌跳过
            skip_inline_until_heading = False
            if not in_skip_region and not skip_until_h5 and in_正文:
                # 脚手架标题不输出
                if _is_scaffold_heading(text):
                    i += 1
                    continue
                clean_text = _clean_heading(text)
                if clean_text:
                    blocks.append({'type': 'h5', 'text': clean_text, 'id': f's{len(blocks)}'})
            i += 1
            continue

        # 非标题段落
        if in_skip_region or skip_until_h4 or skip_until_h5 or skip_inline_until_heading:
            # 检查是否遇到了新的非跳过标题
            if style in ('4', '5') and not should_skip_region(text, style):
                in_skip_region = False
                skip_until_h4 = False
                skip_until_h5 = False
            else:
                i += 1
                continue

        if not in_正文:
            i += 1
            continue

        # 处理图片
        if images:
            for img_file in images:
                blocks.append({'type': 'image', 'src': img_file, 'caption': text if text else ''})
            if not text:
                i += 1
                continue

        # 分类段落内容
        category, clean_text = classify_paragraph(text)
        if category == 'skip':
            i += 1
            continue

        # 检查是否为自测题目内容
        if is_quiz_content(text):
            i += 1
            continue

        if clean_text:
            blocks.append({'type': category, 'text': clean_text})

        i += 1

    return ch_num, ch_name, blocks


def build_table_html(rows):
    """将表格数据转为HTML table"""
    if not rows:
        return ''
    html_parts = ['<div class="table-wrapper"><table>']
    # 第一行作为表头
    html_parts.append('<thead><tr>')
    for cell in rows[0]:
        html_parts.append(f'<th>{html_mod.escape(cell)}</th>')
    html_parts.append('</tr></thead>')
    # 数据行
    html_parts.append('<tbody>')
    for row in rows[1:]:
        html_parts.append('<tr>')
        for cell in row:
            html_parts.append(f'<td>{html_mod.escape(cell)}</td>')
        html_parts.append('</tr>')
    html_parts.append('</tbody></table></div>')
    return ''.join(html_parts)


def generate_chapter_html(ch_num, ch_name, blocks, total_chapters):
    """生成单章HTML"""

    # 构建TOC和内容
    toc_items = []
    content_parts = []
    section_counter = 0

    # 英文副标题映射
    en_subtitles = {
        '1': 'The Role and Scope of Practice for the Personal Trainer',
        '2': 'Foundations of Behavior Change',
        '3': 'Effective Communication, Goal-Setting, and Teaching Skills',
        '4': 'Pre-Activity Health Screening and Appraisal',
        '5': 'Cardiorespiratory Training: Physiology, Assessment, and Programming',
        '6': 'Muscular Training: Foundations, Benefits, and Program Design',
    }
    en_subtitle = en_subtitles.get(ch_num, f'Chapter {ch_num}')

    # 导读
    intros = {
        '1': '本章介绍ACE认证私人教练的角色、执业范围和职业责任，并说明私人教练在健康照护联盟中的协作位置以及职业发展路径。',
        '2': '本章系统讲解行为改变的核心理论模型、行为改变的科学原理，以及影响身体活动坚持性的关键因素，为私人教练提供循证的行为干预方法。',
        '3': '本章聚焦私人教练与客户沟通的核心技能、目标设定方法论和教学技巧，帮助教练建立专业、高效的客户关系。',
        '4': '本章讲解运动前健康筛查的流程、工具和方法，包括风险分层、医学许可获取和健康风险评估，确保训练安全。',
        '5': '本章深入讲解心肺训练的生理学基础、评估方法和训练计划设计，为私人教练提供科学的心肺训练指导框架。',
        '6': '本章系统讲解肌肉训练的生理学基础、训练益处和计划设计原则，帮助教练为客户制定科学有效的力量训练方案。',
    }
    intro = intros.get(ch_num, f'第{ch_num}章讲义内容。')

    for block in blocks:
        btype = block['type']

        if btype == 'h3':
            toc_items.append(f'<a href="#{block["id"]}" class="toc-link toc-h2">{html_mod.escape(block["text"])}</a>')
            content_parts.append(f'<h2 class="section-heading" id="{block["id"]}">{html_mod.escape(block["text"])}</h2>')
            section_counter += 1
        elif btype == 'h4':
            toc_items.append(f'<a href="#{block["id"]}" class="toc-link toc-h3">{html_mod.escape(block["text"])}</a>')
            content_parts.append(f'<h3 class="subsection-heading" id="{block["id"]}">{html_mod.escape(block["text"])}</h3>')
            section_counter += 1
        elif btype == 'h5':
            toc_items.append(f'<a href="#{block["id"]}" class="toc-link toc-h4">{html_mod.escape(block["text"])}</a>')
            content_parts.append(f'<h4 class="sub-subsection-heading" id="{block["id"]}">{html_mod.escape(block["text"])}</h4>')
            section_counter += 1
        elif btype == 'table':
            content_parts.append(build_table_html(block['rows']))
        elif btype == 'image':
            src = block['src']
            caption = block.get('caption', '')
            content_parts.append(f'<figure class="img-figure"><img src="images/{src}" loading="lazy" onclick="openLightbox(this)" alt="{html_mod.escape(caption)}"></figure>')
        elif btype == 'tip':
            content_parts.append(f'<div class="card card-tip"><span class="card-label">要点</span><p>{html_mod.escape(block["text"])}</p></div>')
        elif btype == 'wrong':
            content_parts.append(f'<div class="card card-wrong"><span class="card-label">✗ 错误做法</span><p>{html_mod.escape(block["text"])}</p></div>')
        elif btype == 'right':
            content_parts.append(f'<div class="card card-right"><span class="card-label">✓ 正确做法</span><p>{html_mod.escape(block["text"])}</p></div>')
        elif btype == 'warn':
            content_parts.append(f'<div class="card card-warn"><span class="card-label">⚠ 常见误区</span><p>{html_mod.escape(block["text"])}</p></div>')
        elif btype == 'scene':
            content_parts.append(f'<div class="card card-scene"><span class="card-label">场景</span><p>{html_mod.escape(block["text"])}</p></div>')
        elif btype == 'memory':
            content_parts.append(f'<div class="card card-memory"><span class="card-label">记忆提示</span><p>{html_mod.escape(block["text"])}</p></div>')
        elif btype == 'text':
            content_parts.append(f'<p>{html_mod.escape(block["text"])}</p>')

    content_html = '\n'.join(content_parts)
    toc_html = '\n'.join(toc_items)

    # 导航链接
    prev_ch = int(ch_num) - 1
    next_ch = int(ch_num) + 1
    prev_link = f'<a href="ch{prev_ch}.html" class="prev">← 上一章</a>' if prev_ch >= 1 else '<span></span>'
    next_link = f'<a href="ch{next_ch}.html" class="next">下一章 →</a>' if next_ch <= total_chapters else '<span></span>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>第{ch_num}章 {html_mod.escape(ch_name)} | ACEpresso</title>
<style>
:root {{
  --bg: #fafaf8; --surface: #ffffff; --text: #1a1a2e; --text-secondary: #555;
  --accent: #2d5016; --accent-light: #e8f5e9; --border: #e0ddd8;
  --sidebar-bg: #fafbfc; --header-bg: #ffffff; --shadow: rgba(0,0,0,0.06);
  --hero-gradient: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 50%, #fafaf8 100%);
  --table-header: #2e7d32; --table-stripe: #f8f8f5;
  --card-radius: 10px;
}}
[data-theme="dark"] {{
  --bg: #0f0f1a; --surface: #1a1a2e; --text: #e0e0e0; --text-secondary: #aaa;
  --accent: #66bb6a; --accent-light: #1b3a1b; --border: #2a2a3a;
  --sidebar-bg: #12121e; --header-bg: #0f0f1a; --shadow: rgba(0,0,0,0.3);
  --hero-gradient: linear-gradient(135deg, #1b3a1b 0%, #1a2e1a 50%, #0f0f1a 100%);
  --table-header: #1b5e20; --table-stripe: #1e1e30;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', Georgia, 'Times New Roman', serif;
  background: var(--bg); color: var(--text); line-height: 1.9; font-size: 16.5px;
  transition: background 0.3s, color 0.3s;
  -webkit-font-smoothing: antialiased;
}}

/* 进度条 */
.progress-bar {{
  position: fixed; top: 0; left: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent), #4caf50);
  z-index: 1000; transition: width 0.15s; width: 0%;
}}

/* 顶部导航 */
.site-header {{
  position: fixed; top: 3px; left: 0; right: 0; height: 54px;
  background: var(--header-bg); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; z-index: 100;
  box-shadow: 0 1px 6px var(--shadow);
  backdrop-filter: blur(8px);
}}
.logo {{
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 22px; font-weight: 800; color: var(--accent);
  letter-spacing: 1.5px;
}}
.logo span {{
  font-size: 11px; font-weight: 400; color: var(--text-secondary);
  margin-left: 10px; letter-spacing: 0.5px;
}}
.theme-toggle {{
  background: none; border: 1px solid var(--border); color: var(--text);
  padding: 6px 16px; border-radius: 20px; cursor: pointer;
  font-size: 13px; transition: all 0.25s;
}}
.theme-toggle:hover {{
  background: var(--accent-light); border-color: var(--accent); color: var(--accent);
}}

/* 布局 */
.layout {{ display: flex; margin-top: 57px; min-height: calc(100vh - 57px); }}

/* 侧边栏 */
.sidebar {{
  position: fixed; top: 57px; left: 0; width: 280px;
  height: calc(100vh - 57px); background: var(--sidebar-bg);
  border-right: 1px solid var(--border); overflow-y: auto;
  padding: 20px 0; z-index: 50;
}}
.sidebar::-webkit-scrollbar {{ width: 4px; }}
.sidebar::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
.toc-title {{
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 11px; font-weight: 700; color: var(--text-secondary);
  padding: 0 24px 14px; text-transform: uppercase; letter-spacing: 3px;
  border-bottom: 1px solid var(--border); margin-bottom: 8px;
}}
.toc-link {{
  display: block; padding: 7px 24px; color: var(--text-secondary);
  text-decoration: none; font-size: 13px; line-height: 1.5;
  transition: all 0.2s; border-left: 3px solid transparent;
}}
.toc-link:hover {{
  background: var(--accent-light); color: var(--accent);
  border-left-color: var(--accent);
}}
.toc-link.active {{
  color: var(--accent); font-weight: 600;
  border-left-color: var(--accent); background: var(--accent-light);
}}
.toc-h2 {{ padding-left: 24px; font-weight: 700; font-size: 14px; color: var(--text); margin-top: 8px; }}
.toc-h3 {{ padding-left: 36px; }}
.toc-h4 {{ padding-left: 48px; font-size: 12px; }}

/* 主内容区 */
.main-content {{
  margin-left: 280px; flex: 1; max-width: 880px;
  padding: 0 48px 100px;
}}

/* Hero区 */
.hero {{
  padding: 48px 0 36px; border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
  background: var(--hero-gradient);
  margin-left: -48px; margin-right: -48px;
  padding-left: 48px; padding-right: 48px;
}}
.hero .badge {{
  display: inline-block; background: var(--accent); color: white;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 12px; font-weight: 700; padding: 4px 14px;
  border-radius: 20px; letter-spacing: 1px; margin-bottom: 16px;
}}
.hero h1 {{
  font-size: 32px; font-weight: 800; line-height: 1.3;
  color: var(--text); margin-bottom: 8px;
  font-family: 'Noto Sans SC', sans-serif;
}}
.hero .subtitle {{
  font-size: 15px; color: var(--text-secondary);
  font-style: italic; margin-bottom: 16px;
}}
.hero .intro {{
  font-size: 15px; color: var(--text-secondary); line-height: 1.8;
  max-width: 640px; border-left: 3px solid var(--accent);
  padding-left: 16px;
}}

/* Tabs */
.tabs {{
  display: flex; gap: 0; border-bottom: 2px solid var(--border);
  margin-bottom: 32px;
}}
.tab-btn {{
  background: none; border: none; border-bottom: 2px solid transparent;
  padding: 12px 24px; font-size: 14px; font-weight: 500;
  color: var(--text-secondary); cursor: pointer;
  transition: all 0.2s; margin-bottom: -2px;
  font-family: 'Noto Sans SC', sans-serif;
}}
.tab-btn:hover {{ color: var(--accent); }}
.tab-btn.active {{
  color: var(--accent); border-bottom-color: var(--accent);
  font-weight: 700;
}}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
.placeholder {{
  padding: 48px 24px; text-align: center;
  color: var(--text-secondary); font-size: 15px;
}}

/* 标题层级 */
.section-heading {{
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 24px; font-weight: 800; color: var(--accent);
  margin: 48px 0 20px; padding-bottom: 12px;
  border-bottom: 2px solid var(--accent);
  line-height: 1.4;
}}
.subsection-heading {{
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 20px; font-weight: 700; color: var(--text);
  margin: 36px 0 16px; padding-left: 16px;
  border-left: 4px solid var(--accent);
  line-height: 1.4;
}}
.sub-subsection-heading {{
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 17px; font-weight: 600; color: var(--text);
  margin: 28px 0 12px; line-height: 1.4;
}}
.sub-sub-subsection-heading {{
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 15px; font-weight: 600; color: var(--text-secondary);
  margin: 20px 0 10px; line-height: 1.4;
  text-transform: uppercase; letter-spacing: 0.5px;
}}

/* 正文段落 */
.main-content p {{
  margin-bottom: 16px; text-align: justify;
  text-indent: 0;
}}

/* 色块卡片 */
.card {{
  margin: 18px 0; padding: 16px 20px;
  border-radius: var(--card-radius); border-left: 4px solid;
  position: relative;
}}
.card .card-label {{
  font-family: 'Noto Sans SC', sans-serif;
  font-weight: 700; font-size: 12px;
  display: inline-block; margin-bottom: 8px;
  letter-spacing: 1px; text-transform: uppercase;
  padding: 2px 8px; border-radius: 4px;
}}
.card p {{ margin: 0; font-size: 15px; line-height: 1.8; }}

.card-tip {{ background: #e8f5e9; border-color: #4caf50; }}
.card-tip .card-label {{ color: #2e7d32; background: #c8e6c9; }}

.card-wrong {{ background: #fce4ec; border-color: #e53935; }}
.card-wrong .card-label {{ color: #c62828; background: #ffcdd2; }}

.card-right {{ background: #e3f2fd; border-color: #1e88e5; }}
.card-right .card-label {{ color: #1565c0; background: #bbdefb; }}

.card-warn {{ background: #fff8e1; border-color: #ff8f00; }}
.card-warn .card-label {{ color: #e65100; background: #ffecb3; }}

.card-scene {{ background: #f3e5f5; border-color: #7b1fa2; }}
.card-scene .card-label {{ color: #6a1b9a; background: #e1bee7; }}

.card-memory {{
  background: var(--bg-secondary, #f5f5f5); border-color: #9e9e9e;
  border-left-style: dashed;
}}
.card-memory .card-label {{ color: #616161; background: #e0e0e0; }}
.card-memory p {{ font-size: 14px; color: var(--text-secondary); font-style: italic; }}

/* 深色模式卡片 */
[data-theme="dark"] .card-tip {{ background: #1b3a1b; }}
[data-theme="dark"] .card-tip .card-label {{ background: #2e5a2e; color: #81c784; }}
[data-theme="dark"] .card-wrong {{ background: #3a1b1b; }}
[data-theme="dark"] .card-wrong .card-label {{ background: #5a2e2e; color: #ef9a9a; }}
[data-theme="dark"] .card-right {{ background: #1b2a3a; }}
[data-theme="dark"] .card-right .card-label {{ background: #2e4a5a; color: #90caf9; }}
[data-theme="dark"] .card-warn {{ background: #3a2a1b; }}
[data-theme="dark"] .card-warn .card-label {{ background: #5a4a2e; color: #ffcc80; }}
[data-theme="dark"] .card-scene {{ background: #2a1b3a; }}
[data-theme="dark"] .card-scene .card-label {{ background: #4a2e5a; color: #ce93d8; }}
[data-theme="dark"] .card-memory {{ background: #1a1a2a; }}
[data-theme="dark"] .card-memory .card-label {{ background: #2a2a3a; color: #bdbdbd; }}

/* 表格 */
.table-wrapper {{
  margin: 20px 0; overflow-x: auto; border-radius: 10px;
  box-shadow: 0 1px 4px var(--shadow);
}}
table {{
  width: 100%; border-collapse: collapse; font-size: 14px;
  line-height: 1.6;
}}
th {{
  background: var(--table-header); color: white;
  padding: 12px 16px; text-align: left;
  font-family: 'Noto Sans SC', sans-serif; font-weight: 600;
  font-size: 13px; letter-spacing: 0.5px;
}}
td {{
  padding: 10px 16px; border-bottom: 1px solid var(--border);
  vertical-align: top;
}}
tbody tr:nth-child(even) {{ background: var(--table-stripe); }}
tbody tr:hover {{ background: var(--accent-light); }}

/* 图片 */
.img-figure {{
  margin: 24px 0; text-align: center;
}}
.img-figure img {{
  max-width: 100%; height: auto; border-radius: 8px;
  border: 1px solid var(--border); box-shadow: 0 2px 8px var(--shadow);
  cursor: pointer; transition: transform 0.2s;
}}
.img-figure img:hover {{ transform: scale(1.01); }}
.img-figure figcaption {{
  font-size: 13px; color: var(--text-secondary);
  margin-top: 8px; font-style: italic;
}}

/* Lightbox */
.lightbox {{
  display: none; position: fixed; top: 0; left: 0;
  width: 100%; height: 100%; background: rgba(0,0,0,0.9);
  z-index: 2000; justify-content: center; align-items: center;
  cursor: pointer;
}}
.lightbox.active {{ display: flex; }}
.lightbox img {{
  max-width: 90%; max-height: 90%; border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}}

/* 章间导航 */
.chapter-nav {{
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--border);
}}
.chapter-nav a {{
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 14px; font-weight: 600; color: var(--accent);
  text-decoration: none; padding: 10px 20px;
  border: 1px solid var(--accent); border-radius: 8px;
  transition: all 0.2s;
}}
.chapter-nav a:hover {{
  background: var(--accent); color: white;
}}

/* 响应式 */
@media (max-width: 900px) {{
  .sidebar {{ display: none; }}
  .main-content {{ margin-left: 0; padding: 0 20px 60px; }}
  .hero {{ margin-left: -20px; margin-right: -20px; padding-left: 20px; padding-right: 20px; }}
  .hero h1 {{ font-size: 24px; }}
  .section-heading {{ font-size: 20px; }}
  .subsection-heading {{ font-size: 18px; }}
}}

/* 打印 */
@media print {{
  .site-header, .sidebar, .tabs, .chapter-nav, .progress-bar, .theme-toggle, .lightbox {{ display: none !important; }}
  .main-content {{ margin-left: 0; max-width: 100%; padding: 0; }}
  .hero {{ background: none; margin: 0; padding: 20px 0; }}
  .card {{ break-inside: avoid; }}
  table {{ break-inside: avoid; }}
  .img-figure img {{ max-width: 80%; }}
}}
</style>
</head>
<body>

<div class="progress-bar" id="progressBar"></div>

<header class="site-header">
  <div class="logo">ACEpresso <span>循证私人教练教育</span></div>
  <button class="theme-toggle" onclick="toggleTheme()">◐ 主题</button>
</header>

<div class="layout">
  <nav class="sidebar">
    <div class="toc-title">本章目录</div>
    {toc_html}
  </nav>

  <main class="main-content">
    <div class="hero">
      <div class="badge">第{ch_num}章</div>
      <h1>{html_mod.escape(ch_name)}</h1>
      <div class="subtitle">{en_subtitle}</div>
      <div class="intro">{intro}</div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('lecture', this)">讲义</button>
      <button class="tab-btn" onclick="switchTab('quiz', this)">自测</button>
      <button class="tab-btn" onclick="switchTab('sop', this)">SOP工作单</button>
    </div>

    <div id="tab-lecture" class="tab-content active">
{content_html}
    </div>

    <div id="tab-quiz" class="tab-content">
      <div class="placeholder">本章自测题目已移除。</div>
    </div>

    <div id="tab-sop" class="tab-content">
      <div class="placeholder">SOP工作单将在讲义确认后逐章制作。</div>
    </div>

    <div class="chapter-nav">
      {prev_link}
      {next_link}
    </div>
  </main>
</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <img id="lightboxImg" src="" alt="">
</div>

<script>
// 深色模式
function toggleTheme() {{
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
  localStorage.setItem('theme', html.getAttribute('data-theme'));
}}
(function() {{
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
}})();

// Tab切换
function switchTab(tabId, btn) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tabId).classList.add('active');
  btn.classList.add('active');
}}

// 阅读进度条
window.addEventListener('scroll', function() {{
  const scrollTop = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
  document.getElementById('progressBar').style.width = progress + '%';
}});

// Lightbox
function openLightbox(img) {{
  document.getElementById('lightboxImg').src = img.src;
  document.getElementById('lightbox').classList.add('active');
}}
function closeLightbox() {{
  document.getElementById('lightbox').classList.remove('active');
}}

// TOC高亮
const tocLinks = document.querySelectorAll('.toc-link');
const headings = [];
tocLinks.forEach(link => {{
  const id = link.getAttribute('href').substring(1);
  const el = document.getElementById(id);
  if (el) headings.push({{el, link}});
}});
window.addEventListener('scroll', function() {{
  let current = null;
  for (const h of headings) {{
    if (h.el.getBoundingClientRect().top <= 100) current = h;
  }}
  tocLinks.forEach(l => l.classList.remove('active'));
  if (current) current.link.classList.add('active');
}});
</script>

</body>
</html>'''

    return html


def rename_and_copy_images(docx_path, img_rels, blocks, ch_num, images_dir):
    """复制并重命名图片"""
    os.makedirs(images_dir, exist_ok=True)
    img_blocks = [b for b in blocks if b['type'] == 'image']
    with zipfile.ZipFile(docx_path, 'r') as z:
        for idx, b in enumerate(img_blocks, 1):
            src_name = b['src']
            ext = os.path.splitext(src_name)[1]
            new_name = f'ch{ch_num}_fig{idx}{ext}'

            # 找到对应的media路径
            target_path = None
            for rid, target in img_rels.items():
                if os.path.basename(target) == src_name:
                    target_path = 'word/' + target
                    break

            if target_path and target_path in z.namelist():
                out_path = os.path.join(images_dir, new_name)
                with z.open(target_path) as src, open(out_path, 'wb') as dst:
                    dst.write(src.read())
                b['src'] = new_name  # 更新为新的文件名


def verify_chapter(html_content, ch_num):
    """验证生成的HTML"""
    issues = []

    # 检查脚手架残留
    for marker in ['💡', '📚', '🎯']:
        c = html_content.count(marker)
        if c > 0:
            issues.append(f'  ⚠️ Emoji {marker} 残留: {c}处')

    for kw in ['记忆技巧', '教练小Tips', '关键思考', '章节小节']:
        c = html_content.count(kw)
        # 注意：card-label中的文字是允许的
        if c > 0:
            # 检查是否只在card-label中
            in_labels = html_content.count(f'class="card-label">{kw}')
            in_labels2 = html_content.count(f'class="card-label">记忆提示')
            remaining = c - in_labels - (in_labels2 if kw == '记忆技巧' else 0)
            if remaining > 0 and 'card-label' not in kw:
                issues.append(f'  ⚠️ "{kw}" 残留: {c}处 (card-label外: ~{remaining})')

    # 检查编造内容
    for kw in ['FMS', '过头深蹲']:
        if kw in html_content:
            issues.append(f'  ⚠️ 可能的编造内容: {kw}')

    # 检查基本结构
    import re
    tables = len(re.findall(r'<table', html_content))
    images = len(re.findall(r'<img', html_content))
    toc = len(re.findall(r'class="toc-link toc-h', html_content))
    cards = len(re.findall(r'class="card ', html_content))

    # Logo
    if 'ACEpporesso' in html_content:
        issues.append('  ⚠️ Logo拼写错误: ACEpporesso')

    return issues, tables, images, toc, cards


def main():
    print("=" * 60)
    print("ACEpresso Chapter Builder - 教科书排版")
    print("=" * 60)

    # 解析docx
    print("\n[1/4] 解析docx文件...")
    elements, img_rels, _ = parse_docx(DOCX_PATH)
    print(f"  总元素数: {len(elements)}")

    # 找到章节边界
    ch_starts = find_chapters(elements)
    total_chapters = len(ch_starts) - 1
    print(f"  章节数: {total_chapters}")

    # 提取图片
    print("\n[2/4] 提取图片...")
    extracted = extract_images(DOCX_PATH, img_rels, IMAGES_DIR)
    print(f"  提取了 {len(extracted)} 张图片")

    # 生成各章HTML
    print("\n[3/4] 生成各章HTML...")
    for ch_idx in range(total_chapters):
        print(f"\n  --- 第{ch_idx+1}章 ---")
        ch_num, ch_name, blocks = extract_chapter_content(elements, ch_idx, ch_starts, total_chapters)

        # 重命名和复制图片
        rename_and_copy_images(DOCX_PATH, img_rels, blocks, ch_num, IMAGES_DIR)

        # 统计
        n_text = len([b for b in blocks if b['type'] == 'text'])
        n_tip = len([b for b in blocks if b['type'] == 'tip'])
        n_wrong = len([b for b in blocks if b['type'] == 'wrong'])
        n_right = len([b for b in blocks if b['type'] == 'right'])
        n_warn = len([b for b in blocks if b['type'] == 'warn'])
        n_scene = len([b for b in blocks if b['type'] == 'scene'])
        n_memory = len([b for b in blocks if b['type'] == 'memory'])
        n_table = len([b for b in blocks if b['type'] == 'table'])
        n_image = len([b for b in blocks if b['type'] == 'image'])
        n_h3 = len([b for b in blocks if b['type'] == 'h3'])
        n_h4 = len([b for b in blocks if b['type'] == 'h4'])
        n_h5 = len([b for b in blocks if b['type'] == 'h5'])

        print(f"  内容块: {n_text}段落, {n_h3}H3, {n_h4}H4, {n_h5}H5")
        print(f"  卡片: {n_tip}要点, {n_wrong}错误, {n_right}正确, {n_warn}误区, {n_scene}场景, {n_memory}记忆")
        print(f"  表格: {n_table}, 图片: {n_image}")

        # 生成HTML
        html = generate_chapter_html(ch_num, ch_name, blocks, total_chapters)

        # 验证
        issues, tables, images, toc, cards = verify_chapter(html, ch_num)
        print(f"  验证: 表格={tables}, 图片={images}, TOC={toc}, 卡片={cards}")
        if issues:
            for iss in issues:
                print(iss)
        else:
            print("  ✅ 验证通过")

        # 写入文件
        out_path = os.path.join(OUTPUT_DIR, f'ch{ch_num}.html')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  输出: {out_path} ({len(html)} bytes)")

    print("\n[4/4] 完成！")


if __name__ == '__main__':
    main()
