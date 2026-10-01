#!/usr/bin/env python3
"""
将 ch1.html 原地转换为编辑报风排版
直接修改原文件，保留所有内容
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

def convert_chapter(ch_num):
    ch_id = CHAPTERS[ch_num - 1][1]
    title = CHAPTERS[ch_num - 1][2]
    en_title = CHAPTERS[ch_num - 1][3]

    html = (WORK_DIR / f'{ch_id}.html').read_text(encoding='utf-8')

    # 1. 替换 CSS：删除内联 <style> 块，改为引用 acepresso.css
    html = re.sub(r'<style>.*?</style>', '<link rel="stylesheet" href="acepresso.css">', html, count=1, flags=re.DOTALL)

    # 2. 替换 meta bar
    old_header = r'''<header class="site-header">
  <div class="logo">ACEpresso <span>循证私人教练教育</span></div>
  <button class="theme-toggle" onclick="toggleTheme()">◐ 主题</button>
</header>'''

    new_header = f'''<div class="meta-bar">
  <div class="meta-left">
    <span class="brand">ACEPRESSO</span>
    <span class="brand-sub">循证私人教练教育</span>
    <span class="chapter-label">CH{ch_num:02d}</span>
  </div>
  <div class="meta-right">
    <span>{title}</span>
    <button class="theme-toggle" onclick="toggleTheme()">◐ Theme</button>
  </div>
</div>'''

    html = html.replace(old_header, new_header)

    # 3. 更新 hero
    old_hero_pattern = r'''<div class="hero">
      <div class="badge">第\d+章</div>
      <h1>.*?</h1>
      <div class="subtitle">.*?</div>
      <div class="intro">.*?</div>
    </div>'''

    new_hero = f'''<div class="hero">
  <div class="hero-meta">Chapter {ch_num:02d} &middot; ACEpresso &middot; 循证私人教练教育</div>
  <h1>{title}</h1>
  <div class="subtitle-en">{en_title}</div>
</div>'''

    html = re.sub(old_hero_pattern, new_hero, html, flags=re.DOTALL)

    # 4. 更新 tabs
    old_tabs = '''<div class="tabs">
      <button class="tab-btn active" onclick="switchTab('lecture', this)">讲义</button>
      <button class="tab-btn" onclick="switchTab('quiz', this)">自测</button>
      <button class="tab-btn" onclick="switchTab('sop', this)">SOP工作单</button>
    </div>'''

    new_tabs = '''<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('lecture', this)">讲义</button>
  <button class="tab-btn" onclick="switchTab('quiz', this)">自测</button>
</div>'''

    html = html.replace(old_tabs, new_tabs)

    # 5. 更新 sidebar - 添加章间导航
    old_sidebar_end = '</nav>\n\n  <main class="main-content">'

    prev_ch = CHAPTERS[ch_num - 2] if ch_num > 1 else None
    next_ch = CHAPTERS[ch_num] if ch_num < len(CHAPTERS) else None

    chapter_nav_html = '''
  <div class="chapter-nav">
    <div class="chapter-nav-title">全部章节</div>'''

    for num, fname, t, et in CHAPTERS:
        cls = 'current' if num == ch_num else ''
        chapter_nav_html += f'\n    <a href="{fname}.html" class="{cls}">Ch{num}. {t}</a>'

    chapter_nav_html += '\n  </div>\n</nav>\n\n  <main class="main-content">'

    html = html.replace(old_sidebar_end, chapter_nav_html)

    # 6. 更新卡片标签样式（保留原有内容，只改标签文字为编辑风）
    label_map = {
        '要点': 'KNOW',
        '⚠ 常见误区': 'CAUTION',
        '✗ 错误做法': 'AVOID',
        '✓ 正确做法': 'DO THIS',
        '场景': 'SCENE',
        '记忆提示': 'REMEMBER',
    }

    for old_label, new_label in label_map.items():
        html = html.replace(f'<span class="card-label">{old_label}</span>',
                          f'<span class="card-label">{new_label}</span>')

    # 7. 添加章间导航底部
    footer_html = ''
    if prev_ch or next_ch:
        footer_html = '<div class="chapter-footer">'
        if prev_ch:
            footer_html += f'<div><div class="nav-label">上一章</div><a href="{prev_ch[1]}.html" class="nav-title">Ch{prev_ch[0]}. {prev_ch[2]}</a></div>'
        else:
            footer_html += '<div></div>'
        if next_ch:
            footer_html += f'<div style="text-align:right"><div class="nav-label">下一章</div><a href="{next_ch[1]}.html" class="nav-title">Ch{next_ch[0]}. {next_ch[2]}</a></div>'
        else:
            footer_html += '<div></div>'
        footer_html += '</div>'

    # 在 </main> 前插入 footer
    html = html.replace('</main>\n</div>', footer_html + '\n</main>\n</div>')

    # 8. 添加灯箱 div
    html = html.replace('</body>', '<div class="lightbox" id="lightbox"><img src="" alt="放大"></div>\n</body>')

    # 9. 更新 JS
    old_js = '''<script>
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}
function switchTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
}
(function() {
  const saved = localStorage.getItem('theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
window.addEventListener('scroll', function() {
  const h = document.documentElement;
  const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
  document.getElementById('progressBar').style.width = pct + '%';
});
const tocLinks = document.querySelectorAll('.toc-link');
const sections = document.querySelectorAll('[id^="s"]');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      tocLinks.forEach(link => link.classList.remove('active'));
      const id = entry.target.getAttribute('id');
      const link = document.querySelector('.toc-link[href="#' + id + '"]');
      if (link) link.classList.add('active');
    }
  });
}, { rootMargin: '-20% 0px -70% 0px' });
sections.forEach(section => observer.observe(section));
document.querySelectorAll('.main-content img').forEach(img => {
  img.addEventListener('click', function() {
    const lb = document.getElementById('lightbox');
    lb.querySelector('img').src = this.src;
    lb.classList.add('active');
  });
});
document.getElementById('lightbox').addEventListener('click', function() {
  this.classList.remove('active');
});
</script>'''

    new_js = '''<script>
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}
function switchTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
}
(function() {
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
  else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.setAttribute('data-theme', 'dark');
})();
window.addEventListener('scroll', function() {
  const h = document.documentElement;
  const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
  document.getElementById('progressBar').style.width = pct + '%';
});
const tocLinks = document.querySelectorAll('.toc-link');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      tocLinks.forEach(l => l.classList.remove('active'));
      const id = e.target.id;
      const link = document.querySelector('.toc-link[href="#' + id + '"]');
      if (link) link.classList.add('active');
    }
  });
}, { rootMargin: '-20% 0px -70% 0px' });
document.querySelectorAll('[id^="s"]').forEach(el => observer.observe(el));
document.querySelectorAll('.main-content img').forEach(img => {
  img.addEventListener('click', function() {
    const lb = document.getElementById('lightbox');
    lb.querySelector('img').src = this.src;
    lb.classList.add('active');
  });
});
document.getElementById('lightbox').addEventListener('click', function() {
  this.classList.remove('active');
});
</script>'''

    html = html.replace(old_js, new_js)

    # 10. 更新进度条位置（移到 meta-bar 下面）
    html = html.replace('<div class="progress-bar"', '<div class="progress-bar"')

    # 11. 更新 tab content id 格式
    html = html.replace("onclick=\"switchTab('lecture'", "onclick=\"switchTab('lecture'")
    html = html.replace("onclick=\"switchTab('quiz'", "onclick=\"switchTab('quiz'")

    # 写入
    (WORK_DIR / f'{ch_id}.html').write_text(html, encoding='utf-8')

    # 统计
    cards = len(re.findall(r'class="card card-', html))
    quiz = len(re.findall(r'quiz-item', html))
    imgs = len(re.findall(r'<img', html))
    tables = len(re.findall(r'<table', html))
    ps = len(re.findall(r'<p', html))

    print(f'✅ Ch{ch_num} {title}')
    print(f'   大小: {len(html):,} bytes | 卡片: {cards} | 自测: {quiz} | 图片: {imgs} | 表格: {tables} | 段落: {ps}')

# 先处理 ch1
convert_chapter(1)
