#!/usr/bin/env python3
"""
将 ch1.html 转换为编辑报风排版
- 替换内联 CSS 为外部 acepresso.css
- 更新 HTML 结构（meta bar, hero, sidebar, cards, quiz）
- 保留所有内容（段落、表格、图片、知识卡片）
- 添加章间导航
"""

import re
from pathlib import Path

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

def make_sidebar_toc(ch_num, toc_links_html):
    """生成侧边栏 TOC"""
    lines = ['<nav class="sidebar">', '<div class="toc-title">本章目录</div>']

    # 解析 toc_links_html 中的链接
    pattern = r'<a\s+href="(#s\d+)"\s+class="toc-link\s+([^"]*)">([^<]+)</a>'
    matches = re.findall(pattern, toc_links_html)

    for href, cls, text in matches:
        lines.append(f'<a href="{href}" class="toc-link {cls}">{text}</a>')

    # 章间导航
    lines.append('<div class="chapter-nav">')
    lines.append('<div class="chapter-nav-title">全部章节</div>')
    for num, fname, title, en_title in CHAPTERS:
        cls = 'current' if num == ch_num else ''
        lines.append(f'<a href="{fname}.html" class="{cls}">Ch{num}. {title}</a>')
    lines.append('</div>')
    lines.append('</nav>')
    return '\n'.join(lines)

def transform_cards(html_content):
    """将旧样式卡片转换为编辑报风卡片"""
    # card-tip, card-wrong, card-right, card-warn, card-scene, card-memory
    card_types = ['tip', 'wrong', 'right', 'warn', 'scene', 'memory']
    card_labels = {
        'tip': '知识要点',
        'wrong': '错误做法',
        'right': '正确做法',
        'warn': '常见误区',
        'scene': '典型场景',
        'memory': '记忆提示',
    }

    for ct in card_types:
        # 匹配旧的 card 结构: <div class="card card-xxx">...</div>
        pattern = rf'<div class="card card-{ct}">(.*?)</div>'
        replacement = rf'<div class="card card-{ct}"><span class="card-label">{card_labels[ct]}</span>\1</div>'
        html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

    return html_content

def transform_quiz(html_content):
    """转换自测题样式"""
    # quiz-section 已经存在，主要是更新 quiz-item 结构
    # 添加 quiz-tag
    pattern = r'<div class="quiz-item">(.*?)</div>'

    def replace_quiz(m):
        inner = m.group(1)
        if '<span class="quiz-tag">' not in inner and '<div class="quiz-tag">' not in inner:
            inner = '<span class="quiz-tag">自测</span>' + inner
        return f'<div class="quiz-item">{inner}</div>'

    html_content = re.sub(pattern, replace_quiz, html_content, flags=re.DOTALL)
    return html_content

def build_page(ch_num, ch_id, title, en_title, original_html):
    """构建完整的编辑报风页面"""

    # 提取原文中的内容区域（sidebar 和 main-content 之间）
    # 找到 toc_links 和 main content
    sidebar_match = re.search(r'<nav class="sidebar">(.*?)</nav>', original_html, re.DOTALL)
    toc_html = sidebar_match.group(1) if sidebar_match else ''

    # 提取 main-content 中的内容
    main_match = re.search(r'<main class="main-content">(.*?)</main>', original_html, re.DOTALL)
    main_inner = main_match.group(1) if main_match else ''

    # 从 main_inner 中提取 hero 之后的内容
    # 移除旧的 hero 区域
    hero_pattern = r'<div class="hero">.*?</div>\s*(?=<div class="tabs">)'
    content_after_hero = re.sub(hero_pattern, '', main_inner, flags=re.DOTALL)

    # 移除旧的 tabs
    tabs_pattern = r'<div class="tabs">.*?</div>\s*(?=<div class="tab-content)'
    content_clean = re.sub(tabs_pattern, '', content_after_hero, flags=re.DOTALL)

    # 转换卡片样式
    content_clean = transform_cards(content_clean)
    content_clean = transform_quiz(content_clean)

    # 构建新的 hero
    new_hero = f'''<div class="hero">
  <div class="hero-meta">Chapter {ch_num:02d} &middot; ACEpresso &middot; 循证私人教练教育</div>
  <h1>{title}</h1>
  <div class="subtitle-en">{en_title}</div>
</div>'''

    # 构建新的 tabs
    new_tabs = '''<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('lecture')">讲义</button>
  <button class="tab-btn" onclick="switchTab('quiz')">自测</button>
</div>'''

    # 构建章间导航底部
    prev_ch = CHAPTERS[ch_num - 2] if ch_num > 1 else None
    next_ch = CHAPTERS[ch_num] if ch_num < len(CHAPTERS) else None

    chapter_footer = '<div class="chapter-footer">'
    if prev_ch:
        chapter_footer += f'<div><div class="nav-label">上一章</div><a href="{prev_ch[1]}.html" class="nav-title">Ch{prev_ch[0]}. {prev_ch[2]}</a></div>'
    else:
        chapter_footer += '<div></div>'
    if next_ch:
        chapter_footer += f'<div style="text-align:right"><div class="nav-label">下一章</div><a href="{next_ch[1]}.html" class="nav-title">Ch{next_ch[0]}. {next_ch[2]}</a></div>'
    else:
        chapter_footer += '<div></div>'
    chapter_footer += '</div>'

    # 组装完整内容
    new_main = f'''{new_hero}
{new_tabs}
<div class="tab-content active" id="tab-lecture">
{content_clean}
</div>
{chapter_footer}'''

    # 构建侧边栏
    new_sidebar = make_sidebar_toc(ch_num, toc_html)

    # 构建完整页面
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>第{ch_num}章 {title} | ACEpresso</title>
<link rel="stylesheet" href="acepresso.css">
<script>
function toggleTheme() {{
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}}
function switchTab(name) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}
(function() {{
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
  else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.setAttribute('data-theme', 'dark');
}})();

// 滚动进度条
window.addEventListener('scroll', function() {{
  const h = document.documentElement;
  const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
  document.getElementById('progressBar').style.width = pct + '%';
}});

// TOC 高亮
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

// 图片灯箱
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
  {new_sidebar}
  <main class="main-content">
    {new_main}
  </main>
</div>

<div class="lightbox" id="lightbox"><img src="" alt="放大"></div>

</body>
</html>'''

    return page

# 处理 ch1
ch_num, ch_id, title, en_title = CHAPTERS[0]
ch_file = WORK_DIR / f'{ch_id}.html'
original = ch_file.read_text(encoding='utf-8')

new_page = build_page(ch_num, ch_id, title, en_title, original)
output_file = WORK_DIR / f'{ch_id}_editorial.html'
output_file.write_text(new_page, encoding='utf-8')

print(f'✅ {ch_id}_editorial.html 已生成 ({len(new_page)} bytes)')
