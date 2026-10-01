#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

BASE = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"

CSS_BLOCK = r"""
.flipcard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  padding: 8px 0;
}
.flipcard {
  perspective: 800px;
  height: 200px;
  cursor: pointer;
}
.flipcard-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
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
  -webkit-backface-visibility: hidden;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  box-sizing: border-box;
}
.flipcard-front {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
}
.flipcard-front .fc-num {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  opacity: 0.7;
  margin-bottom: 12px;
}
.flipcard-front .fc-question {
  font-size: 14px;
  line-height: 1.7;
  font-weight: 500;
}
.flipcard-front .fc-hint {
  font-size: 11px;
  opacity: 0.5;
  margin-top: 12px;
}
.flipcard-back {
  background: #f8f9fa;
  color: var(--text-primary, #1a1a2e);
  border: 2px solid #667eea;
  transform: rotateY(180deg);
}
.flipcard-back .fc-answer {
  font-size: 13px;
  line-height: 1.8;
}
[data-theme="dark"] .flipcard-back {
  background: #1e1e2e;
  color: #e0e0e0;
}
[data-theme="dark"] .flipcard-front {
  background: linear-gradient(135deg, #4a5568 0%, #553c7b 100%);
}
.fc-header {
  margin-bottom: 24px;
}
.fc-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
  margin: 0 0 8px 0;
}
.fc-header p {
  font-size: 14px;
  color: var(--text-secondary, #666);
  margin: 0;
}
.fc-counter {
  display: inline-block;
  background: #667eea;
  color: #fff;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-top: 12px;
}
.fc-reset-btn {
  display: inline-block;
  margin-top: 20px;
  padding: 8px 20px;
  background: none;
  border: 1px solid var(--border, #ddd);
  border-radius: 6px;
  color: var(--text-secondary, #666);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.fc-reset-btn:hover {
  border-color: #667eea;
  color: #667eea;
}
.fc-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border, #eee);
}
@media (max-width: 600px) {
  .flipcard-grid { grid-template-columns: 1fr; }
  .flipcard { height: 220px; }
}
@media print {
  .flipcard { height: auto; perspective: none; }
  .flipcard-inner { transform: none !important; transform-style: flat; }
  .flipcard-back { display: none; }
  .flipcard-front {
    position: relative;
    background: #f0f0f0 !important;
    color: #333 !important;
    border: 1px solid #ccc;
  }
  .flipcard-front::after {
    content: attr(data-answer);
    display: block;
    margin-top: 12px;
    font-size: 13px;
    color: #555;
    font-weight: normal;
  }
}"""

JS_BLOCK = """
function flipCard(card) {
  card.classList.toggle('flipped');
  updateFlipCounter(card);
}
function updateFlipCounter(card) {
  var container = card.closest('.tab-content');
  if (!container) return;
  var all = container.querySelectorAll('.flipcard');
  var flipped = container.querySelectorAll('.flipcard.flipped');
  var counter = container.querySelector('.fc-counter');
  if (counter) counter.textContent = '\u5df2\u7ffb\u8f6c: ' + flipped.length + '/' + all.length;
}
function resetFlipcards(btn) {
  var container = btn.closest('.tab-content');
  if (!container) return;
  container.querySelectorAll('.flipcard').forEach(function(c) { c.classList.remove('flipped'); });
  var counter = container.querySelector('.fc-counter');
  var all = container.querySelectorAll('.flipcard');
  if (counter) counter.textContent = '\u5df2\u7ffb\u8f6c: 0/' + all.length;
}
"""

ch3_cards = [
    ("建立良好客户关系的核心要素是什么？", "真诚、共情、尊重、积极倾听、非评判态度。"),
    ("积极倾听的四个技巧是什么？", "①注视对方 ②适时的语言回应（嗯、对）③身体前倾 ④复述对方观点确认理解。"),
    ("非语言沟通包括哪些要素？", "面部表情、眼神接触、身体姿态、手势、空间距离、语调语速。"),
    ("如何根据客户的学习风格调整教学方法？", "视觉型：多用图示、示范、视频；听觉型：口头讲解、讨论；动觉型：实际操作、体验式学习。"),
    ("动作示范的最佳顺序是什么？", "正面示范→侧面示范→背面示范，慢速→正常速度，分解→完整。"),
    ("给予反馈的\u201c三明治法\u201d是什么？", "先肯定做得好的部分→指出需要改进的地方→鼓励再次尝试。"),
    ("如何帮助客户设定有效的短期目标？", "将长期目标拆解为可量化、可达成的小步骤，每1-2周设定一个里程碑，完成后及时庆祝。"),
    ("动机性访谈的五个核心原则是什么？", "①表达共情 ②发展不一致感 ③避免争辩 ④顺应阻抗 ⑤支持自我效能。"),
    ("如何处理客户的抗拒心理？", "不直接对抗，而是反映式倾听，引导客户自己发现改变的理由，使用\u201c滚动抵抗\u201d技术。"),
    ("有效沟通中，开放式问题和封闭式问题分别适用于什么场景？", "开放式问题（如何、为什么）用于探索客户想法和感受；封闭式问题（是否、多少）用于确认具体信息。"),
    ("如何进行有效的客户面谈？", "①准备面谈提纲 ②建立融洽关系 ③积极倾听 ④记录关键信息 ⑤总结确认 ⑥制定下一步计划。"),
    ("为什么记录每次训练的客户反馈很重要？", "追踪进展、调整计划、展示进步、增强客户信心、发现潜在问题。"),
    ("如何运用\u201c反映式倾听\u201d？", "用自己的话复述客户表达的内容和感受，确认理解正确，让客户感到被理解和尊重。"),
    ("教学中的\u201c脚手架\u201d策略是什么？", "先提供充分的支持和指导，随着客户能力提升逐步减少辅助，最终让客户独立完成动作。"),
    ("如何处理客户的负面情绪？", "承认和接纳情绪，不否定不评判，引导客户表达，帮助找到情绪的根源，共同探讨应对策略。"),
]

ch4_cards = [
    ("PAR-Q+问卷的作用是什么？", "筛查客户在开始运动前是否存在健康风险，识别需要医学许可的人群。"),
    ("健康危险分层的三个等级是什么？", "低风险（\u22641个危险因素）、中风险（2个危险因素或已有疾病）、高风险（已知疾病且有症状）。"),
    ("常见的心血管疾病危险因素有哪些？", "年龄（男\u226545/女\u226555）、吸烟、高血压、血脂异常、糖尿病、肥胖、家族史、久坐生活方式。"),
    ("什么情况下客户需要医学许可才能开始运动？", "PAR-Q+任一问题回答\u201c是\u201d；存在心血管疾病症状；中高风险分层；已知疾病且近期未就医。"),
    ("知情同意书应包含哪些内容？", "测试目的和程序说明、潜在风险和益处、客户权利（随时终止）、紧急程序、签字确认。"),
    ("静息血压测量的标准程序是什么？", "安静休息5分钟后，坐位，袖带与心脏同高，测量2次取平均值。"),
    ("体成分评估常用哪些方法？", "BMI、腰围/臀围比、皮褶厚度法、生物电阻抗法（BIA）、水下称重法、DXA。"),
    ("如何根据健康筛查结果确定运动强度？", "低风险：可进行中高强度运动；中风险：中等强度，需监督；高风险：低强度，需医学监督。"),
]

ch6_cards = [
    ("抗阻训练的基本原则是什么？", "渐进超负荷\u2014\u2014逐步增加训练量（重量、组数、次数）以持续刺激肌肉适应。"),
    ("1RM测试的注意事项是什么？", "充分热身（8-10次→6-8次→2-3次递增组），每组间隔3-5分钟，不超过5次尝试达到1RM。"),
    ("多关节动作和单关节动作的区别是什么？", "多关节：涉及两个以上关节（深蹲、硬拉、卧推）；单关节：只涉及一个关节（弯举、腿屈伸）。训练应以多关节为主。"),
    ("力量训练的训练顺序原则是什么？", "先大肌群后小肌群，先多关节后单关节，先高强度后低强度。"),
    ("组间休息时间如何根据训练目标调整？", "最大力量：3-5分钟；肌肉肥大：30-90秒；肌肉耐力：<30秒。"),
    ("渐进超负荷的常见方法有哪些？", "增加重量、增加次数、增加组数、缩短休息时间、增加训练频率、增加动作难度。"),
    ("什么是\u201c粘性点\u201d（sticking point）？如何处理？", "在动作中力学劣势最大的位置。处理方法：降低重量、在粘性点附近做部分动作训练、加强弱侧肌群。"),
    ("自由重量和固定器械各有什么优缺点？", "自由重量：需要更多稳定肌参与、功能性更强、但技术要求高；固定器械：稳定性好、安全性高、但运动轨迹固定。"),
    ("核心训练的主要目标肌群有哪些？", "腹直肌、腹横肌、腹内外斜肌、竖脊肌、多裂肌、腰方肌、骨盆底肌。"),
    ("超等长训练（Plyometrics）的适用人群和注意事项是什么？", "适用于有一定训练基础的客户。需先具备足够的基础力量，从低强度开始，注意落地缓冲技术，避免过度训练。"),
    ("如何为初学者设计全身训练计划？", "8-10个练习覆盖主要肌群，每个练习2-3组\u00d710-15次，每周2-3次，组间休息60-90秒，从轻负荷开始学习动作。"),
    ("抗阻训练中呼吸的基本原则是什么？", "发力（向心）时呼气，还原（离心）时吸气。避免瓦尔萨尔瓦动作（屏气用力），尤其是高血压客户。"),
]

chapters = {
    'ch3.html': ch3_cards,
    'ch4.html': ch4_cards,
    'ch6.html': ch6_cards,
}

for fname, cards in chapters.items():
    fpath = os.path.join(BASE, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Insert CSS before </style>
    content = content.replace('</style>', CSS_BLOCK + '\n</style>', 1)
    
    # 2. Add tab button before SOP工作单
    old_btn = '<button class="tab-btn" onclick="switchTab(\'sop\', this)">SOP工作单</button>'
    new_btn = '<button class="tab-btn" onclick="switchTab(\'flashcards\', this)">知识翻卡</button>\n<button class="tab-btn" onclick="switchTab(\'sop\', this)">SOP工作单</button>'
    content = content.replace(old_btn, new_btn, 1)
    
    # 3. Build flipcard HTML
    count = len(cards)
    lines = []
    lines.append('<div class="tab-content" id="tab-flashcards">')
    lines.append('<div class="fc-header">')
    lines.append('<h2>知识翻卡</h2>')
    lines.append('<p>共 {} 张知识卡片，点击翻转查看答案</p>'.format(count))
    lines.append('<span class="fc-counter">已翻转: 0/{}</span>'.format(count))
    lines.append('</div>')
    lines.append('<div class="flipcard-grid">')
    for i, (q, a) in enumerate(cards, 1):
        lines.append('<div class="flipcard" data-answer="{}" onclick="flipCard(this)">'.format(a))
        lines.append('<div class="flipcard-inner">')
        lines.append('<div class="flipcard-front">')
        lines.append('<span class="fc-num">Q{}</span>'.format(i))
        lines.append('<span class="fc-question">{}</span>'.format(q))
        lines.append('<span class="fc-hint">点击翻转</span>')
        lines.append('</div>')
        lines.append('<div class="flipcard-back">')
        lines.append('<span class="fc-answer">{}</span>'.format(a))
        lines.append('</div>')
        lines.append('</div>')
        lines.append('</div>')
    lines.append('</div>')
    lines.append('<div class="fc-footer">')
    lines.append('<button class="fc-reset-btn" onclick="resetFlipcards(this)">全部复位</button>')
    lines.append('</div>')
    lines.append('</div>')
    
    flipcard_html = '\n'.join(lines)
    
    # Insert before tab-sop
    sop_marker = '<div class="tab-content" id="tab-sop">'
    content = content.replace(sop_marker, flipcard_html + '\n' + sop_marker, 1)
    
    # 4. Insert JS before </script>
    content = content.replace('</script>', JS_BLOCK + '\n</script>', 1)
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OK {} - {} cards".format(fname, count))

print("All done!")
