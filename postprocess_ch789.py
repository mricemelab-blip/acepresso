#!/usr/bin/env python3
"""
Post-process ch7/ch8/ch9 HTML:
1. Remove card-memory -> convert to italic paragraphs
2. Generate quiz questions from chapter content
3. Replace quiz placeholder with quiz-section
"""
import re, os, html as html_mod

OUTPUT_DIR = '/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso'

# ============================================================
# Quiz questions for each chapter - based on actual docx content
# ============================================================

QUIZ_CH7 = [
    # (statement, answer, explanation, tag_css)
    ("所有慢性病客户开始运动前必须获得医学许可。", True,
     "原文明确指出所有慢性病客户开始运动前需获得医学许可，这是跨疾病通用原则的首要要求。",
     "quiz-tip"),
    ("高血压中约90-95%为继发性高血压，由肾脏疾病等可识别原因引起。", False,
     "原文指出原发性高血压占90-95%，病因不明，为遗传+环境交互所致；继发性仅占5-10%。",
     "quiz-tip"),
    ("单次运动后血压可降低5-7 mmHg，且该效应持续24小时。", True,
     "原文明确报告单次运动后血压可降低5-7 mmHg，持续24小时；每周≥150分钟运动量降压效果最大。",
     "quiz-tip"),
    ("服用β受体阻滞剂的客户应使用心率监控运动强度。", False,
     "原文指出服用β受体阻滞剂/钙通道阻滞剂者应使用RPE监控强度，而非心率，并需缓慢变换体位。",
     "quiz-warn"),
    ("中风中约80%为缺血性中风，由脑血管被血栓/斑块堵塞引起。", True,
     "原文指出缺血性中风约占80%，出血性约占20%。",
     "quiz-tip"),
    ("FAST原则中的A代表Arrival（到达医院）。", False,
     "FAST中A代表Arms（手臂突然无力），F代表Face（面部下垂），S代表Speech（说话困难），T代表Time（立即呼叫急救）。",
     "quiz-warn"),
    ("外周动脉疾病（PAD）的核心运动改善模式是间歇步行训练。", True,
     "原文明确PAD的核心运动改善模式为间歇步行训练，通过步行产生缺血刺激侧支循环形成。",
     "quiz-tip"),
    ("单纯运动对LDL（低密度脂蛋白）的改善效果一致且显著。", False,
     "原文指出单纯运动对LDL改善不一致，需结合减重才能有效降低LDL。",
     "quiz-warn"),
    ("心肺训练是降低甘油三酯（TG）最有效的运动方式，肌力训练对此无效。", True,
     "原文指出心肺训练最有效（TG可作燃料），肌力训练对降低TG无效。",
     "quiz-tip"),
    ("单次中等强度运动30-60分钟可使TG降低持续12-36小时。", True,
     "原文报告餐后脂血症（PPL）单次中等强度运动30-60分钟后TG降低持续12-36小时，建议至少隔天运动一次。",
     "quiz-tip"),
    ("1型糖尿病患者运动时应增加胰岛素剂量以防止高血糖。", False,
     "原文指出1型糖尿病患者运动前应减少胰岛素剂量，运动前/中摄取易吸收碳水化合物，以防低血糖。",
     "quiz-warn"),
    ("PAD患者的间歇步行训练中，'高强度'指的是疼痛强度而非能量消耗。", True,
     "原文解释PAD间歇步行训练中'高强度'在此语境指疼痛强度，非能量消耗。",
     "quiz-tip"),
]

QUIZ_CH8 = [
    ("仅20-26%的美国青少年达到身体活动推荐水平。", True,
     "原文引用2018年报告卡评分D-，仅20-26%的美国青少年达到推荐水平。",
     "quiz-tip"),
    ("久坐习惯不具有代际传递性，父母的运动习惯不影响子女。", False,
     "原文指出久坐习惯延续至成年，形成代际恶性循环——父母不运动→子女不运动可能性高6倍。",
     "quiz-warn"),
    ("青春期前儿童在适当监督下不可进行肌肉训练，因为会导致生长迟缓。", False,
     "原文明确澄清：青春期前儿童可安全进行肌肉训练（在适当监督下），无证据显示适当监督的渐进式肌肉训练会导致生长迟缓或骨骼损伤。",
     "quiz-warn"),
    ("10个月简单肌肉训练使9岁女孩骨密度增幅达对照组4倍。", True,
     "原文引用研究数据：10个月简单肌肉训练使9岁女孩骨密度增幅达对照组4倍（6.2% vs 1.4%）。",
     "quiz-tip"),
    ("青少年每天应总计≥60分钟中等至高强度身体活动。", True,
     "原文核心原则明确青少年每天总计≥60分钟中等至高强度身体活动，包含心肺活动+肌肉强化+骨骼强化运动。",
     "quiz-tip"),
    ("孕妇运动时应使用心率监控运动强度。", False,
     "原文指出孕妇的谈话测试优于心率监控，结果<VT1即为中等强度。",
     "quiz-warn"),
    ("孕期运动可降低先兆子痫、妊娠期糖尿病和剖腹产的发生率。", True,
     "原文明确运动可降低先兆子痫、妊娠期糖尿病、剖腹产、下背痛、焦虑、恶心等多种不良结局的发生率。",
     "quiz-tip"),
    ("腹直肌分离在孕期的发病率高达45%。", True,
     "原文指出腹直肌分离孕期发病率高达45%，产后12个月仍达33%，孕前和孕期运动可减少35%发病率。",
     "quiz-tip"),
    ("孕期可以安全地进行热瑜伽练习。", False,
     "原文指出孕妇应避免极端高温环境（如热瑜伽），因环境温度/湿度升高可显著影响散热，可能导致高热症。",
     "quiz-warn"),
    ("产后运动恢复的目标是9-12个月回到孕前运动强度水平。", True,
     "原文建议产后慢慢开始，先增加持续时间和频率再增加强度，目标9-12个月回到孕前运动强度水平。",
     "quiz-tip"),
    ("老年人大约20%的髋骨折患者会死于相关并发症。", True,
     "原文指出约20%髋骨折老年人死于相关并发症，强调骨骼健康和防跌倒的重要性。",
     "quiz-tip"),
    ("老年人运动计划不需要包含平衡训练。", False,
     "原文明确平衡训练必须纳入老年人运动计划，以提高本体感受、降低跌倒风险。每周≥2次肌力训练同样必须纳入。",
     "quiz-warn"),
    ("身体活动可以预防和减缓50岁以上人群的认知能力衰退。", True,
     "原文指出身体活动可预防和减缓认知能力衰退，适用于50岁以上人群，无论初始认知状态。",
     "quiz-tip"),
]

QUIZ_CH9 = [
    ("私人教练的职责包括损伤评估和诊断。", False,
     "原文指出私人教练的职责是运动评估，不是损伤评估/诊断。客户出现疼痛或受伤，必须转介给医疗保健专业人员。",
     "quiz-warn"),
    ("RICE处理中的I代表冰敷（Ice），应在受伤后前24-48小时内使用。", True,
     "原文指出急性期标准处理为RICE（休息Rest、冰敷Ice、压迫Compression、抬高Elevation），前24-48小时冰敷。",
     "quiz-tip"),
    ("冰敷时应直接接触皮肤以获得最佳效果。", False,
     "原文指出冰敷应间接接触皮肤，每次≤20分钟。直接冰敷可能造成冻伤。",
     "quiz-warn"),
    ("疼痛超过3级即应停止运动。", True,
     "原文明确疼痛超过3级即停止运动（3级尚未引起不适/痛苦），训练前及训练中需持续评估疼痛等级。",
     "quiz-tip"),
    ("静态拉伸应放在锻炼开始时进行热身。", False,
     "原文指出静态拉伸放在锻炼结束时，因为长时间拉伸后会导致神经抑制和力量下降。",
     "quiz-warn"),
    ("III级肌肉拉伤在老年人中更常见，因为胶原组织失去弹性。", True,
     "原文指出III级拉伤在老年人中更常见（胶原组织失去弹性），愈合时间取决于严重程度。",
     "quiz-tip"),
    ("ACL撕裂只能通过接触性外力产生。", False,
     "原文指出ACL撕裂机制包括接触性（如橄榄球撞击）和非接触性（如篮球踩硬地面同时突然切球和扭动）两种。",
     "quiz-warn"),
    ("大部分软骨无血管，因此无法自行愈合。", True,
     "原文指出大部分软骨无血管→无法自行愈合，常需手术取出撕裂碎片；例外是半月板外侧1/3血管丰富，可手术修复。",
     "quiz-tip"),
    ("脑震荡后二次损伤可导致危及生命的二次撞击综合征。", True,
     "原文指出脑震荡后脑部极脆弱，二次损伤可导致二次撞击综合征（危及生命），必须立即停止活动。",
     "quiz-tip"),
    ("椎间盘损伤中Valsalva动作（憋气）会增加受伤风险。", True,
     "原文指出Valsalva动作增加椎间盘受伤风险，打喷嚏/咳嗽同理。",
     "quiz-tip"),
    ("应力性骨折仅发生在胫骨。", False,
     "原文指出所有骨头均可发生应力性骨折，股骨颈时有发生，胫骨最常见（常被误认为外胫夹）。",
     "quiz-warn"),
    ("包含全方位力量和稳定性训练可降低非接触性韧带损伤风险。", True,
     "原文明确包含全方位力量和稳定性训练可降低非接触性损伤风险。",
     "quiz-tip"),
]


def build_quiz_html(quiz_items):
    """Build quiz section HTML from quiz items list."""
    parts = ['<div class="quiz-section">',
             '<div class="quiz-header"><h2>判断题</h2>',
             '<p class="quiz-instruction">判断以下说法是否正确，点击展开参考答案。</p></div>']
    for idx, (stmt, answer, explanation, css_class) in enumerate(quiz_items, 1):
        escaped_stmt = html_mod.escape(stmt)
        ans_text = '正确' if answer else '错误'
        parts.append(
            f'<div class="quiz-item">'
            f'<div class="quiz-q"><span class="quiz-num">{idx}.</span>'
            f'<span class="quiz-tag {css_class}">要点</span>'
            f'<span>{escaped_stmt}</span></div>'
            f'<details class="quiz-answer"><summary>查看答案</summary>'
            f'<p><strong>答案：{ans_text}</strong>。{html_mod.escape(explanation)}</p>'
            f'</details></div>'
        )
    parts.append('</div>')
    return '\n'.join(parts)


def process_html(filepath, quiz_items):
    """Post-process a single HTML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 1. Convert card-memory to italic paragraphs
    # Pattern: <div class="card card-memory">...<p>content</p>...</div>
    def replace_card_memory(match):
        card_html = match.group(0)
        # Extract text from <p> tags inside
        p_matches = re.findall(r'<p>(.*?)</p>', card_html, re.DOTALL)
        if p_matches:
            text = p_matches[0]
            return f'<p style="color:var(--text-secondary);font-size:14px;font-style:italic;margin:8px 0 16px;">💡 {text}</p>'
        return ''
    
    html = re.sub(
        r'<div class="card card-memory">.*?</div>\s*</div>',
        replace_card_memory,
        html,
        flags=re.DOTALL
    )
    
    # 2. Replace quiz placeholder with quiz content
    quiz_html = build_quiz_html(quiz_items)
    
    # Replace various placeholder patterns
    html = re.sub(
        r'<div class="placeholder">本章暂无判断题。</div>',
        quiz_html,
        html
    )
    html = re.sub(
        r'<div class="placeholder">本章自测题目已移除。</div>',
        quiz_html,
        html
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html


def verify(html, ch_name):
    """Verify the processed HTML."""
    card_memory = len(re.findall(r'class="card card-memory"', html))
    card_tip = len(re.findall(r'class="card card-tip"', html))
    card_wrong = len(re.findall(r'class="card card-wrong"', html))
    card_right = len(re.findall(r'class="card card-right"', html))
    card_warn = len(re.findall(r'class="card card-warn"', html))
    card_scene = len(re.findall(r'class="card card-scene"', html))
    quiz_items = len(re.findall(r'class="quiz-item"', html))
    tables = len(re.findall(r'<table', html))
    images = len(re.findall(r'<img', html))
    memory_paras = len(re.findall(r'font-style:italic', html))
    size = len(html.encode('utf-8'))
    
    print(f"\n{'='*50}")
    print(f"验证: {ch_name}")
    print(f"  文件大小: {size:,} bytes")
    print(f"  card-memory: {card_memory} (应为0)")
    print(f"  memory段落: {memory_paras}")
    print(f"  卡片: tip={card_tip}, wrong={card_wrong}, right={card_right}, warn={card_warn}, scene={card_scene}")
    print(f"  表格: {tables}")
    print(f"  图片: {images}")
    print(f"  quiz题目: {quiz_items}")
    
    ok = card_memory == 0 and quiz_items > 0
    print(f"  {'✅ 通过' if ok else '❌ 问题'}")
    return ok


# Main
chapters = {
    'ch7.html': ('第7章', QUIZ_CH7),
    'ch8.html': ('第8章', QUIZ_CH8),
    'ch9.html': ('第9章', QUIZ_CH9),
}

all_ok = True
for fname, (ch_name, quiz) in chapters.items():
    fpath = os.path.join(OUTPUT_DIR, fname)
    html = process_html(fpath, quiz)
    ok = verify(html, ch_name)
    if not ok:
        all_ok = False

print(f"\n{'='*50}")
print(f"总体结果: {'✅ 全部通过' if all_ok else '❌ 存在问题'}")
