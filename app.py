"""Streamlit 演示界面：对话 + 文件上传 + 多 Agent 执行过程展示。"""
import os
import time

import streamlit as st

from graph import graph
from rag.ingest import DOCUMENTS_DIR

st.set_page_config(page_title="多 Agent 学习助手 Demo", page_icon="🤖", layout="wide")

# 确保目录存在
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

st.title("🤖 多 Agent 智能学习助手")
st.caption("调度 Agent → 学习规划 / 日程提醒 / 知识库（RAG）")

# 初始化会话
if "messages" not in st.session_state:
    st.session_state.messages = []

# 旧版演示入口只保存候选文件，导入操作统一由主界面的“我的知识库”完成。
with st.sidebar:
    st.header("📚 知识库管理")
    uploaded = st.file_uploader(
        "上传文档（PDF / TXT / MD）到待导入目录",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
    )
    if uploaded:
        for f in uploaded:
            save_path = os.path.join(DOCUMENTS_DIR, f.name)
            with open(save_path, "wb") as out:
                out.write(f.read())
            st.success(f"已保存：{f.name}")
        st.info("文档不会自动进入知识库，请在主界面的“我的知识库”中手动导入。")

    st.divider()
    st.markdown("**演示话术：**")
    st.code("我要两周学完 LangGraph", language="text")
    st.code("今天该学什么", language="text")
    st.code("什么是 StateGraph", language="text")

# 对话区
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("trace"):
            with st.expander("🔍 查看 Agent 执行链路", expanded=False):
                st.markdown(msg["trace"])

if user_input := st.chat_input("输入你的学习目标 / 今日任务 / 知识问题..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("多 Agent 协作中..."):
            start = time.time()
            result = graph.invoke({"user_input": user_input})
            elapsed = time.time() - start

        route = result.get("route", "")
        answer = result.get("final_answer", "")

        # 路由标签
        route_labels = {
            "plan": "📋 学习规划",
            "schedule": "🗓️ 日程提醒",
            "knowledge": "📖 知识库 RAG",
        }
        st.markdown(f"**调度路由：** `{route_labels.get(route, route)}`")
        st.markdown(answer)
        if route == "knowledge" and result.get("rag_source"):
            st.caption(f"来源：{result['rag_source']}")
        st.caption(f"⏱️ 耗时 {elapsed:.1f}s")

        # 执行链路 trace
        trace_lines = [f"1. **Supervisor** 识别意图 → `{route}`"]
        if route == "plan":
            plan = result.get("plan_json") or {}
            trace_lines.append(
                f"2. **学习规划 Agent** 生成计划 JSON（{len(plan.get('tasks', []))} 条任务）"
            )
            trace_lines.append(
                f"3. **日程 Agent** 写入 SQLite → {result.get('schedule_result', '')}"
            )
        elif route == "schedule":
            trace_lines.append(
                f"2. **日程 Agent** 从 SQLite 查询今日任务 → {result.get('schedule_result', '')}"
            )
        elif route == "knowledge":
            ctx = result.get("rag_context") or []
            trace_lines.append(
                f"2. **知识库 Agent** FAISS 检索命中 {len(ctx)} 个片段并生成回答"
                if ctx
                else "2. **知识库 Agent** 知识库未命中，改用网络知识回答"
            )
        trace_lines.append("4. **统一回复渲染** 输出最终结果")

        with st.expander("🔍 查看 Agent 执行链路", expanded=True):
            st.markdown("\n\n".join(trace_lines))

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "trace": "\n\n".join(trace_lines)}
    )
