#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诸神议事厅 · 最终完整版（绝无精简）
功能：多圣贤辩论、自由对话、记忆库、自定义圣贤、头像生成（身份匹配）、领域识别、导出报告
视觉：暖白高级 · 毛玻璃 · 古风沉浸式
"""

import subprocess
import sys
import importlib
import json
import requests
import time
import socket
import re
from collections import defaultdict
import random
import os
import base64
from flask import Flask, render_template_string, request, Response, jsonify, send_from_directory
from dotenv import load_dotenv
from typing import List, Tuple

# ==================== 1. 自动安装依赖 ====================
required_packages = ["flask", "python-dotenv", "requests"]

def install_package(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])

def check_and_install():
    print("🔍 正在检查运行环境...")
    for pkg in required_packages:
        try:
            importlib.import_module(pkg)
            print(f"   ✅ {pkg} 已安装")
        except ImportError:
            print(f"   ⏳ {pkg} 未安装，正在自动安装...")
            try:
                install_package(pkg)
                print(f"   ✅ {pkg} 安装成功")
            except Exception as e:
                print(f"   ❌ {pkg} 安装失败，请手动执行：pip install {pkg}")
                sys.exit(1)
    print("✅ 环境检查完成！\n")

check_and_install()

# ==================== 2. 导入主程序库 ====================
load_dotenv()

# ==================== 3. 配置 ====================
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
AGNES_BASE_URL = "https://api.agnes-ai.cn/v1"
AGNES_TEXT_MODEL = "agnes-2.5-flash"
AGNES_IMAGE_MODEL = "agnes-image-2.1-flash"
REQUEST_TIMEOUT = 120
MAX_TOKENS = 1024

AVATAR_DIR = os.path.join(os.path.dirname(__file__), 'static', 'avatars')
os.makedirs(AVATAR_DIR, exist_ok=True)

# ==================== 4. 默认圣贤配置 ====================
DEFAULT_SAGES = {
    "孔子": {
        "emoji": "🧓",
        "core_idea": "仁、礼、中庸，以德治国",
        "system": "你是孔子，春秋时期鲁国人，儒家学派创始人。说话多用对偶、排比，善用比喻，语气温和但坚定。"
    },
    "苏格拉底": {
        "emoji": "🧠",
        "core_idea": "精神助产术，认识你自己",
        "system": "你是苏格拉底，古希腊雅典公民，自称'精神助产士'。几乎全篇用反问句，从不直接给答案，擅长拆解问题。"
    },
    "尼采": {
        "emoji": "⚡",
        "core_idea": "权力意志，超人哲学，重估一切价值",
        "system": "你是尼采，德国哲学家，自称'用锤子思考'。短句、断句、感叹句为主，语气傲慢、狂热、挑衅感强。"
    },
    "富兰克林": {
        "emoji": "🦅",
        "core_idea": "实用主义、勤俭、经验主义",
        "system": "你是本杰明·富兰克林，美国开国元勋、印刷商、发明家。说话简洁、干脆，善用数字、事实、日常经验来论证。"
    }
}

# ==================== 5. 领域-圣贤映射 ====================
DOMAIN_SAGES = {
    "哲学伦理": {
        "sages": {
            "孔子": {"emoji": "🧓", "system": DEFAULT_SAGES["孔子"]["system"]},
            "苏格拉底": {"emoji": "🧠", "system": DEFAULT_SAGES["苏格拉底"]["system"]},
            "尼采": {"emoji": "⚡", "system": DEFAULT_SAGES["尼采"]["system"]},
            "康德": {"emoji": "📐", "system": "你是康德，德国哲学家，核心：绝对命令、先验理性。说话严谨、逻辑性强。"},
            "亚里士多德": {"emoji": "📜", "system": "你是亚里士多德，古希腊哲学家，核心：逻辑学、伦理学、政治学。说话条理分明。"}
        },
        "select_count": 4
    },
    "经济投资": {
        "sages": {
            "亚当·斯密": {"emoji": "💼", "system": "你是亚当·斯密，经济学之父，核心：看不见的手、分工理论。说话冷静务实。"},
            "凯恩斯": {"emoji": "📊", "system": "你是凯恩斯，宏观经济学奠基人，核心：有效需求、政府干预。说话果断。"},
            "巴菲特": {"emoji": "💰", "system": "你是巴菲特，投资大师，核心：价值投资、长期持有。说话简洁务实。"},
            "索罗斯": {"emoji": "🌪️", "system": "你是索罗斯，金融巨鳄，核心：反身性理论。说话犀利，关注市场心理。"},
            "马克思": {"emoji": "🔨", "system": "你是马克思，经济学与哲学思想家，核心：剩余价值、阶级斗争。说话充满批判性。"}
        },
        "select_count": 4
    },
    "心理情感": {
        "sages": {
            "弗洛伊德": {"emoji": "🛋️", "system": "你是弗洛伊德，精神分析学创始人，核心：潜意识、童年经验。说话深具洞察力。"},
            "荣格": {"emoji": "🌙", "system": "你是荣格，分析心理学创始人，核心：集体无意识、原型。说话富有象征性。"},
            "阿德勒": {"emoji": "👤", "system": "你是阿德勒，个体心理学创始人，核心：自卑感、社会兴趣。说话温暖而具有鼓励性。"},
            "马斯洛": {"emoji": "📈", "system": "你是马斯洛，人本主义心理学先驱，核心：需求层次、自我实现。说话积极向上。"}
        },
        "select_count": 4
    },
    "商业管理": {
        "sages": {
            "彼得·德鲁克": {"emoji": "📘", "system": "你是彼得·德鲁克，现代管理学之父，核心：目标管理、知识工作者。说话清晰务实。"},
            "稻盛和夫": {"emoji": "⛩️", "system": "你是稻盛和夫，日本经营之圣，核心：阿米巴经营、敬天爱人。说话富有哲学底蕴。"},
            "杰克·韦尔奇": {"emoji": "⚔️", "system": "你是杰克·韦尔奇，前GE CEO，核心：数一数二战略、领导力。说话果断，富有激情。"},
            "马可·奥勒留": {"emoji": "🏛️", "system": "你是马可·奥勒留，古罗马皇帝、斯多葛学派哲学家，核心：坚韧、理性。说话冷静平和。"}
        },
        "select_count": 4
    },
    "科学技术": {
        "sages": {
            "爱因斯坦": {"emoji": "⚛️", "system": "你是爱因斯坦，物理学家，核心：相对论、量子理论。说话充满想象力。"},
            "图灵": {"emoji": "💻", "system": "你是图灵，计算机科学之父，核心：图灵机、人工智能。说话逻辑清晰。"},
            "费曼": {"emoji": "🎲", "system": "你是费曼，物理学家，核心：量子电动力学。说话幽默风趣。"},
            "达尔文": {"emoji": "🌿", "system": "你是达尔文，进化论奠基人，核心：自然选择、物种起源。说话细腻严谨。"}
        },
        "select_count": 4
    },
    "政治治理": {
        "sages": {
            "柏拉图": {"emoji": "🏛️", "system": "你是柏拉图，古希腊哲学家，核心：理想国、理念论。说话理想主义。"},
            "马基雅维利": {"emoji": "🗡️", "system": "你是马基雅维利，政治学家，核心：君主论。说话冷静犀利。"},
            "卢梭": {"emoji": "📜", "system": "你是卢梭，启蒙思想家，核心：社会契约论、人民主权。说话充满批判性。"},
            "孟子": {"emoji": "🧘", "system": "你是孟子，儒家思想家，核心：性善论、仁政。说话充满浩然之气。"}
        },
        "select_count": 4
    }
}

FALLBACK_SAGES = {
    "孔子": {"emoji": "🧓", "system": DEFAULT_SAGES["孔子"]["system"]},
    "苏格拉底": {"emoji": "🧠", "system": DEFAULT_SAGES["苏格拉底"]["system"]},
    "尼采": {"emoji": "⚡", "system": DEFAULT_SAGES["尼采"]["system"]},
    "富兰克林": {"emoji": "🦅", "system": DEFAULT_SAGES["富兰克林"]["system"]}
}

# ==================== 6. 记忆库 ====================
class Memory:
    def __init__(self):
        self.history = defaultdict(list)
    
    def add_speech(self, name, content):
        self.history[name].append(content)
    
    def get_history(self, name, limit=3):
        return self.history[name][-limit:] if self.history[name] else []

memory = Memory()

# ==================== 7. 风格模板 ====================
def get_style_template(role_name, core_idea=""):
    return f"""
你是{role_name}。{core_idea}

【输出要求】
1. 一次性完整表达你的观点，不要截断，不要使用省略号。
2. 不要使用星号（*）、下划线（_）、反引号（`）等特殊符号。
3. 不要输出 Markdown 格式、代码块或列表符号。
4. 每个段落用句号或分号分隔，确保自然流畅。
5. 每次回答控制在 200-400 字之间。
6. 不要使用"首先、其次、最后"这类模板化开场，直接用观点切入。
"""

# ==================== 8. 自定义圣贤生成 ====================
def generate_sage_system(name, description):
    prompt = f"""请为一位名为「{name}」的思想家生成一段人设描述。
用户给的核心描述是：{description}
请扩展为完整的角色卡，包含：
1. 核心思想（一句话概括）
2. 说话风格（3个关键词）
3. 典型句式（1-2个例句）
4. 避讳内容（1-2个）
输出控制在100字以内。"""
    
    url = f"{AGNES_BASE_URL}/chat/completions"
    payload = {
        "model": AGNES_TEXT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 300,
        "stream": False
    }
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            system = resp.json()["choices"][0]["message"]["content"]
            return get_style_template(name, system)
        else:
            return get_style_template(name, description)
    except:
        return get_style_template(name, description)

# ==================== 9. 头像生成（身份匹配） ====================
def generate_avatar_image(sage_name):
    # 按身份定制的提示词库
    style_map = {
        # 中国思想家
        "孔子": "中国古代思想家孔子，春秋时期，汉服，温文尔雅，水墨风格，高清，半身肖像",
        "孟子": "中国古代思想家孟子，战国时期，儒雅，汉服，水墨风格，高清，半身肖像",
        "老子": "中国古代思想家老子，道骨仙风，汉服，水墨风格，高清，半身肖像",
        "庄子": "中国古代哲学家庄子，超然，道袍，水墨风格，高清，半身肖像",
        "王阳明": "中国古代哲学家王阳明，明代，儒服，庄重，水墨风格，高清，半身肖像",
        "韩非子": "中国古代法家思想家韩非子，战国时期，法家气质，汉服，水墨风格，高清，半身肖像",
        "孙子": "中国古代军事思想家孙子，铠甲，战国风格，水墨风格，高清，半身肖像",
        "朱熹": "南宋理学家朱熹，儒服，水墨风格，高清，半身肖像",
        "司马迁": "中国古代史学家司马迁，胡须，汉服，水墨风格，高清，半身肖像",
        "诸葛亮": "三国时期政治家诸葛亮，羽扇纶巾，水墨风格，高清，半身肖像",
        "李白": "唐代诗人李白，飘逸，水墨风格，高清，半身肖像",
        "杜甫": "唐代诗人杜甫，忧国忧民，水墨风格，高清，半身肖像",
        "曹操": "三国时期政治家曹操，枭雄气质，铠甲或王服，水墨风格，高清，半身肖像",
        # 古希腊
        "苏格拉底": "古希腊哲学家苏格拉底，秃顶，有胡须，希腊式长袍，古典雕塑风格，高清，半身肖像",
        "柏拉图": "古希腊哲学家柏拉图，有胡须，希腊式长袍，古典雕塑风格，高清，半身肖像",
        "亚里士多德": "古希腊哲学家亚里士多德，有胡须，希腊式长袍，古典雕塑风格，高清，半身肖像",
        "伊壁鸠鲁": "古希腊哲学家伊壁鸠鲁，胡须，希腊长袍，古典雕塑风格，高清，半身肖像",
        "第欧根尼": "古希腊犬儒哲学家第欧根尼，木桶，不修边幅，古典风格，高清，半身肖像",
        # 德国
        "尼采": "德国哲学家尼采，浓密胡须，严肃眼神，欧洲油画风格，高清，半身肖像",
        "康德": "德国哲学家康德，18世纪德国服饰，严谨，欧洲油画风格，高清，半身肖像",
        "马克思": "德国哲学家马克思，大胡子，19世纪风格，欧洲油画风格，高清，半身肖像",
        "黑格尔": "德国哲学家黑格尔，有胡须，19世纪风格，欧洲油画风格，高清，半身肖像",
        "叔本华": "德国哲学家叔本华，胡须，悲观眼神，欧洲油画风格，高清，半身肖像",
        "弗洛伊德": "奥地利心理学家弗洛伊德，有胡须，雪茄，欧洲油画风格，高清，半身肖像",
        "荣格": "瑞士心理学家荣格，学者气质，20世纪风格，欧洲风格，高清，半身肖像",
        "阿德勒": "奥地利心理学家阿德勒，温和，20世纪，欧洲风格，高清，半身肖像",
        # 美国/英国
        "富兰克林": "美国开国元勋本杰明·富兰克林，秃顶，眼镜，18世纪美国肖像画，高清，半身肖像",
        "亚当·斯密": "苏格兰经济学家亚当·斯密，18世纪服饰，英国肖像画风格，高清，半身肖像",
        "凯恩斯": "英国经济学家凯恩斯，20世纪风格，西装，现代肖像，高清，半身肖像",
        "巴菲特": "美国投资家巴菲特，眼镜，和蔼笑容，照片写实风格，高清，半身肖像",
        "索罗斯": "美国金融家索罗斯，锐利眼神，照片写实风格，高清，半身肖像",
        "彼得·德鲁克": "德鲁克，美国管理学家，学者气质，现代肖像，高清，半身肖像",
        "杰克·韦尔奇": "韦尔奇，美国企业家，自信眼神，现代肖像，高清，半身肖像",
        "马斯洛": "马斯洛，美国心理学家，20世纪，现代肖像，高清，半身肖像",
        # 法国
        "卢梭": "法国启蒙思想家卢梭，18世纪法国服饰，法国肖像画，高清，半身肖像",
        "伏尔泰": "法国启蒙思想家伏尔泰，胡须，18世纪服饰，法国肖像画，高清，半身肖像",
        "笛卡尔": "笛卡尔，法国哲学家，胡须，17世纪风格，欧洲古典，高清，半身肖像",
        "萨特": "萨特，法国哲学家，20世纪，法国风格，高清，半身肖像",
        "加缪": "加缪，法国作家，20世纪，法国风格，高清，半身肖像",
        # 日本
        "稻盛和夫": "稻盛和夫，日本企业家，和服，严肃，日本风格，高清，半身肖像",
        "铃木大拙": "铃木大拙，日本禅师，和服，日本风格，高清，半身肖像",
        "西田几多郎": "西田几多郎，日本哲学家，和服，日本风格，高清，半身肖像",
        # 科学家
        "爱因斯坦": "爱因斯坦，物理学家，白发，分头，照片写实风格，高清，半身肖像",
        "图灵": "图灵，计算机科学家，20世纪风格，照片写实风格，高清，半身肖像",
        "费曼": "费曼，物理学家，20世纪风格，照片写实风格，高清，半身肖像",
        "达尔文": "达尔文，生物学家，大胡子，19世纪风格，欧洲油画，高清，半身肖像",
        "牛顿": "牛顿，物理学家，17世纪风格，欧洲古典，高清，半身肖像",
        "伽利略": "伽利略，科学家，17世纪，胡须，欧洲古典，高清，半身肖像",
        "居里夫人": "居里夫人，物理学家，1900年代，照片写实风格，高清，半身肖像",
        # 其他
        "马基雅维利": "马基雅维利，意大利政治哲学家，文艺复兴风格，西方古典，高清，半身肖像",
        "维特根斯坦": "维特根斯坦，奥地利哲学家，20世纪，欧洲风格，高清，半身肖像",
        "乔布斯": "乔布斯，美国企业家，黑毛衣，眼镜，现代风格，高清，半身肖像",
        "马斯克": "马斯克，美国企业家，现代，高清，半身肖像",
        "奥勒留": "奥勒留，古罗马皇帝，铠甲，古罗马雕塑风格，高清，半身肖像",
        "斯宾诺莎": "斯宾诺莎，荷兰哲学家，17世纪，欧洲古典，高清，半身肖像",
        "洛克": "洛克，英国哲学家，17世纪，英国肖像画，高清，半身肖像",
        "边沁": "边沁，英国哲学家，18世纪，英国肖像画，高清，半身肖像",
        "密尔": "密尔，英国哲学家，19世纪，英国肖像画，高清，半身肖像",
        "罗素": "罗素，英国哲学家，20世纪，英国肖像画，高清，半身肖像",
        "维柯": "维柯，意大利哲学家，18世纪，意大利风格，高清，半身肖像",
        "托克维尔": "托克维尔，法国思想家，19世纪，法国风格，高清，半身肖像",
        "柏克": "柏克，英国思想家，18世纪，英国肖像画，高清，半身肖像"
    }

    # 智能推断（自定义圣贤）
    def infer_style(name):
        if name.endswith("子") or name in ["老子", "庄子", "孔子", "孟子", "荀子"]:
            return "中国古代思想家"
        elif name.endswith("斯") or name in ["苏格拉底", "柏拉图", "亚里士多德"]:
            return "古希腊思想家"
        elif name.endswith("德") or name in ["康德", "海德格尔", "阿德勒"]:
            return "德国思想家"
        elif name.endswith("尔") or name in ["尼采", "黑格尔", "叔本华"]:
            return "德国思想家"
        elif name.endswith("夫") or name in ["稻盛和夫"]:
            return "日本思想家"
        elif name.endswith("逊") or name in ["达尔文"]:
            return "英国思想家"
        else:
            return "思想家"

    # 构建提示词
    if sage_name in style_map:
        prompt = style_map[sage_name] + "，高清，精细，半身像"
    else:
        inferred = infer_style(sage_name)
        prompt = f"{sage_name}，{inferred}，半身肖像，高清，精细"

    # 调用图像生成API
    url = f"{AGNES_BASE_URL}/images/generations"
    payload = {
        "model": AGNES_IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": "1K"
    }
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and len(data['data']) > 0 and 'url' in data['data'][0]:
                img_url = data['data'][0]['url']
                img_resp = requests.get(img_url, timeout=30)
                if img_resp.status_code == 200:
                    file_path = os.path.join(AVATAR_DIR, f"{sage_name}.png")
                    with open(file_path, 'wb') as f:
                        f.write(img_resp.content)
                    print(f"✅ 头像保存成功: {sage_name} ({len(img_resp.content)} 字节)")
                    return file_path
        return None
    except Exception as e:
        print(f"❌ 头像生成异常 ({sage_name}): {e}")
        return None

def ensure_avatar(name):
    """确保头像存在，不存在则生成"""
    file_path = os.path.join(AVATAR_DIR, f"{name}.png")
    if not os.path.exists(file_path):
        print(f"⏳ 生成头像: {name}")
        generate_avatar_image(name)
    return file_path

# ==================== 10. 调用 Agnes AI 文本 API ====================
def call_local_llm(messages, temp=0.8, max_retries=2):
    url = f"{AGNES_BASE_URL}/chat/completions"
    payload = {
        "model": AGNES_TEXT_MODEL,
        "messages": messages,
        "temperature": temp,
        "max_tokens": MAX_TOKENS,
        "stop": ["**", "```", "---", "* ", "_ "],
        "stream": False
    }
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ API 错误 ({resp.status_code})"
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return "❌ 无法连接 Agnes AI 服务"
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return f"❌ 请求超时（{REQUEST_TIMEOUT}秒）"
        except Exception as e:
            return f"❌ 错误：{e}"
    return "❌ 未知错误"

# ==================== 11. 工具函数 ====================
def find_available_port(start_port=5000, max_attempts=10):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return None

def check_agness_api(max_retries=3):
    url = f"{AGNES_BASE_URL}/models"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}"}
    for i in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                return True
        except:
            pass
        if i < max_retries - 1:
            time.sleep(2)
    return False

# ==================== 12. 领域识别与圣贤匹配 ====================
def identify_domain(topic):
    prompt = f"""
请分析以下问题属于哪个领域。只输出领域名称，不要解释。

可选领域列表：哲学伦理、经济投资、政治治理、心理情感、科学技术、商业管理。

如果无法判断，输出"综合"。

问题：{topic}
领域："""
    messages = [{"role": "user", "content": prompt}]
    response = call_local_llm(messages, temp=0.3)
    if response.startswith("❌"):
        return "综合"
    domain = response.strip()
    valid_domains = ["哲学伦理", "经济投资", "政治治理", "心理情感", "科学技术", "商业管理", "综合"]
    return domain if domain in valid_domains else "综合"

def select_top_sages(domain, topic, count=4):
    if domain not in DOMAIN_SAGES:
        return list(FALLBACK_SAGES.items())[:count]
    
    sage_dict = DOMAIN_SAGES[domain]["sages"]
    sage_names = list(sage_dict.keys())
    target_count = DOMAIN_SAGES[domain].get("select_count", count)
    
    if len(sage_names) <= target_count:
        return list(sage_dict.items())
    
    prompt = f"""
问题：{topic}
请从以下圣贤中选择最匹配的 {target_count} 位来辩论这个问题：
{', '.join(sage_names)}
只输出名字，用逗号分隔，不要解释。
"""
    messages = [{"role": "user", "content": prompt}]
    response = call_local_llm(messages, temp=0.3)
    
    if response.startswith("❌"):
        selected_names = sage_names[:target_count]
    else:
        selected_names = [name.strip() for name in response.split(',') if name.strip() in sage_names]
        if len(selected_names) < target_count:
            selected_names = sage_names[:target_count]
    
    result = []
    for name in selected_names[:target_count]:
        if name in sage_dict:
            result.append((name, sage_dict[name]))
    
    if not result:
        return list(FALLBACK_SAGES.items())[:count]
    return result

# ==================== 13. 流式生成器 ====================
def generate_debate(topic, mode, sages, rounds=2, max_speeches=12):
    try:
        default_names = set(DEFAULT_SAGES.keys())
        current_names = set(sages.keys())
        is_default = (current_names == default_names)
        
        if is_default and mode == "debate":
            yield f"data: {json.dumps({'type': 'status', 'content': '🔍 正在分析问题领域...'})}\n\n"
            time.sleep(0.5)
            domain = identify_domain(topic)
            yield f"data: {json.dumps({'type': 'status', 'content': f'📂 识别领域：{domain}'})}\n\n"
            time.sleep(0.3)
            
            if domain in DOMAIN_SAGES:
                matched_sages = select_top_sages(domain, topic, count=4)
                if matched_sages:
                    new_sages = {}
                    for name, info in matched_sages:
                        new_sages[name] = info
                        # 确保头像存在
                        ensure_avatar(name)
                    sages = new_sages
                    sages_str = ",".join(sages.keys())
                    yield f"data: {json.dumps({'type': 'status', 'content': f'🧑‍🏫 已匹配圣贤：{sages_str}'})}\n\n"
                    time.sleep(0.5)
            else:
                yield f"data: {json.dumps({'type': 'status', 'content': 'ℹ️ 未匹配到专属圣贤，使用默认'})}\n\n"
                time.sleep(0.5)
        
        order = list(sages.keys())
        if not order:
            order = list(DEFAULT_SAGES.keys())
            sages = {name: DEFAULT_SAGES[name] for name in order}
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 圣贤列表为空，已恢复默认'})}\n\n"
            time.sleep(0.3)
        
        # 确保所有头像存在（包括自定义）
        for name in order:
            ensure_avatar(name)
        
        speeches = {name: "" for name in order}
        votes = {name: "" for name in order}
        
        custom_names = [n for n in order if n not in DEFAULT_SAGES]
        if custom_names:
            custom_names_str = ",".join(custom_names)
            yield f"data: {json.dumps({'type': 'status', 'content': f'🧑‍🏫 欢迎自定义圣贤：{custom_names_str}'})}\n\n"
            time.sleep(0.5)
        
        if mode == "debate":
            yield f"data: {json.dumps({'type': 'status', 'content': f'⚔️ 辩论模式 · 议题：{topic} · {rounds}轮'})}\n\n"
            time.sleep(0.5)
            
            for idx, name in enumerate(order):
                yield f"data: {json.dumps({'type': 'status', 'content': f'⏳ {name} 立论...（{idx+1}/{len(order)}）'})}\n\n"
                time.sleep(0.2)
                config = sages[name]
                style = get_style_template(name, config.get("core_idea", ""))
                history = memory.get_history(name, 3)
                memory_content = f"\n你之前说过：{' '.join(history[:2])}" if history else ""
                msg = [
                    {"role": "system", "content": style + memory_content},
                    {"role": "user", "content": f"议题：{topic}"}
                ]
                reply = call_local_llm(msg, temp=0.8)
                speeches[name] = f"【立论】\n{reply}"
                memory.add_speech(name, reply[:200])
                yield f"data: {json.dumps({'type': 'speech', 'name': name, 'content': speeches[name]})}\n\n"
                time.sleep(0.3)
            
            for round_num in range(rounds):
                yield f"data: {json.dumps({'type': 'status', 'content': f'⚡ 第 {round_num+1} 轮反驳'})}\n\n"
                time.sleep(0.3)
                for idx, name in enumerate(order):
                    target = order[(idx + 1) % len(order)]
                    yield f"data: {json.dumps({'type': 'status', 'content': f'⏳ {name} 反驳 {target}...'})}\n\n"
                    time.sleep(0.2)
                    target_speech = speeches[target]
                    style = get_style_template(name, sages[name].get("core_idea", ""))
                    history = memory.get_history(name, 2)
                    memory_str = f"你之前说过：{' '.join(history[:2])}" if history else ""
                    msg = [
                        {"role": "system", "content": style + f"\n你的对手{target}说：{target_speech[:200]}...\n{memory_str}"},
                        {"role": "user", "content": f"议题：{topic}"}
                    ]
                    reply = call_local_llm(msg, temp=0.9)
                    speeches[name] += f"\n\n【反驳 {target}】\n{reply}"
                    memory.add_speech(name, reply[:200])
                    yield f"data: {json.dumps({'type': 'speech', 'name': name, 'content': speeches[name]})}\n\n"
                    time.sleep(0.3)
            
            for idx, name in enumerate(order):
                yield f"data: {json.dumps({'type': 'status', 'content': f'🗳️ {name} 投票...'})}\n\n"
                time.sleep(0.2)
                style = get_style_template(name, sages[name].get("core_idea", ""))
                msg = [
                    {"role": "system", "content": style + "请明确表态：支持还是反对？只输出『支持』『反对』或『弃权』，并附一句简短理由。格式：【立场：X】理由：xxx"},
                    {"role": "user", "content": f"议题：{topic}"}
                ]
                votes[name] = call_local_llm(msg, temp=0.6)
                memory.add_speech(name, f"投票：{votes[name][:100]}")
                yield f"data: {json.dumps({'type': 'vote', 'name': name, 'content': votes[name]})}\n\n"
                time.sleep(0.2)
            
            yield f"data: {json.dumps({'type': 'status', 'content': '⚖️ 终审判官裁决...'})}\n\n"
            time.sleep(0.5)
            all_content = "\n".join([f"{name}: {speeches[name]}" for name in order])
            judge_msg = [
                {"role": "system", "content": "你是终审法官。综合所有辩论和投票，只输出一句话结论。格式：『最终答案：XXX』。不超过30个字。不要说过程、不要说分析。"},
                {"role": "user", "content": f"辩论记录：{all_content}\n投票：{votes}"}
            ]
            final_verdict = call_local_llm(judge_msg, temp=0.3)
            yield f"data: {json.dumps({'type': 'final', 'content': final_verdict})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'content': '✅ 辩论完成！'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        else:
            yield f"data: {json.dumps({'type': 'status', 'content': f'💬 自由对话 · 话题：{topic}'})}\n\n"
            time.sleep(0.5)
            conversation_history = []
            
            for name in order:
                context = "\n".join(conversation_history[-3:]) if conversation_history else f"话题是：{topic}"
                style = get_style_template(name, sages[name].get("core_idea", ""))
                msg = [
                    {"role": "system", "content": style + f"\n你正在和{'、'.join(order)}自由聊天。话题：{topic}。简短自然，50-200字。"},
                    {"role": "user", "content": f"{context}\n\n请开始发言。"}
                ]
                reply = call_local_llm(msg, temp=0.85)
                speeches[name] = reply
                conversation_history.append(f"{name}：{reply[:150]}")
                memory.add_speech(name, reply[:200])
                yield f"data: {json.dumps({'type': 'speech', 'name': name, 'content': reply})}\n\n"
                time.sleep(0.5)
            
            total_speeches = len(order)
            while total_speeches < max_speeches:
                last_speaker = order[(total_speeches - 1) % len(order)]
                candidates = [n for n in order if n != last_speaker]
                next_speaker = random.choice(candidates)
                context = "\n".join(conversation_history[-4:])
                style = get_style_template(next_speaker, sages[next_speaker].get("core_idea", ""))
                msg = [
                    {"role": "system", "content": style + f"\n自由聊天。话题：{topic}。自然接话，50-200字。"},
                    {"role": "user", "content": f"对话记录：\n{context}\n\n请继续。"}
                ]
                reply = call_local_llm(msg, temp=0.9)
                if len(reply) < 5 or "❌" in reply:
                    total_speeches += 1
                    continue
                speeches[next_speaker] = (speeches.get(next_speaker, "") + f"\n\n{reply}")[:800]
                conversation_history.append(f"{next_speaker}：{reply[:150]}")
                memory.add_speech(next_speaker, reply[:200])
                yield f"data: {json.dumps({'type': 'speech', 'name': next_speaker, 'content': speeches[next_speaker]})}\n\n"
                total_speeches += 1
                time.sleep(0.5)
            
            yield f"data: {json.dumps({'type': 'status', 'content': '✨ 生成结论...'})}\n\n"
            time.sleep(0.5)
            summary_prompt = f"用一句话总结以上对话的最终结论。不超过30个字。不要说过程。对话记录：{' '.join(conversation_history[-6:])}"
            msg = [{"role": "user", "content": summary_prompt}]
            summary = call_local_llm(msg, temp=0.4)
            if not summary or "❌" in summary:
                summary = "（结论生成失败）"
            summary_content = f"📝 结论\n\n{summary}"
            yield f"data: {json.dumps({'type': 'final', 'content': summary_content})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    except Exception as e:
        import traceback
        error_msg = f"❌ 辩论过程中发生错误：{str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

# ==================== 14. Flask 应用 ====================
app = Flask(__name__)
app.custom_sages = {}

@app.route('/static/avatars/<filename>')
def serve_avatar(filename):
    return send_from_directory(AVATAR_DIR, filename)

@app.route('/generate_avatar/<sage_name>', methods=['GET'])
def generate_avatar(sage_name):
    if sage_name not in DEFAULT_SAGES and sage_name not in app.custom_sages:
        return jsonify({'error': '圣贤不存在'}), 404
    file_path = ensure_avatar(sage_name)
    if not os.path.exists(file_path):
        return jsonify({'error': '生成失败'}), 500
    return jsonify({'url': f'/static/avatars/{sage_name}.png'})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/add_sage', methods=['POST'])
def add_sage():
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    if not name or not description:
        return jsonify({'status': 'error', 'message': '缺少名字或描述'})
    system = generate_sage_system(name, description)
    app.custom_sages[name] = system
    # 立即生成头像
    ensure_avatar(name)
    return jsonify({'status': 'ok', 'message': f'已生成圣贤 {name}'})

@app.route('/debate_stream')
def debate_stream():
    topic = request.args.get('topic', '').strip()
    mode = request.args.get('mode', 'debate')
    rounds = int(request.args.get('rounds', '2'))
    sages_str = request.args.get('sages', '')
    if not topic:
        def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': '请输入一个问题'})}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    sage_names = sages_str.split(',') if sages_str else list(DEFAULT_SAGES.keys())
    sages = {}
    for name in sage_names:
        if name in DEFAULT_SAGES:
            sages[name] = DEFAULT_SAGES[name]
        elif name in app.custom_sages:
            sages[name] = {'emoji': '🧐', 'system': app.custom_sages[name]}
        else:
            sages[name] = {'emoji': '🧐', 'system': f"你是{name}，一位思想家。"}
        # 确保头像
        ensure_avatar(name)
    max_speeches = 12 if mode == 'free' else 0
    return Response(
        generate_debate(topic, mode, sages, rounds, max_speeches),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )

# ==================== 15. HTML 模板（完整高级版） ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏛️ 诸神议事厅</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Noto Serif SC', 'Georgia', serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 30px 20px;
            background: #f5efe8;
            background-image: 
                radial-gradient(ellipse at 30% 20%, rgba(210,180,140,0.15) 0%, transparent 60%),
                radial-gradient(ellipse at 70% 80%, rgba(180,150,120,0.10) 0%, transparent 60%),
                radial-gradient(ellipse at 50% 100%, rgba(200,180,160,0.08) 0%, transparent 50%);
        }
        .container {
            max-width: 1400px;
            width: 100%;
            background: rgba(250,245,238,0.65);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-radius: 48px;
            padding: 40px 48px 48px;
            border: 1px solid rgba(180,160,140,0.15);
            box-shadow: 0 30px 80px rgba(120,90,60,0.08), 0 10px 30px rgba(120,90,60,0.04), inset 0 1px 0 rgba(255,248,240,0.6);
        }
        .header { text-align: center; margin-bottom: 32px; }
        .header h1 { font-size: 3rem; font-weight: 900; letter-spacing: 0.15em; color: #3d322a; text-shadow: 0 2px 20px rgba(160,130,100,0.08); margin-bottom: 6px; }
        .header .subtitle { font-size: 0.85rem; letter-spacing: 0.5em; color: rgba(120,100,80,0.4); font-weight: 400; text-transform: uppercase; }
        .header .divider { width: 80px; height: 1px; margin: 12px auto 0; background: linear-gradient(90deg, transparent, rgba(160,130,100,0.2), transparent); }
        .controls { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; justify-content: center; }
        .controls select, .controls input {
            padding: 10px 18px; background: rgba(245,238,230,0.6); border: 1px solid rgba(160,140,120,0.15); border-radius: 12px; color: #3d322a; font-size: 0.9rem; font-family: 'Noto Serif SC', serif; outline: none; transition: all 0.3s;
        }
        .controls select:focus, .controls input:focus { border-color: rgba(160,130,100,0.3); box-shadow: 0 0 30px rgba(160,130,100,0.05); }
        .controls select option { background: #f5efe8; color: #3d322a; }
        .custom-sage-area { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; justify-content: center; }
        .custom-sage-area input {
            padding: 10px 16px; background: rgba(245,238,230,0.6); border: 1px solid rgba(160,140,120,0.12); border-radius: 12px; color: #3d322a; font-size: 0.9rem; font-family: 'Noto Serif SC', serif; outline: none; transition: all 0.3s; width: 150px;
        }
        .custom-sage-area input::placeholder { color: rgba(120,100,80,0.3); }
        .custom-sage-area input:focus { border-color: rgba(160,130,100,0.3); }
        .custom-sage-area button {
            padding: 10px 20px; background: rgba(160,130,100,0.08); border: 1px solid rgba(160,140,120,0.15); border-radius: 12px; color: #3d322a; font-size: 0.9rem; font-family: 'Noto Serif SC', serif; cursor: pointer; transition: all 0.3s;
        }
        .custom-sage-area button:hover { background: rgba(160,130,100,0.15); border-color: rgba(160,130,100,0.25); }
        .sage-tag { display: inline-block; background: rgba(160,130,100,0.08); padding: 4px 14px; border-radius: 20px; font-size: 0.8rem; color: rgba(80,65,50,0.7); margin: 2px; border: 1px solid rgba(160,130,100,0.06); }
        .input-area { display: flex; gap: 12px; margin-bottom: 28px; flex-wrap: wrap; justify-content: center; }
        .input-area input {
            flex: 1 1 300px; padding: 16px 24px; background: rgba(245,238,230,0.5); border: 1px solid rgba(160,140,120,0.12); border-radius: 16px; color: #3d322a; font-size: 1rem; font-family: 'Noto Serif SC', serif; outline: none; transition: all 0.3s;
        }
        .input-area input::placeholder { color: rgba(120,100,80,0.3); }
        .input-area input:focus { border-color: rgba(160,130,100,0.3); box-shadow: 0 0 40px rgba(160,130,100,0.04); }
        .btn-primary {
            padding: 16px 36px; background: linear-gradient(135deg, rgba(160,130,100,0.15), rgba(140,110,85,0.08)); border: 1px solid rgba(160,130,100,0.2); border-radius: 16px; color: #3d322a; font-size: 1rem; font-weight: 600; font-family: 'Noto Serif SC', serif; letter-spacing: 0.08em; cursor: pointer; transition: all 0.4s;
        }
        .btn-primary:hover { background: linear-gradient(135deg, rgba(160,130,100,0.25), rgba(140,110,85,0.15)); border-color: rgba(160,130,100,0.35); box-shadow: 0 4px 30px rgba(160,130,100,0.10); transform: translateY(-1px); }
        .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
        .btn-export {
            padding: 16px 24px; background: rgba(200,185,170,0.15); border: 1px solid rgba(160,140,120,0.08); border-radius: 16px; color: rgba(80,65,50,0.5); font-size: 0.9rem; font-family: 'Noto Serif SC', serif; cursor: pointer; transition: all 0.3s;
        }
        .btn-export:hover { background: rgba(200,185,170,0.25); border-color: rgba(160,140,120,0.15); color: rgba(80,65,50,0.7); }
        .status-bar { text-align: center; padding: 14px 20px; margin-bottom: 24px; background: rgba(240,232,222,0.4); border-radius: 16px; border: 1px solid rgba(160,140,120,0.06); color: rgba(80,65,50,0.6); font-size: 0.95rem; min-height: 54px; letter-spacing: 0.04em; }
        .error-box { background: rgba(180,80,60,0.08); border: 1px solid rgba(180,80,60,0.12); border-radius: 16px; padding: 16px 24px; margin-bottom: 20px; color: rgba(140,70,50,0.8); display: none; }
        .error-box.show { display: block; }
        .sages-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 18px; margin-bottom: 28px; }
        @media (max-width:1000px){ .sages-grid { grid-template-columns: repeat(2,1fr); } }
        @media (max-width:550px){ .sages-grid { grid-template-columns: 1fr; } }
        .sage-card {
            background: rgba(250,245,238,0.55); border-radius: 24px; padding: 20px 22px 22px; border: 1px solid rgba(160,140,120,0.08); transition: all 0.4s ease; position: relative; overflow: hidden;
        }
        .sage-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, rgba(160,130,100,0.12), transparent); }
        .sage-card:hover { border-color: rgba(160,130,100,0.15); background: rgba(250,245,238,0.8); transform: translateY(-2px); box-shadow: 0 8px 30px rgba(120,90,60,0.06); }
        .sage-card.updating { border-color: rgba(160,130,100,0.25); box-shadow: 0 0 40px rgba(160,130,100,0.04); }
        .sage-header { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
        .avatar { width: 44px; height: 44px; border-radius: 50%; cursor: pointer; border: 2px solid rgba(160,140,120,0.12); object-fit: cover; transition: all 0.4s; flex-shrink: 0; background: rgba(240,232,222,0.5); }
        .avatar:hover { border-color: rgba(160,130,100,0.4); transform: scale(1.05); box-shadow: 0 0 30px rgba(160,130,100,0.10); }
        .avatar.avatar-speaking { border-color: #c9b037; animation: speakGlowLight 1.2s ease-in-out infinite; }
        @keyframes speakGlowLight {
            0% { box-shadow: 0 0 10px rgba(201,176,55,0.10); }
            50% { box-shadow: 0 0 30px rgba(201,176,55,0.20), 0 0 60px rgba(201,176,55,0.04); }
            100% { box-shadow: 0 0 10px rgba(201,176,55,0.10); }
        }
        .sage-name { font-size: 1.1rem; font-weight: 700; color: #3d322a; letter-spacing: 0.06em; }
        .sage-name .emoji { font-size: 0.9rem; opacity: 0.5; }
        .speech { font-size: 0.92rem; line-height: 1.9; color: #4a3d32; background: rgba(245,238,230,0.5); border-left: 3px solid rgba(160,130,100,0.15); border-radius: 8px; padding: 14px 18px; min-height: 70px; max-height: 280px; overflow-y: auto; margin-bottom: 12px; font-family: 'Noto Serif SC', serif; }
        .speech .placeholder { color: rgba(120,100,80,0.25); font-style: italic; }
        .speech::-webkit-scrollbar { width: 3px; }
        .speech::-webkit-scrollbar-track { background: transparent; }
        .speech::-webkit-scrollbar-thumb { background: rgba(160,130,100,0.15); border-radius: 10px; }
        .vote { font-size: 0.85rem; color: #5a4d40; background: rgba(240,232,222,0.4); border-left: 3px solid #c9b037; border-radius: 6px; padding: 10px 14px; min-height: 28px; font-family: 'Noto Serif SC', serif; }
        .vote .placeholder { color: rgba(120,100,80,0.2); font-style: italic; }
        .final-box { background: rgba(250,245,238,0.7); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border: 1px solid rgba(160,140,120,0.10); border-radius: 24px; padding: 28px 32px; margin-top: 8px; color: #3d322a; font-family: 'Noto Serif SC', serif; line-height: 1.9; box-shadow: 0 0 60px rgba(160,130,100,0.02); }
        .final-box strong { color: #8b7a5a; font-weight: 700; }
        .final-box .placeholder { color: rgba(120,100,80,0.2); font-style: italic; }
        .footer { margin-top: 28px; text-align: center; font-size: 0.75rem; color: rgba(120,100,80,0.15); letter-spacing: 0.08em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ 诸神议事厅</h1>
            <p class="subtitle">· 圣贤对谈 · 千年一辩 ·</p>
            <div class="divider"></div>
        </div>
        
        <div class="controls">
            <select id="modeSelect">
                <option value="debate">⚔️ 辩论模式</option>
                <option value="free">💬 自由对话</option>
            </select>
            <input type="number" id="roundsInput" value="2" min="1" max="5" style="width:70px;">
            <label style="font-size:0.8rem;color:rgba(120,100,80,0.4);">轮数</label>
        </div>
        
        <div class="custom-sage-area">
            <input type="text" id="customName" placeholder="圣贤名字" />
            <input type="text" id="customDesc" placeholder="一句话描述" style="width:200px;" />
            <button onclick="addCustomSage()">➕ 添加</button>
            <span id="customSageList"></span>
        </div>
        
        <div class="input-area">
            <input type="text" id="topic" placeholder="请提出你的议题..." />
            <button id="debateBtn" class="btn-primary" onclick="startDebate()">🔥 点燃辩论之火</button>
            <button onclick="exportReport()" class="btn-export">📄 导出报告</button>
        </div>
        
        <div id="statusBar" class="status-bar">
            <span class="status-text">💡 输入议题，选择模式，点击开始</span>
        </div>
        <div id="errorBox" class="error-box"></div>
        
        <div id="resultArea">
            <div class="sages-grid" id="sagesGrid"></div>
            <div id="finalVerdict"><div class="final-box"><span class="placeholder">⚖️ 等待判决...</span></div></div>
        </div>
        
        <div class="footer">· 圣贤之辩 · 智识之光 ·</div>
    </div>
    
    <script>
        const defaultSages = ["孔子","苏格拉底","尼采","富兰克林"];
        const emojiMap = {"孔子":"🧓","苏格拉底":"🧠","尼采":"⚡","富兰克林":"🦅"};
        let customSages = [];
        let currentEventSource = null;
        let allSpeeches = {};
        let currentlySpeaking = null;
        let currentSages = defaultSages.slice();  // 跟踪当前圣贤列表
        
        function initCards(sagesList) {
            const grid = document.getElementById('sagesGrid');
            grid.innerHTML = '';
            const sages = sagesList || getCurrentSages();
            sages.forEach(name => {
                const card = document.createElement('div');
                card.className = 'sage-card';
                card.id = 'card-' + name;
                const emoji = emojiMap[name] || '🧐';
                card.innerHTML = `
                    <div class="sage-header">
                        <img id="avatar-${name}" class="avatar" 
                             src="/static/avatars/${encodeURIComponent(name)}.png" 
                             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2244%22 height=%2244%22%3E%3Crect width=%2244%22 height=%2244%22 fill=%22%23f0e8d8%22/%3E%3Ctext x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2222%22%3E${emoji}%3C/text%3E%3C/svg%3E'"
                             onclick="regenerateAvatar('${name}')" />
                        <span class="sage-name">${name} <span class="emoji">${emoji}</span></span>
                    </div>
                    <div class="speech"><span class="placeholder">等待发言...</span></div>
                    <div class="vote"><span class="placeholder">等待投票...</span></div>
                `;
                grid.appendChild(card);
            });
            document.getElementById('finalVerdict').innerHTML = '<div class="final-box"><span class="placeholder">⚖️ 等待判决...</span></div>';
            allSpeeches = {};
            currentSages = sages;
        }
        
        function getCurrentSages() {
            const all = [...defaultSages];
            customSages.forEach(s => { if (!all.includes(s)) all.push(s); });
            return all;
        }
        
        function addCustomSage() {
            const name = document.getElementById('customName').value.trim();
            const desc = document.getElementById('customDesc').value.trim();
            if (!name || !desc) { alert('请输入名字和描述'); return; }
            if (customSages.includes(name)) { alert('该圣贤已存在'); return; }
            customSages.push(name);
            fetch('/add_sage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, description: desc })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ok') {
                    const list = document.getElementById('customSageList');
                    const tag = document.createElement('span');
                    tag.className = 'sage-tag';
                    tag.textContent = name;
                    list.appendChild(tag);
                    document.getElementById('customName').value = '';
                    document.getElementById('customDesc').value = '';
                    initCards();
                    updateStatus(`✅ 已添加圣贤：${name}`);
                }
            });
        }
        
        function regenerateAvatar(name) {
            fetch(`/generate_avatar/${encodeURIComponent(name)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.url) {
                        const img = document.getElementById(`avatar-${name}`);
                        img.src = data.url + '?t=' + new Date().getTime();
                        updateStatus(`✅ 头像已更新：${name}`);
                    } else {
                        alert('头像生成失败，请重试');
                    }
                })
                .catch(err => console.error(err));
        }
        
        function updateSpeech(name, content) {
            const card = document.getElementById('card-' + name);
            if (!card) {
                // 如果卡片不存在，尝试重新创建
                const sages = getCurrentSages();
                if (sages.includes(name)) {
                    initCards(sages);
                } else {
                    // 如果名字不在列表中，则添加并重建
                    const newList = [...sages, name];
                    initCards(newList);
                }
                // 递归调用更新
                setTimeout(() => updateSpeech(name, content), 100);
                return;
            }
            const speechDiv = card.querySelector('.speech');
            allSpeeches['speech-' + name] = content;
            speechDiv.innerHTML = content.replace(/\\n/g, '<br>');
            if (currentlySpeaking !== name) {
                const prev = document.querySelector('.avatar-speaking');
                if (prev) prev.classList.remove('avatar-speaking');
                const img = document.getElementById(`avatar-${name}`);
                if (img) img.classList.add('avatar-speaking');
                currentlySpeaking = name;
            }
        }
        
        function updateVote(name, content) {
            const card = document.getElementById('card-' + name);
            if (!card) return;
            const voteDiv = card.querySelector('.vote');
            voteDiv.innerHTML = '<strong>🗳️ 投票</strong><br>' + content.replace(/\\n/g, '<br>');
        }
        
        function updateStatus(text) {
            document.getElementById('statusBar').querySelector('.status-text').textContent = text;
        }
        
        function updateFinal(content) {
            document.getElementById('finalVerdict').innerHTML = `<div class="final-box"><strong>⚖️ 判决</strong><br><br>${content.replace(/\\n/g, '<br>')}</div>`;
        }
        
        function showError(msg) {
            const box = document.getElementById('errorBox');
            box.className = 'error-box show';
            box.textContent = '❌ ' + msg;
        }
        
        function hideError() {
            document.getElementById('errorBox').className = 'error-box';
        }
        
        function exportReport() {
            let content = '# 🏛️ 诸神议事厅 · 辩论报告\\n\\n';
            const sages = currentSages || getCurrentSages();
            sages.forEach(name => {
                const fullId = 'speech-' + name;
                if (allSpeeches[fullId]) {
                    content += `## ${name}\\n\\n${allSpeeches[fullId]}\\n\\n`;
                }
            });
            const finalDiv = document.getElementById('finalVerdict');
            const finalText = finalDiv.textContent || '';
            if (finalText && !finalText.includes('等待判决')) {
                content += `## ⚖️ 判决\\n\\n${finalText}\\n\\n`;
            }
            const blob = new Blob([content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '辩论报告.md';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        function startDebate() {
            const topic = document.getElementById('topic').value.trim();
            if (!topic) { alert('请提出你的议题！'); return; }
            const mode = document.getElementById('modeSelect').value;
            const rounds = parseInt(document.getElementById('roundsInput').value) || 2;
            const sages = getCurrentSages();
            
            const btn = document.getElementById('debateBtn');
            btn.disabled = true;
            btn.textContent = '⏳ 进行中...';
            hideError();
            document.querySelectorAll('.avatar-speaking').forEach(el => el.classList.remove('avatar-speaking'));
            currentlySpeaking = null;
            initCards(sages);
            updateStatus('⏳ 正在连接服务器...');
            if (currentEventSource) { currentEventSource.close(); }
            const url = `/debate_stream?topic=${encodeURIComponent(topic)}&mode=${mode}&rounds=${rounds}&sages=${encodeURIComponent(sages.join(','))}`;
            currentEventSource = new EventSource(url);
            currentEventSource.onmessage = function(event) {
                console.log('📨 收到消息:', event.data);
                try {
                    const data = JSON.parse(event.data);
                    switch (data.type) {
                        case 'status':
                            updateStatus(data.content);
                            if (data.content.includes('已匹配圣贤：')) {
                                const match = data.content.match(/已匹配圣贤：(.*)/);
                                if (match) {
                                    const names = match[1].split(',').map(s => s.trim());
                                    initCards(names);
                                    // 刷新头像
                                    names.forEach(name => {
                                        const img = document.getElementById(`avatar-${name}`);
                                        if (img) {
                                            img.src = `/static/avatars/${encodeURIComponent(name)}.png?t=${Date.now()}`;
                                        }
                                    });
                                }
                            }
                            break;
                        case 'speech':
                            updateSpeech(data.name, data.content);
                            allSpeeches['speech-' + data.name] = data.content;
                            break;
                        case 'vote':
                            updateVote(data.name, data.content);
                            break;
                        case 'final':
                            updateFinal(data.content);
                            break;
                        case 'done':
                            currentEventSource.close();
                            btn.disabled = false;
                            btn.textContent = '🔥 点燃辩论之火';
                            updateStatus('✅ 辩论完成！');
                            document.querySelectorAll('.avatar-speaking').forEach(el => el.classList.remove('avatar-speaking'));
                            break;
                        case 'error':
                            showError(data.content);
                            updateStatus('❌ 出错了');
                            currentEventSource.close();
                            btn.disabled = false;
                            btn.textContent = '🔥 点燃辩论之火';
                            break;
                        default: console.warn('未知消息类型:', data.type);
                    }
                } catch (e) { console.error('解析消息失败:', e); }
            };
            currentEventSource.onerror = function(e) {
                console.error('SSE 连接错误:', e);
                if (currentEventSource.readyState === EventSource.CLOSED) {
                    btn.disabled = false;
                    btn.textContent = '🔥 点燃辩论之火';
                    if (document.getElementById('errorBox').className.indexOf('show') === -1) {
                        updateStatus('✅ 辩论完成');
                    }
                } else {
                    updateStatus('⚠️ 连接中断，正在重试...');
                }
            };
        }
        
        window.addEventListener('beforeunload', function() {
            if (currentEventSource) { currentEventSource.close(); }
        });
    </script>
</body>
</html>
"""

# ==================== 16. 启动 ====================
def ask_api_key():
    print("\n" + "=" * 50)
    print("   🔑 Agnes AI API Key 配置")
    print("=" * 50 + "\n")
    
    env_key = os.getenv("AGNES_API_KEY", "")
    if env_key and env_key.startswith("sk-"):
        print("📂 检测到已有 API Key，正在验证...")
        headers = {"Authorization": f"Bearer {env_key}"}
        try:
            resp = requests.get(f"{AGNES_BASE_URL}/models", headers=headers, timeout=5)
            if resp.status_code == 200:
                print("✅ 密钥有效，自动使用")
                return env_key
            else:
                print(f"⚠️ 密钥无效（状态码：{resp.status_code}），请重新输入")
        except:
            pass
    
    link_url = "https://platform.agnes-ai.cn"
    hyperlink = f"\x1b]8;;{link_url}\x1b\\打开 Agnes AI 平台（点击直达）\x1b]8;;\x1b\\"
    print("📌 获取 Agnes AI API Key 的步骤：")
    print(f"   1. {hyperlink}")
    print("   2. 注册并登录账号")
    print("   3. 进入控制台 -> API Keys -> 创建新密钥")
    print("   4. 复制生成的 sk-xxx 密钥")
    print(f"   📍 备用网址：{link_url}\n")
    
    while True:
        key = input("🔑 请粘贴你的 API Key: ").strip()
        if not key:
            print("⚠️ 密钥不能为空")
            continue
        if not key.startswith("sk-"):
            print("⚠️ 密钥格式不正确（应以 sk- 开头）")
            continue
        print("⏳ 正在验证密钥...")
        headers = {"Authorization": f"Bearer {key}"}
        try:
            resp = requests.get(f"{AGNES_BASE_URL}/models", headers=headers, timeout=10)
            if resp.status_code == 200:
                print("✅ 密钥验证通过！正在保存到 .env ...")
                dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
                with open(dotenv_path, 'w', encoding='utf-8') as f:
                    f.write(f"AGNES_API_KEY={key}\n")
                print("✅ 密钥已保存到 .env")
                return key
            else:
                print(f"❌ 密钥验证失败（状态码：{resp.status_code}）")
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接 Agnes AI 服务，请检查网络")
        except requests.exceptions.Timeout:
            print("❌ 连接超时，请稍后重试")
        except Exception as e:
            print(f"❌ 验证出错：{e}")
        retry = input("\n重新输入？(直接回车=重试，输入 n=退出): ").strip().lower()
        if retry == "n":
            print("已退出程序")
            sys.exit(0)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("   🏛️ 诸神议事厅 · 最终完整版（绝无精简）")
    print("=" * 50)
    
    AGNES_API_KEY = ask_api_key()
    os.environ["AGNES_API_KEY"] = AGNES_API_KEY
    
    print("\n[1/4] 检测 API 服务...")
    if not check_agness_api():
        print("❌ 无法连接到 Agnes AI API！")
        input("\n按回车退出...")
        sys.exit(1)
    print("✅ API 服务正常")
    
    print("\n[2/4] 预生成头像...")
    for name in DEFAULT_SAGES.keys():
        file_path = ensure_avatar(name)
        if os.path.exists(file_path):
            print(f"   ✅ {name} 头像已存在")
        else:
            print(f"   ⏳ 生成 {name} 头像...")
            result = generate_avatar_image(name)
            if result:
                print(f"   ✅ {name} 头像生成成功")
            else:
                print(f"   ⚠️ {name} 头像生成失败，占位符将替代")
    
    print("\n[3/4] 检测可用端口...")
    PORT = find_available_port(5000)
    if PORT is None:
        print("❌ 无法找到可用端口")
        input("\n按回车退出...")
        sys.exit(1)
    print(f"✅ 使用端口：{PORT}")
    
    print(f"\n[4/4] 启动服务（模型：{AGNES_TEXT_MODEL}）...")
    print("=" * 50)
    print(f"🌐 请在浏览器访问：http://127.0.0.1:{PORT}")
    print("💡 点击头像可重新生成")
    print("📄 点击'导出报告'可下载Markdown辩论报告")
    print("⚡ 模型：Agnes AI 云端（免费）")
    print("🤖 智能识别领域并自动匹配圣贤")
    print("=" * 50 + "\n")
    
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)
