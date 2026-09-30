#!/usr/bin/env python3
"""ACEpresso Chapter Builder v3 - faithful to original docx"""
import zipfile, xml.etree.ElementTree as ET, re, os, sys, html as html_mod, glob
def extract_docx(filepath):
    with zipfile.ZipFile(filepath) as z:
        with z.open('word/document.xml') as f:
            tree = ET.parse(f); root = tree.getroot()
        elements = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'p':
                ps = elem.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
                style = ps.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val','') if ps is not None else ''
                texts = [t.text for t in elem.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text]
                text = ''.join(texts).strip()
                if text: elements.append({'type':'p','style':style,'text':text})
            elif tag == 'tbl':
                rows = []
                for tr in elem.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                    cells = []
                    for tc in tr.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                        ct = [t.text for t in tc.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text]
                        cells.append(''.join(ct).strip())
                    rows.append(cells)
                if rows: elements.append({'type':'tbl','rows':rows})
            elif tag in ('drawing','pict'):
                blips = list(elem.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip'))
                if blips:
                    rid = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed','')
                    if rid: elements.append({'type':'img','rid':rid})
        try:
            with z.open('word/_rels/document.xml.rels') as f:
                rt = ET.parse(f); img_map = {}
                for rel in rt.getroot():
                    rid = rel.get('Id',''); target = rel.get('Target','')
                    if target and any(ext in target for ext in ('png','jpg','jpeg','gif')): img_map[rid] = os.path.basename(target)
        except: img_map = {}
        for e in elements:
            if e['type']=='img': e['file'] = img_map.get(e.get('rid',''),'')
        return elements
MARKERS_RAW = [
    '记忆技巧',
    '📚记忆技巧',
    '📚 记忆技巧',
    '【记忆技巧】',
    '💡 记忆技巧',
    '🎯教练小Tips',
    '🎯 教练小Tips',
    '教练小Tips',
    '💡关键思考',
    '💡 关键思考',
]
MARKERS = set(MARKERS_RAW)
SCAFFOLD_PREFIXES = ['记忆提示：','理解类比：','理解要点：','补充理解：','补充：','一句话记牢：','口诀：','场景：','❌ 错误做法','❌错误做法','✓ 正确做法','✅ 正确做法','常见误区','PAR-Q+使用提醒：','记忆技巧：','教练小Tips：','关键思考：',' 记忆技巧：',' 教练小Tips：',' 关键思考：']
def is_marker(text):
    t = text.strip()
    if t in MARKERS: return True
    # Handle colon variants: "记忆技巧：" "教练小Tips：" "关键思考："
    for keyword in ['记忆技巧', '教练小Tips', '关键思考']:
        if t == keyword + '：' or t == keyword + ':': return True
        if t.endswith(keyword) and len(t) <= len(keyword) + 4: return True
    return False

def find_inline_marker(text):
    """Find scaffold keyword position in text for inline splitting."""
    t = text.strip()
    for keyword in ['记忆技巧', '教练小Tips', '关键思考']:
        idx = t.find(keyword)
        if idx >= 0:
            after_kw = t[idx+len(keyword):]
            # Marker if: end of string, or followed by colon/newline/whitespace
            if not after_kw or after_kw[0] in ('：', ':', ' ', '\t', '\n', '●', '•'):
                return idx, keyword
            # Also if keyword is at the very end (nothing after)
            if idx + len(keyword) >= len(t) - 1:
                return idx, keyword
    return -1, None

def is_scaffold_content(text):
    t = text.strip()
    for p in SCAFFOLD_PREFIXES:
        if t.startswith(p): return True
        if t.startswith(p.rstrip('：') + '：'): return True
        core = p.strip('：').strip()
        if t.startswith('• '+core) or t.startswith('● '+core): return True
    # Handle emoji-prefixed scaffold: strip leading emoji+spaces then check
    import re as _re
    t2 = _re.sub(r'^[🌀-🫿☀-⟿​ \s]+', '', t)
    for p in SCAFFOLD_PREFIXES:
        if t2.startswith(p): return True
        core = p.strip('：').strip()
        if t2.startswith(core): return True
    return False
def strip_prefix(text):
    t = text.strip()
    for p in SCAFFOLD_PREFIXES:
        if t.startswith(p):
            cleaned = t[len(p):].strip()
            if '错误做法' in p or '❌' in p:
                if not cleaned.startswith('❌'): cleaned = '❌ '+cleaned
            elif '正确做法' in p and not cleaned.startswith(('✓','✅')): cleaned = '✓ '+cleaned
            return cleaned
    return t
QUIZ_Q_PATTERNS = ['开放思考题：','选择题：','思考题：','● 开放思考题：','● 选择题：','● 思考题：',' 思考题']
def is_quiz_question(text):
    t = text.strip()
    for p in QUIZ_Q_PATTERNS:
        if t.startswith(p) or t==p.strip(): return True
    return t.startswith('参考答案')
def is_answer_choice(text):
    t = text.strip()
    return bool(re.match(r'^[A-D][\.\、\)]\s', t) or re.match(r'^[•●\s]*[A-D][\.\、\)]\s', t))
def process_chapter(elements):
    quiz_indices = set()
    collecting = False; non_quiz_run = 0
    for i, e in enumerate(elements):
        if e['type'] != 'p': continue
        text = e['text'].strip()
        if text in ('思考与练习', '预习思考与练习'):
            collecting = True; non_quiz_run = 0; quiz_indices.add(i); continue
        if collecting:
            if is_quiz_question(text) or is_answer_choice(text): quiz_indices.add(i); non_quiz_run = 0
            else:
                non_quiz_run += 1
                if non_quiz_run >= 2: collecting = False
    found_header = False
    for i, e in enumerate(elements):
        if e['type'] != 'p': continue
        if e['text'].strip() in ('思考与练习','预习思考与练习'): found_header = True; break
        if not found_header and i not in quiz_indices and is_quiz_question(e['text']):
            quiz_indices.add(i)
            for j in range(i+1, min(i+10, len(elements))):
                if elements[j]['type']=='p' and is_answer_choice(elements[j]['text']): quiz_indices.add(j)
                else: break
    lecture_parts = []; quiz_items = []; toc_headings = []; img_files = []
    for i, e in enumerate(elements):
        if e['type']=='p' and i in quiz_indices: quiz_items.append(e['text']); continue
        if e['type']=='tbl':
            t = '<table class="content-table">\n'
            for ri, row in enumerate(e['rows']):
                t += '<tr>'
                for ci, cell in enumerate(row):
                    tag = 'th' if ri==0 else 'td'
                    t += '<'+tag+'>'+html_mod.escape(cell)+'</'+tag+'>'
                t += '</tr>\n'
            t += '</table>'; lecture_parts.append(t); continue
        if e['type']=='img':
            f = e.get('file','')
            if f: img_files.append(f); lecture_parts.append('<img src="images/'+f+'" alt="图表" loading="lazy" onclick="openLightbox(this)">')
            continue
        text = e['text']; style = e.get('style','')
        if is_marker(text): continue
        # Check for inline scaffold markers BEFORE scaffold content
        idx, kw = find_inline_marker(text)
        if idx >= 0:
            before = text[:idx].strip()
            after_kw = text[idx+len(kw):].lstrip('\uff1a:').strip()
            if not after_kw:
                # Pure marker (e.g., " 关键思考：" with nothing after) - skip
                continue
            if before:
                lecture_parts.append('<p>'+html_mod.escape(before)+'</p>')
            # Rewrite the scaffold content as a natural paragraph
            lecture_parts.append('<p>'+html_mod.escape(after_kw)+'</p>')
            continue
        if is_scaffold_content(text):
            cleaned = strip_prefix(text)
            cls = ''
            if '错误做法' in text or '❌' in text: cls = ' class="tip-wrong"'
            elif '正确做法' in text and any(c in text for c in ('✓','✅')): cls = ' class="tip-correct"'
            elif '常见误区' in text: cls = ' class="tip-warn"'
            lecture_parts.append('<p'+cls+'>'+html_mod.escape(cleaned)+'</p>'); continue
        if re.match(r'^图\d+[-.\s]*\d*$', text.strip()) or re.match(r'^表\d+[-.\s]*\d*$', text.strip()): continue
        if style == '3': continue
        if style == '4': lecture_parts.append('<p class="subtitle">'+html_mod.escape(text)+'</p>'); continue
        if style == '5':
            t = text.strip(); is_toc = False
            if re.match(r'^\d+\.\d+\s', t): is_toc = True
            elif re.match(r'^[一二三四五六七八九十]+[、．.]\s*', t): is_toc = True
            elif t in ('总述','分述') or t.startswith('分述：') or t.startswith('分述:'): is_toc = True
            elif t in ('本章导读','学习目标','本章核心','本章内容','关键数字','名词与缩写','核心知识','知识点总结','练习与应用','核心要义凝练','预习思考与练习','名词与缩写表','关键数字表','核心板块速览表','本章收口总结','本章核心回顾','知识结构','重点内容','行为改变评估自检清单','知识衔接','章末复习','思考与练习'): is_toc = True
            if is_toc:
                toc_headings.append(t)
                safe_id = 'sec-'+re.sub(r'[^\w\u4e00-\u9fff]+','-',t).strip('-')
                lecture_parts.append('<h3 id="'+safe_id+'">'+html_mod.escape(t)+'</h3>')
            else: lecture_parts.append('<h4>'+html_mod.escape(t)+'</h4>')
            continue
        lecture_parts.append('<p>'+html_mod.escape(text)+'</p>')
    return {'lecture_html':'\n'.join(lecture_parts),'quiz_items':quiz_items,'toc_headings':toc_headings,'image_files':img_files}
def build_quiz_html(quiz_items, ch_num):
    if not quiz_items: return '<p>本章自测题目待添加。</p>'
    parts = ['<div class="quiz-container">','<div class="quiz-header"><h3>第'+str(ch_num)+'章 自测练习</h3><div class="quiz-score" id="quizScore"></div></div>','<div class="quiz-questions" id="quizQuestions">']
    q_num=0; cur_q=None; cur_choices=[]
    def flush():
        nonlocal q_num,cur_q,cur_choices
        if cur_q:
            q_num+=1; parts.append('<div class="quiz-item">')
            parts.append('<div class="quiz-q"><span class="quiz-q-num">第'+str(q_num)+'题</span> '+html_mod.escape(cur_q)+'</div>')
            for c in cur_choices: parts.append('<label class="quiz-option"><input type="radio" name="q'+str(q_num)+'"> <span>'+html_mod.escape(c)+'</span></label>')
            parts.append('</div>'); cur_q=None; cur_choices=[]
    for item in quiz_items:
        t=item.strip(); is_q=False
        for p in QUIZ_Q_PATTERNS:
            if t.startswith(p) or t==p.strip(): is_q=True; break
        if is_q:
            flush(); cur_q=t
            for p in QUIZ_Q_PATTERNS:
                if cur_q.startswith(p): cur_q=cur_q[len(p):].strip(); break
        elif is_answer_choice(t): cur_choices.append(re.sub(r'^[•●\-\s]*','',t))
    flush(); parts.append('</div></div>'); return '\n'.join(parts)
CHAPTER_INFO = {
    1:('私人教练的角色和执业范围','Role and Scope of Practice','ACE 私人教练的专业性由四件事共同定义。'),
    2:('行为改变的基础','Foundations of Behavior Change','行为改变不能只归因于意志力。'),
    3:('有效的沟通、目标设定和教学技巧','Effective Communication, Goal Setting, and Teaching Techniques','有效的沟通是将理论转化为客户行为改变的核心工具。'),
    4:('运动前健康筛查','Pre-Participation Health Screening','理解运动前健康筛查的目的、流程和执业边界。'),
    5:('心肺训练、生理机能评估和计划','Cardiorespiratory Training and Programming','心肺训练是健康体能的核心组成。'),
    6:('肌肉训练基础和计划设计','Resistance Training Fundamentals and Program Design','肌肉训练是改善体成分、提升代谢健康和运动表现的核心手段。'),
}
DOCX_DIR = '/Coze/Drive/Arise'
DOCX_FILES = {}
for ch in range(1,7):
    pattern = os.path.join(DOCX_DIR, 'ACEpresso_第'+str(ch)+'章_*.docx')
    files = glob.glob(pattern)
    if files: DOCX_FILES[ch] = files[0]
def generate_html(ch_num, lec_html, quiz_html, toc_headings):
    name,name_en,desc = CHAPTER_INFO.get(ch_num,('','',''))
    num = str(ch_num).zfill(2)
    toc_items = ''
    for h in toc_headings:
        sid = 'sec-'+re.sub(r'[^\w\u4e00-\u9fff]+','-',h).strip('-')
        toc_items += '<li class="toc-item"><a href="#'+sid+'" onclick="scrollToSection(\''+sid+'\')">'+html_mod.escape(h)+'</a></li>\n'
    nav_parts = []
    for i in range(1,7):
        cls = ' class="active"' if i==ch_num else ''
        nav_parts.append('<a href="ch'+str(i)+'.html'+cls+'">第'+str(i)+'章</a>')
    nav_links = '\n    '.join(nav_parts)
    prev_h = 'ch'+str(ch_num-1)+'.html' if ch_num>1 else 'javascript:void(0)'
    nxt_h = 'ch'+str(ch_num+1)+'.html' if ch_num<6 else 'javascript:void(0)'
    prev_l = '第'+str(ch_num-1)+'章' if ch_num>1 else '—'
    nxt_l = '第'+str(ch_num+1)+'章' if ch_num<6 else '—'
    prev_c = '' if ch_num>1 else ' disabled'
    nxt_c = ' next'+('' if ch_num<6 else ' disabled')
    html = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
    html += '<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '<title>第'+str(ch_num)+'章 '+name+' - ACEpresso</title>\n'
    html += '<link rel="stylesheet" href="style.css">\n</head>\n<body>\n'
    html += '<div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>\n'
    html += '<nav class="nav">\n'
    html += '  <div class="nav-brand" onclick="location.href=\'index.html\'"><div class="nav-logo">ACEpporesso</div><div class="nav-sub">ACE-CPT 系统精读</div></div>\n'
    html += '  <div class="nav-links">'+nav_links+'</div>\n'
    html += '  <div class="nav-actions"><button class="dark-toggle" id="darkToggle">🌙</button><button class="print-btn" onclick="window.print()">🖨️</button></div>\n'
    html += '</nav>\n'
    html += '<section class="ch-hero"><div class="ch-badge">Chapter '+num+'</div><div class="ch-num">'+num+'</div>'
    html += '<h1 class="ch-title">'+name+'</h1><div class="ch-title-en">'+name_en+'</div><p class="ch-desc">'+desc+'</p></section>\n'
    html += '<div class="tabs">'
    html += '<button class="tab-btn active" onclick="switchTab(\'lecture\',this)">📖 讲义</button>'
    html += '<button class="tab-btn" onclick="switchTab(\'cards\',this)">🃏 知识要点</button>'
    html += '<button class="tab-btn" onclick="switchTab(\'quiz\',this)">✍️ 自测</button>'
    html += '<button class="tab-btn" onclick="switchTab(\'sop\',this)"> SOP工作单</button>'
    html += '</div>\n'
    html += '<section id="lecture" class="section active"><div class="lecture-layout">'
    html += '<aside class="toc-panel" id="tocPanel"><div class="toc-header">本章目录</div><ul class="toc-list" id="tocList">'+toc_items+'</ul></aside>'
    html += '<div class="lecture-block" id="lectureContent">'+lec_html+'</div></div></section>\n'
    html += '<section id="cards" class="section"><div class="cards-intro"><h3>核心知识卡片</h3><p>本章知识要点将以互动卡片形式呈现（开发中）。</p></div></section>\n'
    html += '<section id="quiz" class="section">'+quiz_html+'</section>\n'
    html += '<section id="sop" class="section"><div class="sop-intro"><h3>SOP 工作单</h3><p>SOP 工作单将在讲义确认后逐章制作。</p></div></section>\n'
    html += '<div class="chapter-nav">'
    html += '<a class="chapter-nav-item'+prev_c+'" href="'+prev_h+'"><span class="chapter-nav-label">← 上一章</span><span class="chapter-nav-title">'+prev_l+'</span></a>'
    html += '<a class="chapter-nav-item'+nxt_c+'" href="'+nxt_h+'"><span class="chapter-nav-label">下一章 →</span><span class="chapter-nav-title">'+nxt_l+'</span></a>'
    html += '</div>\n'
    html += '<script>\n'
    html += 'function switchTab(id,btn){document.querySelectorAll(".tab-btn").forEach(b=>b.classList.remove("active"));btn.classList.add("active");document.querySelectorAll(".section").forEach(s=>s.classList.remove("active"));document.getElementById(id).classList.add("active");document.getElementById("tocPanel").style.display=id==="lecture"?"":"none";}\n'
    html += 'function scrollToSection(id){const el=document.getElementById(id);if(el)el.scrollIntoView({behavior:"smooth",block:"start"});}\n'
    html += 'const dt=document.getElementById("darkToggle");if(localStorage.getItem("darkMode")==="1"){document.body.classList.add("dark-mode");dt.textContent="️";}\n'
    html += 'dt.addEventListener("click",()=>{document.body.classList.toggle("dark-mode");const d=document.body.classList.contains("dark-mode");localStorage.setItem("darkMode",d?"1":"0");dt.textContent=d?"☀️":"🌙";});\n'
    html += 'function updateProgress(){const c=document.getElementById("lectureContent");if(!c)return;const r=c.getBoundingClientRect();const h=c.scrollHeight-window.innerHeight;const s=Math.max(0,-r.top);const p=h>0?Math.min(100,(s/h)*100):0;document.getElementById("progressFill").style.width=p+"%";}\n'
    html += 'window.addEventListener("scroll",updateProgress);window.addEventListener("load",updateProgress);\n'
    html += 'function openLightbox(img){const o=document.createElement("div");o.className="lightbox-overlay";o.onclick=()=>o.remove();const im=document.createElement("img");im.className="lightbox-img";im.src=img.src;o.appendChild(im);document.body.appendChild(o);}\n'
    html += 'window.addEventListener("scroll",()=>{const hs=document.querySelectorAll("#lectureContent h3,#lectureContent h4");const tis=document.querySelectorAll(".toc-item");let cur="";hs.forEach(h=>{if(h.getBoundingClientRect().top<=120)cur=h.id;});tis.forEach(t=>{t.classList.toggle("active",t.querySelector("a")?.getAttribute("href")==="#"+cur);});});\n'
    html += '</script>\n</body>\n</html>'
    return html
def process_and_save(ch_num, output_dir):
    fp = DOCX_FILES.get(ch_num)
    if not fp: print(f'ERROR: File not found for ch{ch_num}'); return False
    print(f'\n=== Chapter {ch_num} ===')
    elements = extract_docx(fp)
    pc = sum(1 for e in elements if e['type']=='p')
    tc = sum(1 for e in elements if e['type']=='tbl')
    ic = sum(1 for e in elements if e['type']=='img')
    print(f'Extracted: {pc} paragraphs, {tc} tables, {ic} images')
    result = process_chapter(elements)
    ms = sum(1 for e in elements if e['type']=='p' and is_marker(e['text']))
    print(f'Skipped markers: {ms}, Quiz items: {len(result["quiz_items"])}, TOC headings: {len(result["toc_headings"])}')
    print(f'Lecture HTML: {len(result["lecture_html"])} chars')
    qhtml = build_quiz_html(result['quiz_items'], ch_num)
    output = generate_html(ch_num, result['lecture_html'], qhtml, result['toc_headings'])
    outpath = os.path.join(output_dir, f'ch{ch_num}.html')
    with open(outpath,'w',encoding='utf-8') as f: f.write(output)
    print(f'Saved: {outpath} ({os.path.getsize(outpath)} bytes)')
    return True
if __name__=='__main__':
    od = '/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso'
    if len(sys.argv)>1: process_and_save(int(sys.argv[1]), od)
    else:
        for ch in range(1,7): process_and_save(ch, od)
