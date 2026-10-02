#!/usr/bin/env python3
"""Test the improved search logic by simulating it in Python."""
import json
import re
import math

HTML_FILE = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso/chat-widget.html"

with open(HTML_FILE, 'r') as f:
    html = f.read()

m = re.search(r'<script type="application/json" id="knowledge-base">(.*?)</script>', html, re.DOTALL)
kb = json.loads(m.group(1))
chapters = kb['chapters']
blocks = kb['blocks']

ACE_DICT = set(w.lower() for w in [
    "有氧代谢","无氧代谢","乳酸阈值","心肺适能","最大心率","储备心率",
    "心率区间","运动强度","基础代谢","代谢当量","静息心率","心率储备",
    "高血压","糖尿病","骨质疏松","肥胖","代谢综合征","久坐行为",
    "非传染性疾病","心血管疾病","深蹲","硬拉","卧推","推举",
    "离心训练","向心训练","等长收缩","超量恢复","周期化","渐进超负荷",
    "执业范围","道德准则","继续教育","续证","转介","健康照护联盟",
    "跨理论模型","自我效能","动机访谈","健康信念模型","自我决定理论",
    "宏量营养素","蛋白质","碳水化合物","脂肪","膳食纤维","能量平衡","热量缺口",
    "VO2max","VT1","VT2","EPOC","RPE","BORG","PAR-Q","FMS","BMI","NCD",
    "ACE","CEC","NCCA","CPR","AED","HIPAA","TTM","SMART",
    "妊娠期","产后","老年人","青少年","慢性病","癌症康复",
    "体适能评估","肌肉耐力","柔韧性","平衡测试","健康筛查",
    "核心肌群","腹直肌","腹横肌","股四头肌","腘绳肌","臀大肌","竖脊肌",
    "斜方肌","三角肌","肱二头肌","肱三头肌","胸大肌","背阔肌",
    "肌肥大","爆发力","最大力量","神经适应",
    "通气阈值","磷酸原系统","糖酵解","基础代谢率",
    "行为改变","训练计划","运动处方","FITT原则",
    "注册营养师","物理治疗师","心理治疗","隐私保护",
    "医学许可","禁忌症","风险消除","职业责任","专业边界","双向转介",
])

SYNONYM_MAP = {k.lower(): v.lower() for k, v in {
    "深蹲": "squat", "squat": "深蹲",
    "高血压": "hypertension", "hypertension": "高血压",
    "执业范围": "scope of practice", "scope of practice": "执业范围",
    "跨理论模型": "transtheoretical model",
    "自我效能": "self-efficacy",
    "周期化": "periodization", "periodization": "周期化",
    "训练计划": "training program", "training program": "训练计划",
    "运动处方": "exercise prescription",
    "核心肌群": "core muscles",
    "腘绳肌": "hamstring", "hamstring": "腘绳肌",
    "股四头肌": "quadriceps", "quadriceps": "股四头肌",
    "臀大肌": "gluteus maximus", "gluteus maximus": "臀大肌",
}.items()}

def tokenize(text):
    text = text.lower()
    tokens = []
    tokens.extend(re.findall(r'[a-z][a-z0-9_-]*', text))
    # Mask out English words before extracting numbers to avoid pulling digits from tokens like "vt1"
    masked = re.sub(r'[a-z][a-z0-9_-]*', ' ', text)
    tokens.extend(re.findall(r'\d+\.?\d*%?', masked))
    for seg_match in re.finditer(r'[\u4e00-\u9fff]+', text):
        seg = seg_match.group()
        i = 0
        while i < len(seg):
            matched = False
            max_len = min(len(seg) - i, 6)
            for length in range(max_len, 1, -1):
                candidate = seg[i:i+length]
                if candidate in ACE_DICT:
                    tokens.append(candidate)
                    i += length
                    matched = True
                    break
            if not matched:
                tokens.append(seg[i])
                if i < len(seg) - 1:
                    tokens.append(seg[i:i+2])
                i += 1
    return tokens

def preprocess_query(query):
    query_lower = query.lower()
    chapter_match = re.search(r'第(\d+)[章节]', query)
    chapter_hint = int(chapter_match.group(1)) if chapter_match else None
    query_clean = re.sub(r'请问|帮我|我想问|我想知道|请告诉我|告诉一下|一下|能不能|请问一下', '', query_lower)
    base_tokens = tokenize(query_clean)
    expanded = set(base_tokens)
    for tok in base_tokens:
        if tok in SYNONYM_MAP:
            expanded.add(SYNONYM_MAP[tok])
            expanded.update(tokenize(SYNONYM_MAP[tok]))
    return list(expanded), chapter_hint

N = len(blocks)
df = {}
for b in blocks:
    content = (b[2] + ' ' + b[1]).lower()
    seen = set()
    for t in tokenize(content):
        if t not in seen:
            seen.add(t)
            df[t] = df.get(t, 0) + 1
idf = {}
for t, count in df.items():
    idf[t] = math.log((N + 1) / (count + 1)) + 1

def search(query, topK=3):
    qTokens, chapterHint = preprocess_query(query)
    if not qTokens:
        return []
    scores = []
    for i, b in enumerate(blocks):
        content = (b[2] + ' ' + b[1]).lower()
        title = (b[1] or '').lower()
        cTokens = tokenize(content)
        tf = {}
        for t in cTokens:
            tf[t] = tf.get(t, 0) + 1
        cLen = len(cTokens) or 1
        score = 0
        for qt in qTokens:
            is_dict_word = qt in ACE_DICT or len(qt) >= 3
            weight = 3.0 if is_dict_word else 1.0
            if qt in tf and qt in idf:
                score += (tf[qt] / cLen) * idf[qt] * weight
            elif qt not in tf and qt in content:
                score += 0.5 * idf.get(qt, 1.0) * weight
        if score > 0 and title:
            for qt in qTokens:
                if qt in title:
                    score *= 1.5
                    break
        if chapterHint and b[0] == chapterHint:
            score *= 2.0
        if score > 0:
            scores.append((i, score))
    scores.sort(key=lambda x: -x[1])
    return scores[:topK]

# Test
test_queries = ['VT1', '高血压', '深蹲', '执业范围', '续证', '第5章运动生理', 'SMART目标']
for q in test_queries:
    results = search(q, 3)
    print(f'\n=== Query: "{q}" ===')
    print(f'Tokens: {preprocess_query(q)[0][:8]}')
    print(f'Chapter hint: {preprocess_query(q)[1]}')
    for idx, score in results:
        b = blocks[idx]
        print(f'  Ch{b[0]} | {b[1][:40]:40s} | score={score:.4f} | {b[2][:50]}...')
