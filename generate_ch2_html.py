import json
import re
import os

output_dir = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"
images_dir = os.path.join(output_dir, "images")

with open(os.path.join(output_dir, '_ch2_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

content_blocks = data['content_blocks']
headings = data['headings']
table_count = data['table_count']
image_count = data['image_count']

def html_escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def classify_card(text):
    """Returns (card_class, label, content) or (None, None, text)"""
    # 要点
    if text.startswith('要点：') or text.startswith('要点:'):
        sep = '：' if '：' in text[:5] else ':'
        content = text.split(sep, 1)[1]
        return 'card-tip', '要点', content
    # ❌ 错误做法
    if re.match(r'^❌\s*错误做法', text):
        content = re.split(r'[：:]', text, 1)[1] if re.search(r'[：:]', text) else text
        return 'card-wrong', '✗ 错误', content
    # ✓ 正确做法
    if re.match(r'^✓\s*正确做法', text):
        content = re.split(r'[：:]', text, 1)[1] if re.search(r'[：:]', text) else text
        return 'card-right', '✓ 正确', content
    # 常见误区/误区
    if re.match(r'^(常见)?误区[：:]', text):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-warn', '⚠ 误区', content
    # 场景
    if text.startswith('场景：') or text.startswith('场景:'):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-scene', '📋 场景', content
    # 记忆提示/口诀
    if re.match(r'^记忆(提示|口诀)[：:]', text):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-memory', '🧠 记忆', content
    # 🎯教练小tips with content
    if re.match(r'^🎯\s*教练小[Tt]ips[：:]', text):
        content = re.split(r'[：:]', text, 1)[1]
        return 'card-tip', '💡 教练提示', content
    return None, None, text

def render_text_block(text, images):
    """Render a text block, possibly as a card"""
    card_class, label, content = classify_card(text)
    
    img_html = ''
    if images:
        for img in images:
            img_html += f'<img src="images/{img}" class="inline-img" loading="lazy" onclick="openLightbox(this.src)">'
    
    if card_class:
        return f'<div class="card {card_class}"><span class="card-label">{html_escape(label)}</span><p>{html_escape(content)}{img_html}</p></div>'
    else:
        p_content = html_escape(text)
        if img_html:
            p_content += img_html
        return f'<p>{p_content}</p>'

def render_table(rows):
    if not rows:
        return ''
    html = '<table>\n'
    for i, row in enumerate(rows):
        html += '<tr>\n'
        tag = 'th' if i == 0 else 'td'
        for cell in row:
            cell_html = html_escape(cell).replace('\n', '<br>')
            html += f'  <{tag}>{cell_html}</{tag}>\n'
        html += '</tr>\n'
    html += '</table>'
    return html

# Build main content HTML
content_html_parts = []
for block in content_blocks:
    if block['type'] == 'table':
        content_html_parts.append(render_table(block['rows']))
    elif block['type'] == 'images_only':
        for img in block['images']:
            content_html_parts.append(f'<figure><img src="images/{img}" loading="lazy" onclick="openLightbox(this.src)"></figure>')
    elif block['type'] == 'text':
        text = block['text']
        style = block.get('style', '')
        images = block.get('images', [])
        
        # Skip residual empty scaffold markers
        stripped = text.strip().lower().replace(' ', '')
        if stripped in ['💡记忆技巧', '💡关键思考', '💡章节小节', '📚记忆技巧', 
                         '🎯教练小tips', '【记忆技巧】']:
            continue
        
        # Render heading
        if 'heading_level' in block and 'heading_id' in block:
            level = block['heading_level']
            hid = block['heading_id']
            tag = f'h{level}'
            content_html_parts.append(f'<{tag} id="{hid}">{html_escape(text)}</{tag}>')
        else:
            content_html_parts.append(render_text_block(text, images))

main_content = '\n'.join(content_html_parts)

# Build TOC
toc_html = '<ul class="toc-list">\n'
for level, text, hid in headings:
    indent = (level - 2) * 16  # h2=0, h3=16, h4=32, h5=48
    toc_html += f'<li style="padding-left:{indent}px"><a href="#{hid}">{html_escape(text)}</a></li>\n'
toc_html += '</ul>'

# Chapter title info
ch_title = "行为改变的基础"
ch_subtitle = "Foundations of Behavior Change"
ch_intro = "本章系统梳理行为改变的理论模型（健康信念模型、自我决定理论、跨理论模型）、底层原理（操作性条件反射与认知行为）以及影响运动坚持的关键因素。理解这些内容是私人教练帮助客户从"开始运动"走向"坚持运动"的知识基础。"

# Generate full HTML
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>第2章 行为改变的基础 | ACEpresso</title>
<style>
:root {{
  --bg: #fafafa;
  --bg-card: #ffffff;
  --text: #1a1a1a;
  --text-secondary: #555;
  --border: #e0e0e0;
  --accent: #2e7d32;
  --accent-light: #e8f5e9;
  --header-bg: #1b5e20;
  --sidebar-bg: #f5f5f5;
  --table-header: #2e7d32;
  --table-stripe: #f5f5f5;
  --shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
[data-theme="dark"] {{
  --bg: #121212;
  --bg-card: #1e1e1e;
  --text: #e0e0e0;
  --text-secondary: #aaa;
  --border: #333;
  --accent: #66bb6a;
  --accent-light: #1b3a1e;
  --header-bg: #0d3010;
  --sidebar-bg: #1a1a1a;
  --table-header: #1b5e20;
  --table-stripe: #252525;
  --shadow: 0 2px 8px rgba(0,0,0,0.3);
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: "Noto Serif SC", "Source Han Serif CN", -apple-system, serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.8;
  font-size: 16px;
  transition: background 0.3s, color 0.3s;
}}

/* Header */
.header {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--header-bg);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 1000;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}}
.header .logo {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
}}
.header .logo span {{ color: #a5d6a7; }}
.theme-toggle {{
  background: none;
  border: 1px solid rgba(255,255,255,0.3);
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}}
.theme-toggle:hover {{ background: rgba(255,255,255,0.1); }}

/* Progress bar */
.progress-bar {{
  position: fixed;
  top: 56px;
  left: 0;
  height: 3px;
  background: var(--accent);
  z-index: 999;
  transition: width 0.1s;
}}

/* Layout */
.layout {{
  display: flex;
  margin-top: 56px;
  min-height: calc(100vh - 56px);
}}

/* Sidebar */
.sidebar {{
  width: 280px;
  min-width: 280px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  padding: 20px 16px;
  position: fixed;
  top: 56px;
  bottom: 0;
  overflow-y: auto;
  transition: transform 0.3s;
}}
.sidebar h3 {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 12px;
  letter-spacing: 1px;
}}
.toc-list {{
  list-style: none;
}}
.toc-list li {{
  margin: 2px 0;
}}
.toc-list a {{
  display: block;
  padding: 5px 10px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-family: "Noto Sans SC", sans-serif;
  border-radius: 4px;
  transition: all 0.2s;
  line-height: 1.4;
}}
.toc-list a:hover {{
  background: var(--accent-light);
  color: var(--accent);
}}

/* Main content */
.main-content {{
  flex: 1;
  margin-left: 280px;
  max-width: 900px;
  padding: 0 40px 60px;
}}

/* Hero */
.hero {{
  padding: 48px 0 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}}
.hero .badge {{
  display: inline-block;
  background: var(--accent);
  color: #fff;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 12px;
  margin-bottom: 12px;
}}
.hero h1 {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 32px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
  line-height: 1.3;
}}
.hero .subtitle {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  font-style: italic;
}}
.hero .intro {{
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.8;
  max-width: 680px;
}}

/* Tabs */
.tabs {{
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--border);
  margin-bottom: 32px;
}}
.tab-btn {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  padding: 10px 20px;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}}
.tab-btn.active {{
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

/* Typography */
h2 {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 26px;
  font-weight: 700;
  color: var(--text);
  margin: 48px 0 20px;
  padding-bottom: 10px;
  border-bottom: 3px solid var(--accent);
  line-height: 1.3;
}}
h3 {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
  margin: 32px 0 16px;
  padding-left: 14px;
  border-left: 4px solid var(--accent);
  line-height: 1.4;
}}
h4 {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
  margin: 24px 0 12px;
  line-height: 1.4;
}}
h5 {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 20px 0 10px;
  line-height: 1.4;
}}
p {{
  margin: 12px 0;
  font-size: 16px;
  line-height: 1.8;
  color: var(--text);
}}

/* Cards */
.card {{
  margin: 16px 0;
  padding: 14px 18px;
  border-radius: 8px;
  border-left: 4px solid;
}}
.card .card-label {{
  font-weight: 700;
  font-size: 13px;
  display: block;
  margin-bottom: 6px;
  font-family: "Noto Sans SC", sans-serif;
}}
.card p {{
  margin: 0;
  font-size: 15px;
  line-height: 1.7;
}}
.card-tip {{ background: #e8f5e9; border-color: #4caf50; }}
.card-tip .card-label {{ color: #2e7d32; }}
.card-wrong {{ background: #fce4ec; border-color: #e53935; }}
.card-wrong .card-label {{ color: #c62828; }}
.card-right {{ background: #e3f2fd; border-color: #1e88e5; }}
.card-right .card-label {{ color: #1565c0; }}
.card-warn {{ background: #fff8e1; border-color: #ff8f00; }}
.card-warn .card-label {{ color: #e65100; }}
.card-scene {{ background: #f3e5f5; border-color: #7b1fa2; }}
.card-scene .card-label {{ color: #6a1b9a; }}
.card-memory {{ background: #f5f5f5; border-color: #9e9e9e; }}
.card-memory .card-label {{ color: #616161; }}
.card-memory p {{ font-size: 13.5px; color: #555; }}

[data-theme="dark"] .card-tip {{ background: #1b3a1e; }}
[data-theme="dark"] .card-wrong {{ background: #3a1b1b; }}
[data-theme="dark"] .card-right {{ background: #1b2a3a; }}
[data-theme="dark"] .card-warn {{ background: #3a2e1b; }}
[data-theme="dark"] .card-scene {{ background: #2e1b3a; }}
[data-theme="dark"] .card-memory {{ background: #252525; }}

/* Tables */
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 14px;
  font-family: "Noto Sans SC", sans-serif;
  box-shadow: var(--shadow);
  border-radius: 8px;
  overflow: hidden;
}}
th {{
  background: var(--table-header);
  color: #fff;
  padding: 12px 14px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
}}
td {{
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}}
tr:nth-child(even) td {{
  background: var(--table-stripe);
}}

/* Images */
figure {{
  margin: 24px 0;
  text-align: center;
}}
.inline-img, figure img {{
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: transform 0.2s;
}}
.inline-img:hover, figure img:hover {{
  transform: scale(1.02);
}}
figcaption {{
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
  font-family: "Noto Sans SC", sans-serif;
}}

/* Lightbox */
.lightbox {{
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.9);
  z-index: 2000;
  justify-content: center;
  align-items: center;
  cursor: pointer;
}}
.lightbox.active {{ display: flex; }}
.lightbox img {{
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
}}

/* Navigation */
.chapter-nav {{
  display: flex;
  justify-content: space-between;
  margin: 48px 0 24px;
  padding: 20px 0;
  border-top: 1px solid var(--border);
}}
.chapter-nav a {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: var(--accent);
  text-decoration: none;
  padding: 8px 16px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  transition: all 0.2s;
}}
.chapter-nav a:hover {{
  background: var(--accent);
  color: #fff;
}}

/* Nav bar */
.nav-chapters {{
  display: flex;
  gap: 4px;
  margin-left: auto;
  margin-right: 16px;
}}
.nav-chapters a {{
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255,255,255,0.7);
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}}
.nav-chapters a:hover, .nav-chapters a.active {{
  background: rgba(255,255,255,0.15);
  color: #fff;
}}

/* Responsive */
@media (max-width: 900px) {{
  .sidebar {{
    transform: translateX(-100%);
    z-index: 500;
  }}
  .sidebar.open {{
    transform: translateX(0);
  }}
  .main-content {{
    margin-left: 0;
    padding: 0 20px 40px;
  }}
  .hero h1 {{ font-size: 26px; }}
  .nav-chapters {{ display: none; }}
  .menu-toggle {{
    display: block !important;
    background: none;
    border: none;
    color: #fff;
    font-size: 24px;
    cursor: pointer;
    margin-right: 12px;
  }}
}}
.menu-toggle {{ display: none; }}

/* Print */
@media print {{
  .header, .sidebar, .tabs, .chapter-nav, .theme-toggle, .progress-bar, .menu-toggle {{ display: none !important; }}
  .main-content {{ margin-left: 0; max-width: 100%; }}
  .card {{ break-inside: avoid; }}
  table {{ break-inside: avoid; }}
}}
</style>
</head>
<body>
<!-- Header -->
<header class="header">
  <button class="menu-toggle" onclick="toggleSidebar()">☰</button>
  <div class="logo">ACE<span>presso</span></div>
  <nav class="nav-chapters">
    <a href="ch1.html">第1章</a>
    <a class="active" href="ch2.html">第2章</a>
    <a href="ch3.html">第3章</a>
    <a href="ch4.html">第4章</a>
    <a href="ch5.html">第5章</a>
    <a href="ch6.html">第6章</a>
    <a href="ch7.html">第7章</a>
    <a href="ch8.html">第8章</a>
    <a href="ch9.html">第9章</a>
  </nav>
  <button class="theme-toggle" onclick="toggleTheme()">🌙 深色模式</button>
</header>

<!-- Progress bar -->
<div class="progress-bar" id="progressBar"></div>

<!-- Layout -->
<div class="layout">
  <!-- Sidebar -->
  <aside class="sidebar" id="sidebar">
    <h3>目录</h3>
    {toc_html}
  </aside>

  <!-- Main content -->
  <main class="main-content">
    <!-- Hero -->
    <section class="hero">
      <span class="badge">Chapter 2</span>
      <h1>{ch_title}</h1>
      <p class="subtitle">{ch_subtitle}</p>
      <p class="intro">{ch_intro}</p>
    </section>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('lecture')">讲义</button>
      <button class="tab-btn" onclick="switchTab('quiz')">自测</button>
      <button class="tab-btn" onclick="switchTab('sop')">SOP</button>
    </div>

    <!-- Lecture tab -->
    <div class="tab-content active" id="tab-lecture">
      {main_content}
    </div>

    <!-- Quiz tab -->
    <div class="tab-content" id="tab-quiz">
      <div style="padding:40px 0;text-align:center;color:var(--text-secondary);font-family:'Noto Sans SC',sans-serif;">
        <p style="font-size:18px;">本章自测题目已移除。</p>
        <p style="font-size:14px;margin-top:8px;">请在课堂中完成相关练习。</p>
      </div>
    </div>

    <!-- SOP tab -->
    <div class="tab-content" id="tab-sop">
      <div style="padding:40px 0;text-align:center;color:var(--text-secondary);font-family:'Noto Sans SC',sans-serif;">
        <p style="font-size:18px;">SOP工作单将在讲义确认后逐章制作。</p>
      </div>
    </div>

    <!-- Chapter navigation -->
    <nav class="chapter-nav">
      <a href="ch1.html">← 第1章 私人教练的角色和执业范围</a>
      <a href="ch3.html">第3章 有效的沟通、目标设定和教学技巧 →</a>
    </nav>
  </main>
</div>

<!-- Lightbox -->
<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <img id="lightboxImg" src="" alt="">
</div>

<script>
// Theme
function toggleTheme() {{
  const body = document.body;
  const btn = document.querySelector('.theme-toggle');
  if (body.getAttribute('data-theme') === 'dark') {{
    body.removeAttribute('data-theme');
    btn.textContent = '🌙 深色模式';
    localStorage.setItem('theme', 'light');
  }} else {{
    body.setAttribute('data-theme', 'dark');
    btn.textContent = '☀️ 浅色模式';
    localStorage.setItem('theme', 'dark');
  }}
}}
// Init theme
if (localStorage.getItem('theme') === 'dark') {{
  document.body.setAttribute('data-theme', 'dark');
  document.querySelector('.theme-toggle').textContent = '☀️ 浅色模式';
}}

// Tabs
function switchTab(name) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
}}

// Sidebar toggle
function toggleSidebar() {{
  document.getElementById('sidebar').classList.toggle('open');
}}

// Lightbox
function openLightbox(src) {{
  document.getElementById('lightboxImg').src = src;
  document.getElementById('lightbox').classList.add('active');
}}
function closeLightbox() {{
  document.getElementById('lightbox').classList.remove('active');
}}

// Progress bar
window.addEventListener('scroll', () => {{
  const winH = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  const pct = (window.scrollY / winH) * 100;
  document.getElementById('progressBar').style.width = pct + '%';
}});
</script>
</body>
</html>'''

# Write HTML
html_path = os.path.join(output_dir, 'ch2.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML written to: {html_path}")
print(f"File size: {os.path.getsize(html_path)} bytes")
