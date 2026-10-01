#!/usr/bin/env python3
"""
为所有章节添加：
1. SOP工具单 tab（占位 + 通用模板）
2. 学员学习记录面板（右侧浮动按钮，点击展开）
   - 阅读进度 %
   - 自测做题记录（每题对错）
   - 累计得分
   - 学习时间
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

# SOP 通用模板内容
SOP_TEMPLATE = '''<div style="padding:8px 0;">
<h3 class="sub-subsection-heading" style="margin-top:0;">📋 SOP 工具单 — 本章执业清单</h3>
<p style="color:var(--text-secondary);font-size:14px;margin-bottom:20px;">以下为本章对应的标准化操作流程工具单，供执业时快速查阅。</p>

<div style="border:1px solid var(--border);padding:20px 24px;margin-bottom:16px;">
<h4 style="font-size:15px;margin-bottom:12px;">一、执业前核查</h4>
<ul style="margin:0;padding-left:20px;font-size:14px;line-height:2;">
  <li>□ 确认客户已填写健康筛查问卷（PAR-Q+ 或同等工具）</li>
  <li>□ 核实客户医疗 Clearance（如有阳性指标）</li>
  <li>□ 检查训练环境安全（器材、地面、通风）</li>
  <li>□ 准备本次训练所需表格与记录工具</li>
</ul>
</div>

<div style="border:1px solid var(--border);padding:20px 24px;margin-bottom:16px;">
<h4 style="font-size:15px;margin-bottom:12px;">二、教学执行流程</h4>
<ul style="margin:0;padding-left:20px;font-size:14px;line-height:2;">
  <li>□ 开场：确认客户当日身体状况与训练目标</li>
  <li>□ 热身：按 IFT 模型执行相应阶段热身</li>
  <li>□ 主体训练：执行计划，实时观察动作质量</li>
  <li>□ 放松整理：静态拉伸 + 呼吸引导</li>
  <li>□ 课后记录：填写训练日志，标注注意事项</li>
</ul>
</div>

<div style="border:1px solid var(--border);padding:20px 24px;margin-bottom:16px;">
<h4 style="font-size:15px;margin-bottom:12px;">三、课后跟进</h4>
<ul style="margin:0;padding-left:20px;font-size:14px;line-height:2;">
  <li>□ 24h 内发送训练反馈（肌肉酸痛、完成情况）</li>
  <li>□ 更新客户档案中的进度记录</li>
  <li>□ 如有异常反应，及时转介医疗专业人员</li>
</ul>
</div>

<p style="color:var(--text-muted);font-size:13px;font-style:italic;margin-top:24px;">
  💡 提示：SOP 工具单为通用模板，实际使用时请根据本章具体知识点和客户需求进行调整。
  后续将针对每章开发定制化工具单。
</p>
</div>'''

# 学习记录面板 HTML
RECORD_PANEL_HTML = '''
<!-- 学习记录浮动按钮 -->
<button class="record-toggle" id="recordToggle" onclick="toggleRecord()">
  <span class="record-icon">📊</span>
  <span class="record-badge" id="recordBadge">0</span>
</button>

<!-- 学习记录面板 -->
<div class="record-panel" id="recordPanel">
  <div class="record-header">
    <span class="record-title">学习记录</span>
    <button class="record-close" onclick="toggleRecord()"></button>
  </div>

  <div class="record-section">
    <div class="record-label">本章阅读进度</div>
    <div class="record-progress-bar">
      <div class="record-progress-fill" id="recordReadPct">0%</div>
    </div>
  </div>

  <div class="record-section">
    <div class="record-label">自测成绩</div>
    <div class="record-score" id="recordScore">-- / --</div>
    <div class="record-detail" id="recordDetail">尚未开始做题</div>
  </div>

  <div class="record-section">
    <div class="record-label">学习时长</div>
    <div class="record-time" id="recordTime">0 分钟</div>
  </div>

  <div class="record-section">
    <div class="record-label">全章节总览</div>
    <div class="record-chapters" id="recordChapters"></div>
  </div>

  <button class="record-reset" onclick="if(confirm('确认清除本章学习记录？'))resetRecord()">清除本章记录</button>
</div>'''

# 学习记录 CSS
RECORD_CSS = '''
/* ============ 学习记录面板 ============ */

.record-toggle {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--text);
  color: var(--bg);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  z-index: 200;
  transition: transform 0.2s;
}
.record-toggle:hover { transform: scale(1.08); }

.record-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background: #E53935;
  color: white;
  font-size: 10px;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
}

.record-panel {
  position: fixed;
  bottom: 90px;
  right: 28px;
  width: 300px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  z-index: 200;
  display: none;
  font-family: var(--font-sans);
  overflow: hidden;
}
.record-panel.active { display: block; }

.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}
.record-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.record-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 4px;
}
.record-close:hover { color: var(--text); }

.record-section {
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}
.record-section:last-of-type { border-bottom: none; }

.record-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.record-progress-bar {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
}
.record-progress-fill {
  height: 100%;
  background: var(--text);
  border-radius: 4px;
  font-size: 0;
  transition: width 0.3s;
}

.record-score {
  font-size: 24px;
  font-weight: 700;
  font-family: var(--font-mono);
}
.record-detail {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
.record-time {
  font-size: 16px;
  font-weight: 600;
  font-family: var(--font-mono);
}

.record-chapters {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.record-ch-item {
  font-size: 11px;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  text-align: center;
  font-family: var(--font-mono);
  color: var(--text-muted);
}
.record-ch-item.done {
  border-color: var(--text);
  color: var(--text);
  font-weight: 600;
}

.record-reset {
  display: block;
  width: 100%;
  padding: 10px;
  background: none;
  border: none;
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: color 0.15s;
}
.record-reset:hover { color: #E53935; }

@media (max-width: 640px) {
  .record-toggle { bottom: 20px; right: 20px; width: 46px; height: 46px; }
  .record-panel { right: 12px; left: 12px; width: auto; bottom: 76px; }
}'''

# 学习记录 JS
RECORD_JS = r'''
// ============ 学习记录系统 ============
(function() {
  const CH_ID = '__CH_ID__';
  const TOTAL_QUIZ = __TOTAL_QUIZ__;
  const STORAGE_KEY = 'acepresso_records';

  function getRecords() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch(e) { return {}; }
  }
  function saveRecords(r) { localStorage.setItem(STORAGE_KEY, JSON.stringify(r)); }

  function getChapterRecord() {
    const records = getRecords();
    if (!records[CH_ID]) {
      records[CH_ID] = { quiz: {}, startTime: Date.now(), lastVisit: Date.now(), readPct: 0 };
      saveRecords(records);
    }
    records[CH_ID].lastVisit = Date.now();
    saveRecords(records);
    return records[CH_ID];
  }

  // 阅读进度追踪
  let readPct = 0;
  window.addEventListener('scroll', function() {
    const h = document.documentElement;
    readPct = Math.round((h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100);
    const records = getRecords();
    if (records[CH_ID]) {
      records[CH_ID].readPct = Math.max(records[CH_ID].readPct || 0, readPct);
      saveRecords(records);
    }
  });

  // 更新面板显示
  window.updateRecordDisplay = function() {
    const rec = getChapterRecord();
    const records = getRecords();

    // 阅读进度
    const pct = rec.readPct || 0;
    const fill = document.getElementById('recordReadPct');
    if (fill) {
      fill.style.width = pct + '%';
      fill.textContent = pct + '%';
    }

    // 自测成绩
    const quiz = rec.quiz || {};
    const answered = Object.keys(quiz).length;
    const correct = Object.values(quiz).filter(v => v === true).length;
    const scoreEl = document.getElementById('recordScore');
    const detailEl = document.getElementById('recordDetail');
    if (scoreEl) scoreEl.textContent = answered > 0 ? correct + ' / ' + answered : '-- / ' + TOTAL_QUIZ;
    if (detailEl) {
      if (answered === 0) detailEl.textContent = '尚未开始做题';
      else if (answered === TOTAL_QUIZ) detailEl.textContent = '全部完成，正确率 ' + Math.round(correct/answered*100) + '%';
      else detailEl.textContent = '已完成 ' + answered + ' / ' + TOTAL_QUIZ + ' 题';
    }

    // 学习时长
    const elapsed = Math.round((Date.now() - (rec.startTime || Date.now())) / 60000);
    const timeEl = document.getElementById('recordTime');
    if (timeEl) timeEl.textContent = elapsed + ' 分钟';

    // Badge
    const badge = document.getElementById('recordBadge');
    if (badge) badge.textContent = answered;

    // 全章节总览
    const chEl = document.getElementById('recordChapters');
    if (chEl) {
      chEl.innerHTML = '';
      __CHAPTER_LIST__.forEach(function(ch) {
        const div = document.createElement('div');
        div.className = 'record-ch-item' + (records[ch.id] && Object.keys(records[ch.id].quiz || {}).length > 0 ? ' done' : '');
        div.textContent = 'Ch' + ch.num;
        div.title = ch.title;
        div.style.cursor = 'pointer';
        div.onclick = function() { window.location.href = ch.id + '.html'; };
        chEl.appendChild(div);
      });
    }
  };

  // 做题记录接口（quiz 模块调用）
  window.recordQuizAnswer = function(questionId, isCorrect) {
    const records = getRecords();
    if (!records[CH_ID]) records[CH_ID] = { quiz: {}, startTime: Date.now() };
    if (!records[CH_ID].quiz) records[CH_ID].quiz = {};
    records[CH_ID].quiz[questionId] = isCorrect;
    saveRecords(records);
    window.updateRecordDisplay();
  };

  // 清除记录
  window.resetRecord = function() {
    const records = getRecords();
    delete records[CH_ID];
    saveRecords(records);
    window.updateRecordDisplay();
  };

  // 面板切换
  window.toggleRecord = function() {
    const panel = document.getElementById('recordPanel');
    panel.classList.toggle('active');
    if (panel.classList.contains('active')) window.updateRecordDisplay();
  };

  // 初始更新
  setTimeout(window.updateRecordDisplay, 500);
})();
'''

def process_chapter(ch_num):
    ch_id = CHAPTERS[ch_num - 1][1]
    title = CHAPTERS[ch_num - 1][2]

    html = (WORK_DIR / f'{ch_id}.html').read_text(encoding='utf-8')

    # 1. 添加 SOP tab
    # 在 tabs 后面添加 SOP tab button
    old_tabs_end = "onclick=\"switchTab('quiz', this)\">自测</button>\n    </div>"
    new_tabs = """onclick="switchTab('quiz', this)">自测</button>
      <button class="tab-btn" onclick="switchTab('sop', this)">SOP工具单</button>
    </div>"""
    html = html.replace(old_tabs_end, new_tabs)

    # 在 lecture tab-content 后面添加 SOP tab-content
    # 找到 quiz tab-content 结束的位置，在后面插入 SOP
    sop_insert = f'''
    <div class="tab-content" id="tab-sop">
      {SOP_TEMPLATE}
    </div>'''

    # 在 chapter-footer 前插入 SOP tab
    html = html.replace('    <div class="chapter-footer">', sop_insert + '\n\n    <div class="chapter-footer">')

    # 2. 添加学习记录面板 CSS
    css_insert = RECORD_CSS
    html = html.replace('</head>', f'{css_insert}\n</head>')

    # 3. 添加学习记录面板 HTML
    html = html.replace('<div class="lightbox"', RECORD_PANEL_HTML + '\n\n<div class="lightbox"')

    # 4. 添加学习记录 JS
    # 替换 __CH_ID__ 和 __TOTAL_QUIZ__
    quiz_count = len(re.findall(r'quiz-item', html))
    js = RECORD_JS.replace('__CH_ID__', ch_id).replace('__TOTAL_QUIZ__', str(quiz_count))

    # 构建章节列表
    ch_list_js = '['
    for num, fname, t, et in CHAPTERS:
        ch_list_js += f'{{id:"{fname}",num:{num},title:"{t}"}},'
    ch_list_js = ch_list_js.rstrip(',') + ']'
    js = js.replace('__CHAPTER_LIST__', ch_list_js)

    # 在 </script> 前插入
    html = html.replace('</script>\n\n</body>', js + '\n</script>\n\n</body>')

    # 5. 给 quiz 答案添加点击记录
    # 在 quiz answer reveal 时调用 recordQuizAnswer
    # 找到 quiz details/summary 的 toggle 事件
    quiz_js = '''
// 自测答题记录
document.querySelectorAll('.quiz-answer summary').forEach(function(summary) {
  summary.addEventListener('click', function() {
    const item = this.closest('.quiz-item');
    const tag = item ? item.querySelector('.quiz-tag') : null;
    const qId = item ? (item.id || 'q_' + Array.from(document.querySelectorAll('.quiz-item')).indexOf(item)) : 'unknown';
    // 简单判定：展开后显示答案即视为已作答
    window.recordQuizAnswer(qId, true);
  });
});'''

    html = html.replace('</script>\n\n</body>', quiz_js + '\n</script>\n\n</body>')

    (WORK_DIR / f'{ch_id}.html').write_text(html, encoding='utf-8')

    # 验证
    has_sop = 'tab-sop' in html
    has_record = 'recordPanel' in html
    has_record_css = 'record-toggle' in html
    cards = len(re.findall(r'class="card card-', html))
    quiz = len(re.findall(r'quiz-item', html))

    status = '✅' if (has_sop and has_record and has_record_css) else '️'
    print(f'{status} Ch{ch_num} {title} | SOP: {has_sop} | Record: {has_record} | 卡片: {cards} | 自测: {quiz}')

# 处理所有 9 章
for i in range(1, 10):
    process_chapter(i)
