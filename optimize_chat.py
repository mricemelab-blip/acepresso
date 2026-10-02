#!/usr/bin/env python3
"""
Optimize ACE AI Tutor: improved tokenization, search, system prompt, 
knowledge base re-chunking, and follow-up suggestions.
Uses plain string replacement to avoid regex escape issues.
"""
import json
import re
import os

WORKDIR = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"
HTML_FILE = os.path.join(WORKDIR, "chat-widget.html")
KB_FILE = os.path.join(WORKDIR, "ace_knowledge_base.md")

# ============================================================
# ACE Dictionary (~200 core terms)
# ============================================================

ACE_DICT = [
    "有氧代谢","无氧代谢","乳酸阈值","心肺适能","最大心率","储备心率",
    "心率区间","运动强度","基础代谢","代谢当量","静息心率","心率储备",
    "无氧阈","通气阈值","摄氧量","氧耗","氧债","运动后过量氧耗",
    "磷酸原系统","糖酵解","氧化磷酸化","三羧酸循环","肌糖原","肝糖原",
    "糖异生","脂肪氧化","底物利用","运动底物","代谢适应",
    "股四头肌","腘绳肌","臀大肌","竖脊肌","斜方肌","三角肌",
    "肱二头肌","肱三头肌","核心肌群","腹直肌","腹横肌","腹斜肌",
    "胸大肌","背阔肌","菱形肌","前锯肌","髂腰肌","腰方肌",
    "腓肠肌","比目鱼肌","胫骨前肌","肩袖肌群","冈上肌","肩胛下肌",
    "内收肌","外展肌","梨状肌","阔筋膜张肌","髂胫束",
    "多裂肌","回旋肌","盆底肌","膈肌","肋间肌",
    "腹内斜肌","腹外斜肌","臀中肌","臀小肌","大圆肌","小圆肌","冈下肌","喙肱肌","肱桡肌",
    "深蹲","硬拉","卧推","推举","引体","划船","离心训练","向心训练",
    "等长收缩","超量恢复","周期化","渐进超负荷","力量训练","抗阻训练",
    "心肺训练","功能性训练","敏捷训练","平衡训练","柔韧性训练",
    "肌肉耐力","爆发力","最大力量","肌肥大","神经适应",
    "超等长训练","复合训练","孤立训练","多关节训练","单关节训练",
    "训练量","训练频率","训练强度","组间休息","训练变量",
    "线性周期","波动周期","板块周期","逆周期化","减量训练",
    "高血压","糖尿病","骨质疏松","肥胖","代谢综合征","久坐行为",
    "非传染性疾病","心血管疾病","冠心病","中风","二型糖尿病",
    "体脂率","体质指数","腰围","内脏脂肪","血脂异常",
    "胆固醇","甘油三酯","高密度脂蛋白","低密度脂蛋白",
    "动脉粥样硬化","胰岛素抵抗","慢性炎症",
    "关节炎","类风湿","骨关节炎",
    "宏量营养素","蛋白质","碳水化合物","脂肪","膳食纤维",
    "能量平衡","热量缺口","微量营养素","维生素","矿物质",
    "氨基酸","必需氨基酸","完全蛋白质","蛋白质合成","氮平衡",
    "升糖指数","血糖负荷","胰岛素敏感性","糖原储备",
    "脂溶性维生素","水溶性维生素","电解质","水分平衡",
    "能量消耗","食物热效应","基础代谢率","总能量消耗",
    "膳食指南","营养金字塔","水分摄入",
    "跨理论模型","前意向阶段","意向阶段","准备阶段","行动阶段",
    "维持阶段","自我效能","动机访谈","健康信念模型","自我决定理论",
    "操作性条件反射","刺激控制","认知行为","目标设定","自我监测",
    "社会认知理论","结果预期","效能预期","自我调节",
    "内在动机","外在动机","自主动机","受控动机","能力感知",
    "自主性","归属感","行为契约","社会支持",
    "健康筛查","体适能评估","肌肉耐力","柔韧性","平衡测试",
    "心肺耐力测试","皮下脂肪","生物电阻抗","皮褶厚度",
    "静态评估","动态评估","姿势评估","步态分析",
    "过顶深蹲","单腿下蹲","推举测试",
    "血压测量","静息心率","心率监测",
    "妊娠期","产后","老年人","青少年","慢性病","癌症康复",
    "哮喘","抑郁症","焦虑症",
    "医学许可","禁忌症","运动处方",
    "执业范围","道德准则","继续教育","续证","转介",
    "健康照护联盟","注册营养师","物理治疗师","心理治疗",
    "隐私保护","客户安全","风险消除",
    "职业责任","专业边界","双向转介","认证项目",
    "VO2max","VT1","VT2","EPOC","RPE","BORG",
    "PAR-Q","FMS","BMI","NCD","WHO","ACE",
    "CEC","NCCA","CPR","AED","HIPAA",
    "TTM","SMART","BLS","RD","SNC",
    "BORG量表","RPE量表","PAR-Q+","体适能测试",
    "Rockport步行测试","YMCA功率车测试","Astrand功率车测试",
    "运动处方","FITT原则","FITTE原则",
    "热身","整理活动","拉伸","动态拉伸","静态拉伸",
    "筋膜","肌筋膜","泡沫轴","自我筋膜放松",
    "本体感觉","神经肌肉控制","运动模式",
    "肩关节","膝关节","髋关节","踝关节","脊柱",
    "屈曲","伸展","外展","内收","旋转","内旋","外旋",
    "矢状面","额状面","水平面","冠状面",
    "力臂","力矩","杠杆","阻力","摩擦力",
    "等张收缩","等动收缩","离心收缩","向心收缩",
    "协同肌","拮抗肌","原动肌","稳定肌","固定肌",
]

ACE_DICT.sort(key=lambda x: len(x), reverse=True)

SYNONYM_MAP = {
    "深蹲": "squat", "squat": "深蹲",
    "硬拉": "deadlift", "deadlift": "硬拉",
    "卧推": "bench press", "bench press": "卧推",
    "高血压": "hypertension", "hypertension": "高血压",
    "糖尿病": "diabetes", "diabetes": "糖尿病",
    "骨质疏松": "osteoporosis", "osteoporosis": "骨质疏松",
    "乳酸阈值": "lactate threshold", "lactate threshold": "乳酸阈值",
    "心肺适能": "cardiorespiratory fitness", "cardiorespiratory fitness": "心肺适能",
    "执业范围": "scope of practice", "scope of practice": "执业范围",
    "跨理论模型": "transtheoretical model", "transtheoretical model": "跨理论模型",
    "自我效能": "self-efficacy", "self-efficacy": "自我效能",
    "动机访谈": "motivational interviewing", "motivational interviewing": "动机访谈",
    "宏量营养素": "macronutrient", "macronutrient": "宏量营养素",
    "代谢综合征": "metabolic syndrome", "metabolic syndrome": "代谢综合征",
    "非传染性疾病": "noncommunicable diseases", "noncommunicable diseases": "非传染性疾病",
    "健康筛查": "health screening", "health screening": "健康筛查",
    "渐进超负荷": "progressive overload", "progressive overload": "渐进超负荷",
    "周期化": "periodization", "periodization": "周期化",
    "肌肥大": "muscle hypertrophy", "muscle hypertrophy": "肌肥大",
    "基础代谢率": "basal metabolic rate", "basal metabolic rate": "基础代谢率",
    "体适能": "fitness", "fitness": "体适能",
    "柔韧性": "flexibility", "flexibility": "柔韧性",
    "转介": "referral", "referral": "转介",
    "健康照护联盟": "allied health", "allied health": "健康照护联盟",
    "继续教育": "continuing education", "continuing education": "继续教育",
    "道德准则": "code of ethics", "code of ethics": "道德准则",
    "妊娠期": "prenatal", "prenatal": "妊娠期",
    "老年人": "older adults", "older adults": "老年人",
    "行为改变": "behavior change", "behavior change": "行为改变",
    "训练计划": "training program", "training program": "训练计划",
    "运动处方": "exercise prescription", "exercise prescription": "运动处方",
    "核心肌群": "core muscles", "core muscles": "核心肌群",
    "肩袖": "rotator cuff", "rotator cuff": "肩袖",
    "腘绳肌": "hamstring", "hamstring": "腘绳肌",
    "股四头肌": "quadriceps", "quadriceps": "股四头肌",
    "臀大肌": "gluteus maximus", "gluteus maximus": "臀大肌",
}


def process_knowledge_base():
    """Re-chunk knowledge base from existing HTML into finer blocks."""
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    json_match = re.search(r'<script type="application/json" id="knowledge-base">(.*?)</script>', html_content, re.DOTALL)
    if not json_match:
        raise ValueError("Cannot find knowledge-base JSON in HTML")
    
    kb_data = json.loads(json_match.group(1))
    chapters = kb_data['chapters']
    old_blocks = kb_data['blocks']
    
    new_blocks = []
    for block in old_blocks:
        ch_num, title, content = block[0], block[1], block[2]
        
        if len(content) <= 500:
            new_blocks.append([ch_num, title, content])
        else:
            paragraphs = re.split(r'\n\n+', content)
            current_chunk = ""
            chunk_title = title
            
            for para in paragraphs:
                if not para.strip():
                    continue
                if len(current_chunk) + len(para) > 500 and current_chunk:
                    new_blocks.append([ch_num, chunk_title, current_chunk.strip()])
                    current_chunk = para
                    chunk_title = title + "（续）"
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
            
            if current_chunk.strip():
                new_blocks.append([ch_num, chunk_title, current_chunk.strip()])
    
    return chapters, new_blocks


def modify_html():
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Process knowledge base
    chapters, new_blocks = process_knowledge_base()
    print(f"Knowledge base: {len(new_blocks)} blocks (re-chunked)")
    
    # === 1. Replace knowledge base JSON ===
    kb_json = json.dumps({"chapters": chapters, "blocks": new_blocks}, ensure_ascii=False)
    json_match = re.search(r'(<script type="application/json" id="knowledge-base">).*?(</script>)', html, re.DOTALL)
    html = html[:json_match.start()] + '<script type="application/json" id="knowledge-base">' + kb_json + '</script>' + html[json_match.end():]
    
    # === 2. Find and replace from tokenize to end of searchKnowledge ===
    # Find "function tokenize(text)" start
    tokenize_start = html.index('// ========== Simple Chinese Tokenizer ==========')
    # Find end of searchKnowledge - it ends before "// ========== Build Context =========="
    build_ctx_marker = '// ========== Build Context =========='
    search_end = html.index(build_ctx_marker)
    
    # Build dictionary JS
    dict_entries_js = ",\n".join(f'    "{w.lower()}"' for w in ACE_DICT)
    syn_entries_js = ",\n".join(f'    "{k.lower()}": "{v.lower()}"' for k, v in SYNONYM_MAP.items())
    
    new_tokenizer_and_search = f'''// ========== ACE Dictionary ==========
const ACE_DICT = new Set([
{dict_entries_js}
]);
const SYNONYM_MAP = {{
{syn_entries_js}
}};

// ========== Improved Chinese Tokenizer (Dictionary-based) ==========
function tokenize(text) {{
  text = text.toLowerCase();
  const tokens = [];
  // English words (may include trailing digits like vt1, vo2max)
  const enMatches = text.match(/[a-z][a-z0-9_-]*/g);
  if (enMatches) tokens.push(...enMatches);
  // Numbers: mask out English-word regions first to avoid extracting digits from tokens like "vt1"
  const masked = text.replace(/[a-z][a-z0-9_-]*/g, ' ');
  const nums = masked.match(/\\d+\\.?\\d*%?/g);
  if (nums) tokens.push(...nums);
  const zhSegments = text.match(/[\\u4e00-\\u9fff]+/g);
  if (zhSegments) {{
    for (const seg of zhSegments) {{
      let i = 0;
      while (i < seg.length) {{
        let matched = false;
        const maxLen = Math.min(seg.length - i, 6);
        for (let len = maxLen; len > 1; len--) {{
          const candidate = seg.substring(i, i + len);
          if (ACE_DICT.has(candidate)) {{
            tokens.push(candidate);
            i += len;
            matched = true;
            break;
          }}
        }}
        if (!matched) {{
          tokens.push(seg[i]);
          if (i < seg.length - 1) tokens.push(seg.substring(i, i + 2));
          i++;
        }}
      }}
    }}
  }}
  return tokens;
}}

// ========== Query Preprocessing ==========
function preprocessQuery(query) {{
  const queryLower = query.toLowerCase();
  const chapterMatch = queryLower.match(/第(\\d+)[章节]/);
  const chapterHint = chapterMatch ? parseInt(chapterMatch[1]) : null;
  let queryClean = queryLower.replace(/请问|帮我|我想问|我想知道|请告诉我|告诉一下|一下|能不能|请问一下/g, '');
  const baseTokens = tokenize(queryClean);
  const expandedSet = new Set(baseTokens);
  for (const tok of baseTokens) {{
    if (SYNONYM_MAP[tok]) {{
      expandedSet.add(SYNONYM_MAP[tok]);
      const synTokens = tokenize(SYNONYM_MAP[tok]);
      synTokens.forEach(t => expandedSet.add(t));
    }}
  }}
  return {{ tokens: Array.from(expandedSet), chapterHint }};
}}

// ========== IDF Pre-computation ==========
const N = blocks.length;
const df = {{}};
for (const b of blocks) {{
  const content = (b[2] + ' ' + b[1]).toLowerCase();
  const seen = new Set();
  const toks = tokenize(content);
  for (const t of toks) {{
    if (!seen.has(t)) {{ seen.add(t); df[t] = (df[t] || 0) + 1; }}
  }}
}}
const idf = {{}};
for (const t in df) {{
  idf[t] = Math.log((N + 1) / (df[t] + 1)) + 1;
}}

// ========== Improved TF-IDF Search with Dictionary Scoring ==========
function searchKnowledge(query, topK) {{
  topK = topK || 6;
  const {{ tokens: qTokens, chapterHint }} = preprocessQuery(query);
  if (!qTokens.length) return [];

  const scores = [];
  for (let i = 0; i < blocks.length; i++) {{
    const b = blocks[i];
    const content = (b[2] + ' ' + b[1]).toLowerCase();
    const title = (b[1] || '').toLowerCase();
    const cTokens = tokenize(content);
    const tf = {{}};
    for (const t of cTokens) tf[t] = (tf[t] || 0) + 1;
    const cLen = cTokens.length || 1;

    let score = 0;
    for (const qt of qTokens) {{
      const isDictWord = ACE_DICT.has(qt) || qt.length >= 3;
      const weight = isDictWord ? 3.0 : 1.0;
      if (tf[qt] && idf[qt]) {{
        score += (tf[qt] / cLen) * idf[qt] * weight;
      }}
      if (!tf[qt] && content.includes(qt)) {{
        score += 0.5 * (idf[qt] || 1.0) * weight;
      }}
    }}
    if (score > 0 && title) {{
      for (const qt of qTokens) {{
        if (title.includes(qt)) {{
          score *= 1.5;
          break;
        }}
      }}
    }}
    if (chapterHint && b[0] === chapterHint) {{
      score *= 2.0;
    }}
    if (score > 0) scores.push({{ idx: i, score: score }});
  }}

  scores.sort((a, b) => b.score - a.score);
  return scores.slice(0, topK).map(s => s.idx);
}}

'''
    
    html = html[:tokenize_start] + new_tokenizer_and_search + html[search_end:]
    
    # === 3. Replace buildContext function ===
    bc_start = html.index('// ========== Build Context ==========')
    bc_end_marker = '// ========== Simple Markdown Renderer =========='
    bc_end = html.index(bc_end_marker)
    
    new_build_context = '''// ========== Build Context with Source Annotations ==========
function buildContext(indices) {
  if (!indices || indices.length === 0) {
    return '【未找到直接相关的教材段落】\\n建议在对话中引导学生回顾教材目录，或提出更具体的问题。';
  }
  const parts = [];
  const seen = new Set();
  for (const idx of indices) {
    const b = blocks[idx];
    const key = b[0] + '|' + b[2].substring(0, 50);
    if (seen.has(key)) continue;
    seen.add(key);
    const chName = chapters[b[0]] || ('第' + b[0] + '章');
    let ctx = '【第' + b[0] + '章 - ' + chName;
    if (b[1]) ctx += ' · ' + b[1];
    ctx += '】\\n' + b[2];
    parts.push(ctx);
  }
  return parts.join('\\n\\n---\\n\\n');
}

'''
    
    html = html[:bc_start] + new_build_context + html[bc_end:]
    
    # === 4. Replace SYSTEM_PROMPT ===
    sp_start = html.index("const SYSTEM_PROMPT = `")
    # Find the closing `;
    sp_content_start = html.index("const SYSTEM_PROMPT = `") + len("const SYSTEM_PROMPT = `")
    # Find the matching closing backtick + semicolon
    search_from = sp_content_start
    while True:
        idx = html.index('`;', search_from)
        # Check it's not escaped
        if idx > 0 and html[idx-1] == '\\':
            search_from = idx + 2
            continue
        sp_end = idx + 2  # include `;
        break
    
    new_system_prompt = r"""const SYSTEM_PROMPT = `你是 ACEpresso 课程的 AI 助教，一名专业的 ACE 认证私人教练导师。

## 核心原则
1. 所有回答必须基于下方提供的教材段落。教材中没有涉及的内容，明确告知学生"这个问题超出了本教材范围，建议查阅[具体章节]或咨询相关专业人士"。
2. 回答时引用教材中的具体章节号和小节标题（如"根据第5章第2节..."）。
3. 专业术语首次出现时附英文原文，如"乳酸阈值（Lactate Threshold, LT）"。
4. 用苏格拉底式提问引导学生思考，而非直接给出全部答案。例如学生问"VT1和VT2有什么区别"，先回答核心区别，再追问"你觉得在训练计划中应该怎样利用这两个阈值？"
5. 如果学生问的是实践问题（如"客户有高血压怎么办"），先给出教材观点，再给出具体的实践步骤。

## 回答结构
每次回答遵循以下结构：
- **核心回答**：1-2句话直接回答
- **教材依据**：引用相关章节和具体知识点
- **实践应用**：如何在实际训练中运用（如适用）
- **延伸思考**：提出一个相关问题引导学生深入（如适用）

## 能力边界
- 不给出医疗诊断、处方或治疗建议
- 不超出私人教练执业范围（不诊断、不开菜单、不治疗）
- 不编造教材中没有的数据、研究或案例
- 涉及其他专业领域时，建议学生咨询相关专业人员

## 语言风格
- 专业但易懂，避免过度学术化
- 适当使用教材中的助记口诀和类比
- 回答控制在 200-400 字，重点突出
- 使用 Markdown 格式（加粗、列表）提高可读性`"""
    
    html = html[:sp_start] + new_system_prompt + html[sp_end:]
    
    # === 5. Add follow-up suggestion function and update sendMessage ===
    old_try_block = """    try {
      const reply = await callDeepSeek(text);
      typing.classList.remove('show');
      addMessage(reply, 'ai');
    } catch (err) {"""
    
    new_try_block = """    try {
      const reply = await callDeepSeek(text);
      typing.classList.remove('show');
      addMessage(reply, 'ai');
      generateFollowUps(reply, text);
    } catch (err) {"""
    
    html = html.replace(old_try_block, new_try_block)
    
    # === 6. Add generateFollowUps function before sendMessage ===
    followup_func = '''
  // ========== Follow-up Suggestion Generator ==========
  function generateFollowUps(reply, originalQuery) {
    const container = document.getElementById('suggestions');
    if (!container) return;
    container.innerHTML = '';
    
    const suggestions = [];
    const replyLower = reply.toLowerCase();
    
    const chapterTopics = {
      1: ['执业范围具体案例', '健康照护联盟协作', 'ACE续证要求'],
      2: ['跨理论模型各阶段特点', '自我效能如何提升', '动机访谈实操'],
      3: ['蛋白质摄入推荐量', '宏量营养素分配', '能量平衡计算'],
      4: ['肌肉收缩类型', '力矩与杠杆原理', '运动平面分类'],
      5: ['VT1和VT2区别', 'EPOC的应用', '心肺训练处方设计'],
      6: ['体适能评估流程', 'FMS评分标准', '血压测量注意事项'],
      7: ['FITT原则应用', '周期化训练设计', '渐进超负荷实施'],
      8: ['妊娠期训练注意事项', '高血压客户训练方案', '老年人跌倒预防'],
      9: ['HIPAA隐私保护', '道德准则案例', '转介流程']
    };
    
    const chapterRefs = reply.match(/第(\\d+)[章节]/g);
    let detectedChapters = [];
    if (chapterRefs) {
      detectedChapters = [...new Set(chapterRefs.map(r => parseInt(r.match(/\\d+/)[0])))];
    }
    
    for (const ch of detectedChapters) {
      if (chapterTopics[ch]) {
        const topics = chapterTopics[ch].filter(t => !replyLower.includes(t.toLowerCase()));
        suggestions.push(...topics.slice(0, 2));
      }
    }
    
    if (suggestions.length === 0) {
      const keywordSuggestions = {
        'vt1': ['VT2的定义和应用', '如何利用VT1设计训练', '通气阈值的测试方法'],
        'vt2': ['VT1和VT2的区别', 'VT2在间歇训练中的应用', '如何判断客户达到VT2'],
        '高血压': ['高血压客户的运动禁忌', '有氧训练对血压的影响', '客户筛查流程'],
        '深蹲': ['深蹲常见错误', '深蹲的肌肉激活顺序', '如何教客户正确深蹲'],
        '执业范围': ['执业范围具体案例', '什么情况下需要转介', '道德准则核心内容'],
        '续证': ['CEC学分要求', '继续教育方向推荐', '认证到期怎么办'],
        '蛋白质': ['每日蛋白质推荐量', '蛋白质来源对比', '蛋白质与肌肥大的关系'],
        '周期化': ['线性周期化设计', '板块周期化特点', '如何为客户制定周期计划'],
      };
      
      for (const [keyword, sugs] of Object.entries(keywordSuggestions)) {
        if (replyLower.includes(keyword) || originalQuery.toLowerCase().includes(keyword)) {
          suggestions.push(...sugs.slice(0, 2));
          break;
        }
      }
    }
    
    if (suggestions.length === 0) {
      suggestions.push('这个知识点在考试中的重点', '能举一个实际案例吗', '还有其他相关内容吗');
    }
    
    const finalSuggestions = suggestions.slice(0, 3);
    for (const sug of finalSuggestions) {
      const chip = document.createElement('div');
      chip.className = 'suggestion-chip';
      chip.textContent = sug;
      chip.onclick = function() { sendSuggestion(this); };
      container.appendChild(chip);
    }
    container.style.display = 'flex';
  }

'''
    
    marker = "  window.sendMessage = async function() {"
    html = html.replace(marker, followup_func + marker)
    
    # === 7. Update sendSuggestion to hide suggestions ===
    old_sug = """  window.sendSuggestion = function(el) {
    document.getElementById('userInput').value = el.textContent;
    sendMessage();
  };"""
    new_sug = """  window.sendSuggestion = function(el) {
    document.getElementById('userInput').value = el.textContent;
    document.getElementById('suggestions').style.display = 'none';
    sendMessage();
  };"""
    html = html.replace(old_sug, new_sug)
    
    # Write
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML updated: {HTML_FILE}")
    print(f"Blocks: {len(new_blocks)}")


if __name__ == '__main__':
    modify_html()
    print("Done!")
