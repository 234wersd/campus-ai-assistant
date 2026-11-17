"""惠园智答 · Streamlit demo app."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from ai_service import api_configured, summarize_with_deepseek
from notice_engine import CHINA_TZ, DEMO, build_answer, current_notices, load_notices, select_notices, sorted_by_deadline, status

load_dotenv(Path(__file__).with_name(".env"))
st.set_page_config(page_title="惠园智答 · 校园 AI 通知助手", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  :root { --navy: #142d50; --blue: #2365a5; --muted: #667b92; }
  .stApp { background: #f5f8fc; color: #172e4b; }
  .block-container { max-width: 1080px; padding-top: 2.2rem; padding-bottom: 5rem; }
  [data-testid="stSidebar"] { background: #eaf1f9; border-right: 1px solid #d7e3f0; }
  .hero { background: linear-gradient(125deg,#102b4d,#245d93); color: white; padding: 2rem 2.2rem;
          border-radius: 22px; box-shadow: 0 12px 30px rgba(19,47,78,.16); margin-bottom: 1.2rem; }
  .hero h1 { color: white; font-size: 2.25rem; margin: .15rem 0 .4rem; }
  .hero p { color: #dfebf8; margin: 0; font-size: 1.05rem; }
  .eyebrow { color: #b8d5ee; font-size: .86rem; letter-spacing: .1em; }
  .notice-banner { background: #eaf3ff; border: 1px solid #bdd5f3; border-radius: 12px;
                   color: #23466c; padding: .7rem 1rem; margin-bottom: 1.1rem; }
  [data-testid="stChatMessage"] { background: white; border: 1px solid #e1eaf4; border-radius: 16px;
                                    box-shadow: 0 3px 12px rgba(23,52,83,.05); margin-bottom: .65rem; }
  div.stButton > button { border-radius: 999px; border: 1px solid #cbdced; background: white; color: #1d4d79; }
  div.stButton > button:hover { border-color: #3979b7; color: #154c7d; }
  [data-testid="stExpander"] { background: #f8fbfe; border-radius: 12px; }
  @media (max-width: 640px) { .hero { padding: 1.3rem; } .hero h1 { font-size: 1.8rem; } }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def notices_data():
    return load_notices()


notices = notices_data()
active = current_notices(notices)
by_id = {n["id"]: n for n in notices}
today = datetime.now(CHINA_TZ)


def render_evidence(ids: list[str]):
    for notice_id in ids:
        n = by_id[notice_id]
        with st.expander(f"来源与通知原文 · {n['id']} · {n['title']}"):
            st.caption(f"{n['source']} ｜ 版本 {n['version']} ｜ 发布 {n['published_at']} ｜ 更新 {n['updated_at']}")
            st.info(DEMO)
            st.write(n["original_text"])


with st.sidebar:
    st.markdown("### 🎓 惠园智答")
    st.caption("校园通知智能检索与问答 · 赛事演示原型")
    st.write("从本地模拟通知中检索活动、核对截止时间和来源，并展示明确的版本更新。")
    st.divider()
    categories = ["全部", "学科竞赛", "校园活动", "学术讲座", "志愿服务", "英语交流活动"]
    category = st.selectbox("通知类别筛选", categories)
    visible = [n for n in active if category == "全部" or n["category"] == category]
    st.metric("当前收录", f"{len(visible)} 条", help=f"共 {len(notices)} 条记录，含 {len(notices)-len(active)} 条被明确更新的历史版本")
    st.caption(f"完整数据：{len(notices)} 条（含历史版本）")
    st.markdown("#### 通知列表")
    for n in sorted_by_deadline(visible):
        badge = "⏳" if status(n, today).startswith("报名中") else "⌛"
        with st.expander(f"{badge} {n['title']} · {n['id']}"):
            st.caption(f"{n['category']} ｜ {status(n, today)}")
            st.write(f"报名截止：{n['registration_deadline']}")
            st.write(n["original_text"])
    st.divider()
    if st.button("清空聊天", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

st.markdown("""<div class="hero"><div class="eyebrow">CAMPUS AI ASSISTANT · 赛事演示原型</div>
<h1>惠园智答</h1><p>让校园消息不再遗漏，让每一次回答都有据可查。</p></div>""", unsafe_allow_html=True)
st.markdown(f'<div class="notice-banner">{DEMO} 当前仅供功能体验，报名前请核对真实学校公告。</div>', unsafe_allow_html=True)
if api_configured():
    st.caption("🟢 DeepSeek API 模式 · 通知事实由本地资料库核验；资料不足时会明确标注并提供 AI 通用回答")
else:
    st.caption("🟡 本地演示模式 · 未配置 DEEPSEEK_API_KEY；当前回答由规则检索生成，不是大模型回答")

st.markdown("#### 试试这样提问")
examples = ["最近有哪些校园比赛？", "把所有校园比赛的报名截止时间从早到晚排列", "创新创业挑战赛最新截止时间是什么？", "秋季校园文化节还可以报名吗？"]
columns = st.columns(2)
for index, example in enumerate(examples):
    with columns[index % 2]:
        if st.button(example, key=f"example-{index}", use_container_width=True):
            st.session_state["pending_question"] = example

st.divider()
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if not st.session_state["messages"]:
    st.info("输入活动名称、报名材料、截止时间或来源问题，开始体验。")

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])
        if message.get("summary"):
            st.caption(f"🤖 DeepSeek 回答：{message['summary']}")
        if message.get("note"):
            st.caption(message["note"])
        if message.get("evidence"):
            render_evidence(message["evidence"])

typed = st.chat_input("例如：数据科学建模赛需要准备哪些材料？")
question = typed or st.session_state.pop("pending_question", None)
if question:
    lookup_question = question
    if any(token in question for token in ("这个活动", "该活动", "这个比赛", "这个讲座", "它的")) and not select_notices(question, notices, category):
        previous = next((m for m in reversed(st.session_state["messages"]) if m["role"] == "assistant"), None)
        if previous and len(previous.get("evidence", [])) == 1:
            lookup_question = f"{question} {by_id[previous['evidence'][0]]['title']}"
    st.session_state["messages"].append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)
    answer = build_answer(lookup_question, notices, now=today, category_filter=category)
    summary = note = None
    if api_configured():
        with st.spinner("正在调用 DeepSeek 整理回答…"):
            summary, note = summarize_with_deepseek(answer, question)
    elif not api_configured():
        note = "本地演示模式：由规则检索生成，非大模型回答。"
    record = {"role": "assistant", "text": answer.text, "summary": summary, "note": note,
              "evidence": [n["id"] for n in answer.evidence]}
    st.session_state["messages"].append(record)
    with st.chat_message("assistant"):
        st.markdown(answer.text)
        if summary:
            st.caption(f"🤖 DeepSeek 回答：{summary}")
        if note:
            st.caption(note)
        render_evidence(record["evidence"])
