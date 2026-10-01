from bs4 import BeautifulSoup
import os

BASE = "/Coze/Drive/Arise/所有对话/主对话/3HFIT/教培中心/acepporesso"

SOP_DATA = {
    1: {
        "title": "私人教练执业边界清单",
        "items": [
            ("✅", "评估客户健康危险因素（PAR-Q+、健康史问卷）"),
            ("✅", "提供基础营养知识普及（非个性化饮食方案）"),
            ("✅", "辅助客户遵从理疗师建议（在许可范围内执行训练）"),
            ("✅", "客观记录客户身体变化和训练数据"),
            ("✅", "运用运动指导技巧（示范、反馈、激励）"),
            ("❌", "不得提供心理咨询或治疗"),
            ("❌", "不得设计矫形/康复方案"),
            ("❌", "不得提供按摩治疗"),
            ("❌", "不得开具处方或诊断"),
            ("❌", "不得制定个性化营养/膳食计划"),
            ("⚠️", "饮食紊乱/抑郁/焦虑客户 → 转介专业人士"),
            ("⚠️", "慢性疼痛客户 → 转介物理治疗师"),
        ]
    },
    2: {
        "title": "行为改变教练操作清单",
        "items": [
            ("", "评估客户处于变化模型的哪个阶段（前/中/行动/维持）"),
            ("", "使用动机性访谈（MI）激发内在动机"),
            ("", "帮助客户设定 SMART 目标"),
            ("", "建立行为契约（书面协议：做什么/何时/频率/时长）"),
            ("", "运用\"如果-那么\"计划（Implementation Intention）"),
            ("", "使用控制刺激法（移除不良线索，增加健康线索）"),
            ("", "帮助客户建立外部支持系统（团体/伙伴/社区）"),
            ("", "使用决策平衡表帮助客户看清利弊"),
            ("", "通过成功体验提升自我效能"),
            ("", "正确看待复发：视为学习机会而非失败"),
        ]
    },
    3: {
        "title": "沟通与教学操作清单",
        "items": [
            ("", "首次面谈：建立融洽关系，使用积极倾听"),
            ("", "非语言沟通：保持眼神接触、开放姿态、适当距离"),
            ("", "动作示范：正面→侧面→背面，慢速→正常速度"),
            ("", "给予反馈：先肯定正确动作，再纠正错误（三明治法）"),
            ("", "目标设定：将长期目标拆解为短期可量化里程碑"),
            ("", "使用多种教学策略适应不同学习风格（视觉/听觉/动觉）"),
            ("", "记录每次训练的客户反馈和进展"),
            ("", "定期回顾目标进度，调整训练计划"),
        ]
    },
    4: {
        "title": "运动前健康筛查操作清单",
        "items": [
            ("", "所有客户填写 PAR-Q+ 问卷"),
            ("", "健康史问卷（既往病史、用药、手术、家族史）"),
            ("", "知情同意书签署"),
            ("", "身体活动准备问卷（PAR-Q+ 阳性 → 医学许可）"),
            ("", "健康危险分层（低风险/中风险/高风险）"),
            ("", "静息心率、血压测量"),
            ("", "体成分评估（体脂率、腰围）"),
            ("", "确定是否需要医学许可后才能开始运动"),
            ("", "根据风险分层选择合适的体适能测试"),
            ("", "记录所有筛查结果，建立客户档案"),
        ]
    },
    5: {
        "title": "心肺训练处方设计清单",
        "items": [
            ("", "确定客户心肺训练目标（减脂/耐力/健康维持）"),
            ("", "选择强度指标：%HRR 或 %VO2R 或 RPE"),
            ("", "计算靶心率范围（Karvonen公式）"),
            ("", "确定频率：中等≥5天/周 或 高强度≥3天/周"),
            ("", "确定时间：≥30分钟中等 或 ≥20分钟高强度"),
            ("", "选择方式：考虑客户偏好、关节状况、设备可用性"),
            ("", "制定渐进计划：每1-2周增加不超过10%训练量"),
            ("", "教授自我监控方法（心率监测、RPE、谈话测试）"),
            ("", "记录每次训练的心率、时长、RPE、主观感受"),
            ("", "定期评估并调整处方（每4-6周）"),
        ]
    },
    6: {
        "title": "肌肉训练处方设计清单",
        "items": [
            ("", "评估客户力量训练经验和目标"),
            ("", "选择负荷：初学者 60-70% 1RM / 中级 70-80% / 高级 80-100%"),
            ("", "确定组数和次数（根据目标：力量/肥大/耐力）"),
            ("", "选择练习动作（单关节 vs 多关节）"),
            ("", "确定训练顺序（大肌群→小肌群，多关节→单关节）"),
            ("", "设定组间休息时间（力量3-5min / 肥大30-90s / 耐力<30s）"),
            ("", "确定频率：每个肌群每周≥2次"),
            ("", "制定渐进超负荷计划"),
            ("", "教授正确动作技术和呼吸模式"),
            ("", "记录训练日志（重量×次数×组数）"),
        ]
    },
    7: {
        "title": "慢性病客户安全运动清单",
        "items": [
            ("", "获取客户医生许可和运动限制说明"),
            ("", "了解客户用药情况及其对运动的影响"),
            ("", None),  # sub-list header
            ("", None),  # placeholder for sub-items
            ("", "运动前中后监测相关指标"),
            ("", "教会客户识别危险信号并立即停止运动"),
            ("", "调整训练环境（温度、湿度、海拔）"),
            ("", "与客户医疗团队保持沟通"),
            ("", "记录运动反应和不适症状"),
        ],
        "special": True  # mark for special handling
    },
    8: {
        "title": "特殊人群运动调整清单",
        "items": "special_ch8",
        "special": True
    },
    9: {
        "title": "损伤客户安全训练清单",
        "items": "special_ch9",
        "special": True
    }
}

# Build SOP HTML for simple chapters
def build_sop_html(ch_num):
    data = SOP_DATA[ch_num]
    html = f'<h4>{data["title"]}</h4>\n<ol class="sop-list">\n'
    for icon, text in data["items"]:
        if icon:
            html += f'  <li><span class="sop-icon">{icon}</span>{text}</li>\n'
        else:
            html += f'  <li>{text}</li>\n'
    html += '</ol>'
    return html

# Ch7 special
def build_ch7_sop():
    return '''<h4>慢性病客户安全运动清单</h4>
<ol class="sop-list">
  <li>获取客户医生许可和运动限制说明</li>
  <li>了解客户用药情况及其对运动的影响</li>
  <li>根据疾病类型调整运动处方：
    <ul>
      <li><span class="sop-icon">⚠️</span>高血压：避免瓦尔萨尔瓦动作、头部低于心脏</li>
      <li><span class="sop-icon">⚠️</span>糖尿病：监测血糖，预防低血糖，注意足部</li>
      <li><span class="sop-icon">⚠️</span>哮喘：备急救吸入器，充分热身</li>
      <li><span class="sop-icon">⚠️</span>心血管疾病：心率低于测试心率10-20次</li>
      <li><span class="sop-icon">⚠️</span>关节炎：无痛范围内训练，低冲击</li>
      <li><span class="sop-icon">⚠️</span>骨质疏松：避免脊柱屈曲和高冲击</li>
    </ul>
  </li>
  <li>运动前中后监测相关指标</li>
  <li>教会客户识别危险信号并立即停止运动</li>
  <li>调整训练环境（温度、湿度、海拔）</li>
  <li>与客户医疗团队保持沟通</li>
  <li>记录运动反应和不适症状</li>
</ol>'''

# Ch8 special
def build_ch8_sop():
    return '''<h4>特殊人群运动调整清单</h4>
<ol class="sop-list">
  <li>儿童青少年：
    <ul>
      <li>关注动作技能发展，避免过度训练</li>
      <li>力量训练从轻负荷开始，注重正确技术</li>
      <li>避免高温环境</li>
    </ul>
  </li>
  <li>孕妇：
    <ul>
      <li>获取医生许可</li>
      <li>避免仰卧位（孕中期后）、接触性运动</li>
      <li>注意补水和体温控制</li>
      <li>产后逐步恢复（顺产数天/剖宫产6-8周）</li>
    </ul>
  </li>
  <li>老年人：
    <ul>
      <li>重点：预防跌倒（平衡训练）</li>
      <li>力量训练保持独立生活能力</li>
      <li>关注心血管安全性</li>
      <li>柔韧性维持关节活动度</li>
    </ul>
  </li>
  <li>更年期女性：
    <ul>
      <li>抗阻训练预防骨质流失</li>
      <li>有氧运动保护心血管</li>
    </ul>
  </li>
  <li>根据年龄调整强度和进阶速度</li>
</ol>'''

# Ch9 special
def build_ch9_sop():
    return '''<h4>损伤客户安全训练清单</h4>
<ol class="sop-list">
  <li>了解客户损伤史和当前状态</li>
  <li>获取医生/物理治疗师的运动许可和限制</li>
  <li>肩部损伤：
    <ul>
      <li>避免过头大重量推举</li>
      <li>强化肩袖肌群和肩胛稳定肌</li>
      <li>注意肩峰下撞击的体征</li>
    </ul>
  </li>
  <li>下背痛：
    <ul>
      <li>核心稳定性训练（McGill三大练习）</li>
      <li>避免腰椎过度屈曲/旋转/侧屈</li>
      <li>逐步恢复日常活动</li>
    </ul>
  </li>
  <li>ACL重建术后：
    <ul>
      <li>遵循康复阶段protocol</li>
      <li>注意移植物类型的训练差异</li>
    </ul>
  </li>
  <li>膝部问题（PFPS）：
    <ul>
      <li>避免深蹲&gt;90°和膝外翻</li>
      <li>强化股四头肌（尤其VMO）</li>
    </ul>
  </li>
  <li>踝关节：
    <ul>
      <li>注意ATFL损伤史</li>
      <li>加强本体感觉训练</li>
    </ul>
  </li>
  <li>记录训练中的疼痛评分（0-10）</li>
  <li>疼痛&gt;3分立即调整或停止</li>
</ol>'''

BUILDERS = {
    7: build_ch7_sop,
    8: build_ch8_sop,
    9: build_ch9_sop,
}

results = []
for ch in range(1, 10):
    fpath = os.path.join(BASE, f"ch{ch}.html")
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    sop_div = soup.find(id='tab-sop')
    
    if not sop_div:
        results.append(f"Ch{ch}: tab-sop NOT FOUND")
        continue
    
    # Build new SOP content
    if ch in BUILDERS:
        new_html = BUILDERS[ch]()
    else:
        new_html = build_sop_html(ch)
    
    # Clear existing content and set new
    sop_div.clear()
    new_soup = BeautifulSoup(new_html, 'html.parser')
    for child in new_soup.children:
        sop_div.append(child)
    
    # Write back
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    
    results.append(f"Ch{ch}: ✅ Updated")

for r in results:
    print(r)
