import json, re, os

output_dir = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"

with open(os.path.join(output_dir, '_ch2_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

content_blocks = data['content_blocks']
headings = data['headings']
table_count = data['table_count']

def he(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def classify_card(text):
    t = text.strip()
    # 要点
    if t.startswith('\u8981\u70b9\uff1a') or t.startswith('\u8981\u70b9:'):
        sep = '\uff1a' if '\uff1a' in t[:5] else ':'
        return 'card-tip', '\u8981\u70b9', t.split(sep, 1)[1]
    # 错误做法
    if re.match(r'^\u274c\s*\u9519\u8bef\u505a\u6cd5', t):
        c = re.split(r'[\uff1a:]', t, 1)[1] if re.search(r'[\uff1a:]', t) else t
        return 'card-wrong', '\u2717 \u9519\u8bef', c
    # 正确做法
    if re.match(r'^\u2713\s*\u6b63\u786e\u505a\u6cd5', t):
        c = re.split(r'[\uff1a:]', t, 1)[1] if re.search(r'[\uff1a:]', t) else t
        return 'card-right', '\u2713 \u6b63\u786e', c
    # 误区
    if re.match(r'^(\u5e38\u89c1)?\u8bef\u533a[\uff1a:]', t):
        c = re.split(r'[\uff1a:]', t, 1)[1]
        return 'card-warn', '\u26a0 \u8bef\u533a', c
    # 场景
    if t.startswith('\u573a\u666f\uff1a') or t.startswith('\u573a\u666f:'):
        c = re.split(r'[\uff1a:]', t, 1)[1]
        return 'card-scene', '\U0001f4cb \u573a\u666f', c
    # 记忆提示/口诀
    if re.match(r'^\u8bb0\u5fc6(\u63d0\u793a|\u53e3\u8bc0)[\uff1a:]', t):
        c = re.split(r'[\uff1a:]', t, 1)[1]
        return 'card-memory', '\U0001f9e0 \u8bb0\u5fc6', c
    # 教练小tips with content
    if re.match(r'^\U0001f3af\s*\u6559\u7ec3\u5c0f[Tt]ips[\uff1a:]', t):
        c = re.split(r'[\uff1a:]', t, 1)[1]
        return 'card-tip', '\U0001f4a1 \u6559\u7ec3\u63d0\u793a', c
    return None, None, t

def render_block(text, images):
    card_class, label, content = classify_card(text)
    img_html = ''
    for img in (images or []):
        img_html += '<img src="images/' + img + '" class="inline-img" loading="lazy" onclick="openLightbox(this.src)">'
    if card_class:
        return '<div class="card ' + card_class + '"><span class="card-label">' + he(label) + '</span><p>' + he(content) + img_html + '</p></div>'
    else:
        p_content = he(text)
        if img_html:
            p_content += img_html
        return '<p>' + p_content + '</p>'

def render_table(rows):
    if not rows:
        return ''
    html = '<table>\n'
    for i, row in enumerate(rows):
        html += '<tr>\n'
        tag = 'th' if i == 0 else 'td'
        for cell in row:
            cell_html = he(cell).replace('\n', '<br>')
            html += '  <' + tag + '>' + cell_html + '</' + tag + '>\n'
        html += '</tr>\n'
    html += '</table>'
    return html

# Build TOC
toc_lines = ['<ul class="toc-list">']
for level, text, hid in headings:
    indent = (level - 2) * 16
    toc_lines.append('<li style="padding-left:' + str(indent) + 'px"><a href="#' + hid + '">' + he(text) + '</a></li>')
toc_lines.append('</ul>')
toc_html = '\n'.join(toc_lines)

# Build main content
parts = []
for block in content_blocks:
    if block['type'] == 'table':
        parts.append(render_table(block['rows']))
    elif block['type'] == 'images_only':
        for img in block['images']:
            parts.append('<figure><img src="images/' + img + '" loading="lazy" onclick="openLightbox(this.src)"></figure>')
    elif block['type'] == 'text':
        text = block['text']
        style = block.get('style', '')
        images = block.get('images', [])

        # Skip residual empty scaffold markers
        stripped = text.strip().lower().replace(' ', '').replace('\u3000', '')
        skip_exact = [
            '\U0001f4a1\u8bb0\u5fc6\u6280\u5de7',  # 💡记忆技巧
            '\U0001f4a1\u5173\u952e\u601d\u8003',  # 💡关键思考
            '\U0001f4a1\u7ae0\u8282\u5c0f\u8282',  # 💡章节小节
            '\U0001f4da\u8bb0\u5fc6\u6280\u5de7',  # 📚记忆技巧
            '\U0001f3af\u6559\u7ec3\u5c0ftips',     # 🎯教练小tips
            '\u3010\u8bb0\u5fc6\u6280\u5de7\u3011',  # 【记忆技巧】
            '\u270d\ufe0f\u5c0f\u8282\u56de\u987e',  # ✍️小节回顾
        ]
        if stripped in skip_exact:
            continue

        # Render heading or paragraph
        if 'heading_level' in block and 'heading_id' in block:
            level = block['heading_level']
            hid = block['heading_id']
            tag = 'h' + str(level)
            parts.append('<' + tag + ' id="' + hid + '">' + he(text) + '</' + tag + '>')
        else:
            parts.append(render_block(text, images))

main_content = '\n'.join(parts)

ch_intro = (
    '\u672c\u7ae0\u7cfb\u7edf\u68b3\u7406\u884c\u4e3a\u6539\u53d8\u7684\u7406\u8bba\u6a21\u578b'
    '\uff08\u5065\u5eb7\u4fe1\u5ff5\u6a21\u578b\u3001\u81ea\u6211\u51b3\u5b9a\u7406\u8bba\u3001\u8de8\u7406\u8bba\u6a21\u578b\uff09\u3001'
    '\u5e95\u5c42\u539f\u7406\uff08\u64cd\u4f5c\u6027\u6761\u4ef6\u53cd\u5c04\u4e0e\u8ba4\u77e5\u884c\u4e3a\uff09'
    '\u4ee5\u53ca\u5f71\u54cd\u8fd0\u52a8\u575a\u6301\u7684\u5173\u952e\u56e0\u7d20\u3002'
    '\u7406\u89e3\u8fd9\u4e9b\u5185\u5bb9\u662f\u79c1\u4eba\u6559\u7ec3\u5e2e\u52a9\u5ba2\u6237'
    '\u4ece\u201c\u5f00\u59cb\u8fd0\u52a8\u201d\u8d70\u5411\u201c\u575a\u6301\u8fd0\u52a8\u201d\u7684\u77e5\u8bc6\u57fa\u7840\u3002'
)

css = """
:root {
  --bg: #fafafa; --bg-card: #ffffff; --text: #1a1a1a; --text-secondary: #555;
  --border: #e0e0e0; --accent: #2e7d32; --accent-light: #e8f5e9;
  --header-bg: #1b5e20; --sidebar-bg: #f5f5f5; --table-header: #2e7d32;
  --table-stripe: #f5f5f5; --shadow: 0 2px 8px rgba(0,0,0,0.08);
}
[data-theme="dark"] {
  --bg: #121212; --bg-card: #1e1e1e; --text: #e0e0e0; --text-secondary: #aaa;
  --border: #333; --accent: #66bb6a; --accent-light: #1b3a1e;
  --header-bg: #0d3010; --sidebar-bg: #1a1a1a; --table-header: #1b5e20;
  --table-stripe: #252525; --shadow: 0 2px 8px rgba(0,0,0,0.3);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:"Noto Serif SC","Source Han Serif CN",-apple-system,serif; background:var(--bg); color:var(--text); line-height:1.8; font-size:16px; transition:background .3s,color .3s; }
.header { position:fixed; top:0; left:0; right:0; height:56px; background:var(--header-bg); color:#fff; display:flex; align-items:center; justify-content:space-between; padding:0 24px; z-index:1000; box-shadow:0 2px 4px rgba(0,0,0,.2); }
.header .logo { font-family:"Noto Sans SC",sans-serif; font-size:20px; font-weight:700; letter-spacing:1px; }
.header .logo span { color:#a5d6a7; }
.theme-toggle { background:none; border:1px solid rgba(255,255,255,.3); color:#fff; padding:6px 14px; border-radius:20px; cursor:pointer; font-size:13px; transition:all .2s; }
.theme-toggle:hover { background:rgba(255,255,255,.1); }
.nav-chapters { display:flex; gap:4px; margin-left:auto; margin-right:16px; }
.nav-chapters a { font-family:"Noto Sans SC",sans-serif; font-size:11px; color:rgba(255,255,255,.7); text-decoration:none; padding:4px 8px; border-radius:4px; transition:all .2s; }
.nav-chapters a:hover,.nav-chapters a.active { background:rgba(255,255,255,.15); color:#fff; }
.progress-bar { position:fixed; top:56px; left:0; height:3px; background:var(--accent); z-index:999; transition:width .1s; }
.layout { display:flex; margin-top:56px; min-height:calc(100vh - 56px); }
.sidebar { width:280px; min-width:280px; background:var(--sidebar-bg); border-right:1px solid var(--border); padding:20px 16px; position:fixed; top:56px; bottom:0; overflow-y:auto; transition:transform .3s; }
.sidebar h3 { font-family:"Noto Sans SC",sans-serif; font-size:13px; text-transform:uppercase; color:var(--text-secondary); margin-bottom:12px; letter-spacing:1px; }
.toc-list { list-style:none; }
.toc-list li { margin:2px 0; }
.toc-list a { display:block; padding:5px 10px; color:var(--text-secondary); text-decoration:none; font-size:13px; font-family:"Noto Sans SC",sans-serif; border-radius:4px; transition:all .2s; line-height:1.4; }
.toc-list a:hover { background:var(--accent-light); color:var(--accent); }
.main-content { flex:1; margin-left:280px; max-width:900px; padding:0 40px 60px; }
.hero { padding:48px 0 32px; border-bottom:1px solid var(--border); margin-bottom:32px; }
.hero .badge { display:inline-block; background:var(--accent); color:#fff; font-family:"Noto Sans SC",sans-serif; font-size:12px; font-weight:600; padding:4px 12px; border-radius:12px; margin-bottom:12px; }
.hero h1 { font-family:"Noto Sans SC",sans-serif; font-size:32px; font-weight:700; color:var(--text); margin-bottom:8px; line-height:1.3; }
.hero .subtitle { font-family:"Noto Sans SC",sans-serif; font-size:16px; color:var(--text-secondary); margin-bottom:16px; font-style:italic; }
.hero .intro { font-size:15px; color:var(--text-secondary); line-height:1.8; max-width:680px; }
.tabs { display:flex; gap:0; border-bottom:2px solid var(--border); margin-bottom:32px; }
.tab-btn { font-family:"Noto Sans SC",sans-serif; font-size:14px; padding:10px 20px; background:none; border:none; color:var(--text-secondary); cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-2px; transition:all .2s; }
.tab-btn.active { color:var(--accent); border-bottom-color:var(--accent); font-weight:600; }
.tab-content { display:none; }
.tab-content.active { display:block; }
h2 { font-family:"Noto Sans SC",sans-serif; font-size:26px; font-weight:700; color:var(--text); margin:48px 0 20px; padding-bottom:10px; border-bottom:3px solid var(--accent); line-height:1.3; }
h3 { font-family:"Noto Sans SC",sans-serif; font-size:20px; font-weight:600; color:var(--text); margin:32px 0 16px; padding-left:14px; border-left:4px solid var(--accent); line-height:1.4; }
h4 { font-family:"Noto Sans SC",sans-serif; font-size:17px; font-weight:600; color:var(--text); margin:24px 0 12px; line-height:1.4; }
h5 { font-family:"Noto Sans SC",sans-serif; font-size:15px; font-weight:600; color:var(--text-secondary); margin:20px 0 10px; line-height:1.4; }
p { margin:12px 0; font-size:16px; line-height:1.8; color:var(--text); }
.card { margin:16px 0; padding:14px 18px; border-radius:8px; border-left:4px solid; }
.card .card-label { font-weight:700; font-size:13px; display:block; margin-bottom:6px; font-family:"Noto Sans SC",sans-serif; }
.card p { margin:0; font-size:15px; line-height:1.7; }
.card-tip { background:#e8f5e9; border-color:#4caf50; } .card-tip .card-label { color:#2e7d32; }
.card-wrong { background:#fce4ec; border-color:#e53935; } .card-wrong .card-label { color:#c62828; }
.card-right { background:#e3f2fd; border-color:#1e88e5; } .card-right .card-label { color:#1565c0; }
.card-warn { background:#fff8e1; border-color:#ff8f00; } .card-warn .card-label { color:#e65100; }
.card-scene { background:#f3e5f5; border-color:#7b1fa2; } .card-scene .card-label { color:#6a1b9a; }
.card-memory { background:#f5f5f5; border-color:#9e9e9e; } .card-memory .card-label { color:#616161; } .card-memory p { font-size:13.5px; color:#555; }
[data-theme="dark"] .card-tip { background:#1b3a1e; }
[data-theme="dark"] .card-wrong { background:#3a1b1b; }
[data-theme="dark"] .card-right { background:#1b2a3a; }
[data-theme="dark"] .card-warn { background:#3a2e1b; }
[data-theme="dark"] .card-scene { background:#2e1b3a; }
[data-theme="dark"] .card-memory { background:#252525; }
table { width:100%; border-collapse:collapse; margin:20px 0; font-size:14px; font-family:"Noto Sans SC",sans-serif; box-shadow:var(--shadow); border-radius:8px; overflow:hidden; }
th { background:var(--table-header); color:#fff; padding:12px 14px; text-align:left; font-weight:600; font-size:13px; }
td { padding:10px 14px; border-bottom:1px solid var(--border); vertical-align:top; }
tr:nth-child(even) td { background:var(--table-stripe); }
figure { margin:24px 0; text-align:center; }
.inline-img,figure img { max-width:100%; height:auto; border-radius:8px; box-shadow:var(--shadow); cursor:pointer; transition:transform .2s; }
.inline-img:hover,figure img:hover { transform:scale(1.02); }
.lightbox { display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,.9); z-index:2000; justify-content:center; align-items:center; cursor:pointer; }
.lightbox.active { display:flex; }
.lightbox img { max-width:90vw; max-height:90vh; object-fit:contain; border-radius:4px; }
.chapter-nav { display:flex; justify-content:space-between; margin:48px 0 24px; padding:20px 0; border-top:1px solid var(--border); }
.chapter-nav a { font-family:"Noto Sans SC",sans-serif; font-size:14px; color:var(--accent); text-decoration:none; padding:8px 16px; border:1px solid var(--accent); border-radius:6px; transition:all .2s; }
.chapter-nav a:hover { background:var(--accent); color:#fff; }
@media (max-width:900px) {
  .sidebar { transform:translateX(-100%); z-index:500; }
  .sidebar.open { transform:translateX(0); }
  .main-content { margin-left:0; padding:0 20px 40px; }
  .hero h1 { font-size:26px; }
  .nav-chapters { display:none; }
  .menu-toggle { display:block !important; background:none; border:none; color:#fff; font-size:24px; cursor:pointer; margin-right:12px; }
}
.menu-toggle { display:none; }
@media print {
  .header,.sidebar,.tabs,.chapter-nav,.theme-toggle,.progress-bar,.menu-toggle { display:none !important; }
  .main-content { margin-left:0; max-width:100%; }
  .card,table { break-inside:avoid; }
}
"""

js = """
function toggleTheme(){var b=document.body,n=document.querySelector('.theme-toggle');if(b.getAttribute('data-theme')==='dark'){b.removeAttribute('data-theme');n.textContent='\\ud83c\\udf19 深色模式';localStorage.setItem('theme','light')}else{b.setAttribute('data-theme','dark');n.textContent='\\u2600\\ufe0f 浅色模式';localStorage.setItem('theme','dark')}}
if(localStorage.getItem('theme')==='dark'){document.body.setAttribute('data-theme','dark');document.querySelector('.theme-toggle').textContent='\\u2600\\ufe0f 浅色模式'}
function switchTab(n){document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.remove('active')});document.querySelectorAll('.tab-content').forEach(function(c){c.classList.remove('active')});event.target.classList.add('active');document.getElementById('tab-'+n).classList.add('active')}
function toggleSidebar(){document.getElementById('sidebar').classList.toggle('open')}
function openLightbox(s){document.getElementById('lightboxImg').src=s;document.getElementById('lightbox').classList.add('active')}
function closeLightbox(){document.getElementById('lightbox').classList.remove('active')}
window.addEventListener('scroll',function(){var h=document.documentElement.scrollHeight-document.documentElement.clientHeight;document.getElementById('progressBar').style.width=(window.scrollY/h*100)+'%'})
"""

# Assemble full HTML
html = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
html += '<meta charset="UTF-8">\n'
html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
html += '<title>第2章 行为改变的基础 | ACEpresso</title>\n'
html += '<style>' + css + '</style>\n'
html += '</head>\n<body>\n'

# Header
html += '<header class="header">\n'
html += '<button class="menu-toggle" onclick="toggleSidebar()">&#9776;</button>\n'
html += '<div class="logo">ACE<span>presso</span></div>\n'
html += '<nav class="nav-chapters">\n'
for ch_num in range(1, 10):
    active = ' class="active"' if ch_num == 2 else ''
    html += f'<a{active} href="ch{ch_num}.html">第{ch_num}章</a>\n'
html += '</nav>\n'
html += '<button class="theme-toggle" onclick="toggleTheme()">&#127769; 深色模式</button>\n'
html += '</header>\n'

# Progress bar
html += '<div class="progress-bar" id="progressBar"></div>\n'

# Layout
html += '<div class="layout">\n'

# Sidebar
html += '<aside class="sidebar" id="sidebar">\n'
html += '<h3>目录</h3>\n'
html += toc_html + '\n'
html += '</aside>\n'

# Main content
html += '<main class="main-content">\n'

# Hero
html += '<section class="hero">\n'
html += '<span class="badge">Chapter 2</span>\n'
html += '<h1>行为改变的基础</h1>\n'
html += '<p class="subtitle">Foundations of Behavior Change</p>\n'
html += '<p class="intro">' + ch_intro + '</p>\n'
html += '</section>\n'

# Tabs
html += '<div class="tabs">\n'
html += '<button class="tab-btn active" onclick="switchTab(\'lecture\')">讲义</button>\n'
html += '<button class="tab-btn" onclick="switchTab(\'quiz\')">自测</button>\n'
html += '<button class="tab-btn" onclick="switchTab(\'sop\')">SOP</button>\n'
html += '</div>\n'

# Tab contents
html += '<div class="tab-content active" id="tab-lecture">\n'
html += main_content + '\n'
html += '</div>\n'

html += '<div class="tab-content" id="tab-quiz">\n'
html += '<div style="padding:40px 0;text-align:center;color:var(--text-secondary);font-family:\'Noto Sans SC\',sans-serif;">\n'
html += '<p style="font-size:18px;">本章自测题目已移除。</p>\n'
html += '<p style="font-size:14px;margin-top:8px;">请在课堂中完成相关练习。</p>\n'
html += '</div></div>\n'

html += '<div class="tab-content" id="tab-sop">\n'
html += '<div style="padding:40px 0;text-align:center;color:var(--text-secondary);font-family:\'Noto Sans SC\',sans-serif;">\n'
html += '<p style="font-size:18px;">SOP工作单将在讲义确认后逐章制作。</p>\n'
html += '</div></div>\n'

# Chapter nav
html += '<nav class="chapter-nav">\n'
html += '<a href="ch1.html">&larr; 第1章 私人教练的角色和执业范围</a>\n'
html += '<a href="ch3.html">第3章 有效的沟通、目标设定和教学技巧 &rarr;</a>\n'
html += '</nav>\n'

html += '</main>\n</div>\n'

# Lightbox
html += '<div class="lightbox" id="lightbox" onclick="closeLightbox()">\n'
html += '<img id="lightboxImg" src="" alt="">\n'
html += '</div>\n'

# Script
html += '<script>' + js + '</script>\n'
html += '</body>\n</html>'

# Write
html_path = os.path.join(output_dir, 'ch2.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML written: {os.path.getsize(html_path)} bytes")
print(f"TOC entries: {len(headings)}")
print(f"Tables in HTML: {html.count('<table>')}")
print(f"Images in HTML: {html.count('<img ')}")
