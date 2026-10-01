#!/usr/bin/env python3
"""
Clean rebuild: read original ch1.html content, wrap in new editorial template.
Preserves ALL body content (paragraphs, tables, images, cards, quiz).
"""

import re
from pathlib import Path
from bs4 import BeautifulSoup

WORK_DIR = Path(__file__).parent
CHAPTERS = [
    (1, "ch1", "私人教练的角色和执业范围", "The Role and Scope of Practice for the Personal Trainer"),
    (2, "ch2", "行为改变的基础", "Foundations of Behavior Change"),
    (3, "ch3", "有效的沟通、目标设定和教学技巧", "Effective Communication, Goal Setting, and Teaching Techniques"),
    (4, "ch4", "运动前健康筛查", "Preparticipation Health Screening"),
    (5, "ch5", "心肺训练：生理机能、评估和计划", "Cardiorespiratory Training: Physiology, Assessment, and Programming"),
    (6, "ch6", "肌肉训练：基础、益处和计划设计", "Resistance Training: Fundamentals, Benefits, and Program Design"),
    (7, "ch7", "慢性病客户注意事项", "Special Considerations for Clients with Chronic Diseases"),
    (8, "ch8", "各个生命阶段的运动注意事项", "Exercise Considerations Across the Lifespan"),
    (9, "ch9", "肌肉骨骼异常客户的注意事项", "Special Considerations for Clients with Musculoskeletal Abnormalities"),
]

def process_chapter(ch_num):
    ch_id = CHAPTERS[ch_num - 1][1]
    title = CHAPTERS[ch_num - 1][2]
    en_title = CHAPTERS[ch_num - 1][3]

    html = (WORK_DIR / f'{ch_id}.html').read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # 提取 TOC 链接
    toc_links = []
    sidebar = soup.find('nav', class_='sidebar')
    if sidebar:
        for a in sidebar.find_all('a', class_='toc-link'):
            toc_links.append({
                'href': a.get('href', ''),
                'class': ' '.join(a.get('class', [])),
                'text': a.get_text(strip=True)
            })

    # 提取主内容区（去掉旧的 hero 和 tabs）
    main = soup.find('main', class_='main-content')
    if not main:
        print(f'❌ Ch{ch_num}: 找不到 main-content')
        return

    # 收集所有子元素
    content_elements = []
    for child in main.children:
        if hasattr(child, 'name') and child.name:  # 只处理 Tag，跳过 NavigableString
            tag = child.name
            cls = ' '.join(child.get('class', [])) if child.get('class') else ''

            # 跳过旧的 hero、tabs、SOP tab、chapter-nav
            if tag == 'div' and ('hero' in cls or 'tabs' in cls):
                continue
            if tag == 'div' and 'tab-content' in cls and 'sop' in child.get('id', ''):
                continue
            if tag == 'div' and 'chapter-nav' in cls:
                continue

            content_elements.append(str(child))

    content_html = '\n'.join(content_elements)

    # 清理内容中旧的 lightbox / chapter-nav / chapter-footer（如果存在）
    content_html = re.sub(r'<div class="chapter-nav">.*?</div>\s*</nav>', '', content_html, flags=re.DOTALL)
    content_html = re.sub(r'<div class="chapter-footer">.*?</div>', '', content_html, flags=re.DOTALL)
    content_html = re.sub(r'<div class="lightbox[^"]*">.*?</div>', '', content_html, flags=re.DOTALL)

    # 更新卡片标签为英文编辑风
    label_map = {
        '要点': 'KNOW',
        ' 常见误区': 'CAUTION',
        '常见误区': 'CAUTION',
        '✗ 错误做法': 'AVOID',
        '错误做法': 'AVOID',
        '✓ 正确做法': 'DO THIS',
        '正确做法': 'DO THIS',
        '场景': 'SCENE',
        '记忆提示': 'REMEMBER',
    }
    for old_label, new_label in label_map.items():
        content_html = content_html.replace(f'class="card-label">{old_label}', f'class="card-label">{new_label}')

    # 构建 TOC sidebar
    toc_html = '<nav class="sidebar">\n<div class="toc-title">本章目录</div>\n'
    for link in toc_links:
        toc_html += f'<a href="{link["href"]}" class="{link["class"]}">{link["text"]}</a>\n'

    # 章间导航
    toc_html += '<div class="chapter-nav">\n<div class="chapter-nav-title">全部章节</div>\n'
    for num, fname, t, et in CHAPTERS:
        cls = 'current' if num == ch_num else ''
        toc_html += f'<a href="{fname}.html" class="{cls}">Ch{num}. {t}</a>\n'
    toc_html += '</div>\n</nav>'

    # 章间导航底部
    prev_ch = CHAPTERS[ch_num - 2] if ch_num > 1 else None
    next_ch = CHAPTERS[ch_num] if ch_num < len(CHAPTERS) else None

    footer_parts = []
    if prev_ch:
        footer_parts.append(f'<div><div class="nav-label">上一章</div><a href="{prev_ch[1]}.html" class="nav-title">Ch{prev_ch[0]}. {prev_ch[2]}</a></div>')
    else:
        footer_parts.append('<div></div>')
    if next_ch:
        footer_parts.append(f'<div style="text-align:right"><div class="nav-label">下一章</div><a href="{next_ch[1]}.html" class="nav-title">Ch{next_ch[0]}. {next_ch[2]}</a></div>')
    else:
        footer_parts.append('<div></div>')
    chapter_footer = '<div class="chapter-footer">' + ''.join(footer_parts) + '</div>'

    # 构建完整页面
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>第{ch_num}章 {title} | ACEpresso</title>
<link rel="stylesheet" href="acepresso.css">
</head>
<body>

<div class="progress-bar" id="progressBar"></div>

<div class="meta-bar">
  <div class="meta-left">
    <span class="brand">ACEPRESSO</span>
    <span class="brand-sub">循证私人教练教育</span>
    <span class="chapter-label">CH{ch_num:02d}</span>
  </div>
  <div class="meta-right">
    <span>{title}</span>
    <button class="theme-toggle" onclick="toggleTheme()">◐ Theme</button>
  </div>
</div>

<div class="layout">
  {toc_html}
  <main class="main-content">
    <div class="hero">
      <div class="hero-meta">Chapter {ch_num:02d} &middot; ACEpresso &middot; 循证私人教练教育</div>
      <h1>{title}</h1>
      <div class="subtitle-en">{en_title}</div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('lecture', this)">讲义</button>
      <button class="tab-btn" onclick="switchTab('quiz', this)">自测</button>
    </div>

    {content_html}

    {chapter_footer}
  </main>
</div>

<div class="lightbox" id="lightbox"><img src="" alt="放大"></div>

<script>
function toggleTheme() {{
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}}
function switchTab(name, btn) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
}}
(function() {{
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
  // 默认亮色，不自动跟随系统暗色
}})();
window.addEventListener('scroll', function() {{
  const h = document.documentElement;
  const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
  document.getElementById('progressBar').style.width = pct + '%';
}});
const tocLinks = document.querySelectorAll('.toc-link');
const observer = new IntersectionObserver((entries) => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      tocLinks.forEach(l => l.classList.remove('active'));
      const id = e.target.id;
      const link = document.querySelector('.toc-link[href="#' + id + '"]');
      if (link) link.classList.add('active');
    }}
  }});
}}, {{ rootMargin: '-20% 0px -70% 0px' }});
document.querySelectorAll('[id^="s"]').forEach(el => observer.observe(el));
document.querySelectorAll('.main-content img').forEach(img => {{
  img.addEventListener('click', function() {{
    const lb = document.getElementById('lightbox');
    lb.querySelector('img').src = this.src;
    lb.classList.add('active');
  }});
}});
document.getElementById('lightbox').addEventListener('click', function() {{
  this.classList.remove('active');
}});
</script>

</body>
</html>'''

    (WORK_DIR / f'{ch_id}.html').write_text(page, encoding='utf-8')

    # 统计
    cards = len(re.findall(r'class="card card-', page))
    quiz = len(re.findall(r'quiz-item', page))
    imgs = len(re.findall(r'<img', page))
    tables = len(re.findall(r'<table', page))
    ps = len(re.findall(r'<p', page))

    print(f'✅ Ch{ch_num} {title}')
    print(f'   {len(page):,} bytes | 卡片: {cards} | 自测: {quiz} | 图片: {imgs} | 表格: {tables} | 段落: {ps}')

# 检查依赖
try:
    from bs4 import BeautifulSoup
    print('BeautifulSoup available')
except ImportError:
    print('Installing beautifulsoup4...')
    import subprocess
    subprocess.run(['pip', 'install', 'beautifulsoup4', '-q'])
    from bs4 import BeautifulSoup
    print('BeautifulSoup installed')

process_chapter(1)
