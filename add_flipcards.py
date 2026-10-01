#!/usr/bin/env python3
"""
修复 + 新增：
1. 修复学习记录面板显示问题（确保按钮可见）
2. 新增「知识翻卡」tab：从各章知识卡片提取问答对，做成交互翻转卡片
3. SOP 工具单保留占位（后续逐章提炼）
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

# ============ 翻卡 CSS ============
FLIP_CARD_CSS = '''
/* ============ 知识翻卡 ============ */
.flipcard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  padding: 8px 0 32px;
}
.flipcard {
  perspective: 1000px;
  height: 200px;
  cursor: pointer;
}
.flipcard-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.5s;
  transform-style: preserve-3d;
}
.flipcard.flipped .flipcard-inner {
  transform: rotateY(180deg);
}
.flipcard-front, .flipcard-back {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.flipcard-front {
  background: var(--surface);
}
.flipcard-back {
  background: var(--text);
  color: var(--bg);
  transform: rotateY(180deg);
}
.flipcard-type {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 3px 8px;
  display: inline-block;
  margin-bottom: 12px;
  border: 1px solid;
  align-self: flex-start;
}
.flipcard-type.know { color: #4CAF50; border-color: #4CAF50; }
.flipcard-type.avoid { color: #D32F2F; border-color: #D32F2F; }
.flipcard-type.dothis { color: #1565C0; border-color: #1565C0; }
.flipcard-type.caution { color: #E65100; border-color: #E65100; }
.flipcard-type.scene { color: #7B1FA2; border-color: #7B1FA2; }
.flipcard-front .flipcard-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text);
  flex: 1;
}
.flipcard-back .flipcard-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--bg);
  flex: 1;
}
.flipcard-hint {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  margin-top: 8px;
  font-family: var(--font-mono);
}
.flipcard-back .flipcard-hint {
  color: rgba(255,255,255,0.5);
}
.flipcard-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  font-family: var(--font-sans);
}
.flipcard-count {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.flipcard-nav-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 16px;
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  transition: all 0.15s;
}
.flipcard-nav-btn:hover {
  border-color: var(--text);
}
'''

# ============ 翻卡 JS ============
FLIP_CARD_JS = r'''
// ============ 知识翻卡 ============
(function() {
  document.querySelectorAll('.flipcard').forEach(function(card) {
    card.addEventListener('click', function() {
      this.classList.toggle('flipped');
    });
  });

  // 翻卡答题记录
  document.querySelectorAll('.flipcard').forEach(function(card, idx) {
    card.addEventListener('click', function() {
      if (this.classList.contains('flipped')) {
        window.recordQuizAnswer && window.recordQuizAnswer('flip_' + idx, true);
      }
    });
  });
})();
'''

def extract_flashcards_from_chapter(html_content):
    """从章节HTML中提取知识卡片，生成翻卡数据"""
    soup = BeautifulSoup(html_content, 'html.parser')
    cards = []

    type_map = {
        'card-tip': ('know', 'KNOW', '知识要点'),
        'card-wrong': ('avoid', 'AVOID', '错误做法'),
        'card-right': ('dothis', 'DO THIS', '正确做法'),
        'card-warn': ('caution', 'CAUTION', '常见误区'),
        'card-scene': ('scene', 'SCENE', '典型场景'),
    }

    for card_div in soup.find_all('div', class_=re.compile(r'card card-')):
        classes = card_div.get('class', [])
        card_type = None
        for cls in classes:
            if cls.startswith('card-') and cls != 'card':
                card_type = cls
                break

        if card_type not in type_map:
            continue

        css_class, label_en, label_cn = type_map[card_type]

        # 提取内容
        label_span = card_div.find('span', class_='card-label')
        label_text = label_span.get_text(strip=True) if label_span else label_cn

        # 获取所有段落文本
        paragraphs = card_div.find_all('p')
        content = ' '.join([p.get_text(strip=True) for p in paragraphs])

        if not content:
            continue

        # 生成问答对
        # 正面：类型标签 + 场景/问题
        # 背面：要点/答案
        if card_type == 'card-scene':
            front = content  # 场景描述
            back = "（详见讲义正文中的正确做法和错误做法）"
        elif card_type == 'card-wrong':
            front = f"❌ {content}"
            back = "（正确做法见 DO THIS 卡片）"
        elif card_type == 'card-right':
            front = f"✅ {content}"
            back = "（这是推荐的标准做法）"
        elif card_type == 'card-warn':
            front = f"⚠ {content}"
            back = "（注意避免这个常见误区）"
        else:
            front = content
            back = "（核心知识点，请牢记）"

        cards.append({
            'type_css': css_class,
            'label': label_en,
            'front': front[:200],
            'back': back[:200],
        })

    return cards

def build_flipcard_html(cards):
    """生成翻卡 HTML"""
    if not cards:
        return '<p style="color:var(--text-muted);font-size:14px;padding:32px 0;">本章暂无翻卡内容。</p>'

    html = '<div class="flipcard-nav">'
    html += f'<span class="flipcard-count">共 {len(cards)} 张卡片 · 点击翻转</span>'
    html += '<div><button class="flipcard-nav-btn" onclick="flipAll(true)">全部翻开</button> '
    html += '<button class="flipcard-nav-btn" onclick="flipAll(false)">全部合上</button></div>'
    html += '</div>'
    html += '<div class="flipcard-grid">'

    for card in cards:
        html += f'''
<div class="flipcard">
  <div class="flipcard-inner">
    <div class="flipcard-front">
      <span class="flipcard-type {card['type_css']}">{card['label']}</span>
      <div class="flipcard-text">{card['front']}</div>
      <div class="flipcard-hint">点击翻转 →</div>
    </div>
    <div class="flipcard-back">
      <span class="flipcard-type {card['type_css']}" style="border-color:rgba(255,255,255,0.3);color:rgba(255,255,255,0.7);">{card['label']}</span>
      <div class="flipcard-text">{card['back']}</div>
      <div class="flipcard-hint">← 点击翻回</div>
    </div>
  </div>
</div>'''

    html += '</div>'
    return html

def process_chapter(ch_num):
    ch_id = CHAPTERS[ch_num - 1][1]
    title = CHAPTERS[ch_num - 1][2]

    html = (WORK_DIR / f'{ch_id}.html').read_text(encoding='utf-8')

    # 1. 添加翻卡 CSS
    if 'flipcard-grid' not in html:
        html = html.replace('</head>', f'{FLIP_CARD_CSS}\n</head>')

    # 2. 添加翻卡 tab button
    if "switchTab('flip', this)" not in html:
        html = html.replace(
            "onclick=\"switchTab('sop', this)\">SOP工具单</button>",
            "onclick=\"switchTab('flip', this)\">知识翻卡</button>\n      <button class=\"tab-btn\" onclick=\"switchTab('sop', this)\">SOP工具单</button>"
        )

    # 3. 提取翻卡数据并生成 HTML
    cards = extract_flashcards_from_chapter(html)
    flipcard_html = build_flipcard_html(cards)

    # 4. 添加翻卡 tab content
    flip_tab = f'''
    <div class="tab-content" id="tab-flip">
      <h3 class="sub-subsection-heading" style="margin-top:0;">📇 知识翻卡 — {title}</h3>
      <p style="color:var(--text-secondary);font-size:14px;margin-bottom:20px;">点击卡片翻转查看要点。正面为场景/问题，背面为核心知识点。</p>
      {flipcard_html}
    </div>'''

    # 在 SOP tab 前插入翻卡 tab
    if 'id="tab-flip"' not in html:
        html = html.replace('<div class="tab-content" id="tab-sop">', flip_tab + '\n\n    <div class="tab-content" id="tab-sop">')

    # 5. 添加翻卡 JS
    if 'flipcard-inner' not in html.split('</script>')[0] if '</script>' in html else True:
        html = html.replace('</script>\n\n</body>', FLIP_CARD_JS + '\n</script>\n\n</body>')

    # 6. 确保翻卡全部翻开/合上功能
    flip_all_js = r'''
function flipAll(state) {
  document.querySelectorAll('.flipcard').forEach(function(card) {
    if (state) card.classList.add('flipped');
    else card.classList.remove('flipped');
  });
}'''
    if 'flipAll' not in html:
        html = html.replace('</script>\n\n</body>', flip_all_js + '\n</script>\n\n</body>')

    (WORK_DIR / f'{ch_id}.html').write_text(html, encoding='utf-8')

    # 验证
    has_flip_tab = 'tab-flip' in html
    has_flip_css = 'flipcard-grid' in html
    has_flip_js = 'flipcard-inner' in html
    card_count = len(cards)

    print(f'✅ Ch{ch_num} {title} | 翻卡: {card_count}张 | Tab: {has_flip_tab} | CSS: {has_flip_css} | JS: {has_flip_js}')

# 处理所有 9 章
for i in range(1, 10):
    process_chapter(i)
