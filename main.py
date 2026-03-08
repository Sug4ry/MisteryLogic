import streamlit as st
import os
from models import MysteryState
from analyzer import analyze_notes
from visualizer import generate_relationship_graph
import streamlit.components.v1 as components
from sheets_db import load_state_from_sheet, save_state_to_sheet

st.set_page_config(page_title="Mystery Logic Analyzer", layout="wide", page_icon="🕵️")

st.title("🕵️ Mystery Logic Analyzer")
st.markdown("ミステリー小説の断片的なメモから情報を抽出し、矛盾を検知して相関図を生成します。")

# --- Authentication & API Key check ---
if "api_key" not in st.session_state:
    _api_key = os.environ.get("GEMINI_API_KEY", "")
    if not _api_key:
        try:
            _api_key = st.secrets.get("GEMINI_API_KEY", "")
        except FileNotFoundError:
            pass
    st.session_state["api_key"] = _api_key.strip(' "\'')

if not st.session_state["api_key"]:
    st.sidebar.warning("API Keyが設定されていません。")
    api_key_input = st.sidebar.text_input("GEMINI_API_KEY", type="password")
    if api_key_input:
        st.session_state["api_key"] = api_key_input.strip(' "\'')
        st.rerun()
    else:
        st.info("👈 サイドバーにGemini APIのキーを入力してください。")
        st.stop()
else:
    st.sidebar.success("API Key設定済み")
    if st.sidebar.button("APIキーを変更する"):
        del st.session_state["api_key"]
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        st.rerun()

# Update os environment just in case underlying libraries need it
os.environ["GEMINI_API_KEY"] = st.session_state["api_key"]

# --- State Loading via Google Sheets ---
try:
    state = load_state_from_sheet()
except Exception as e:
    st.error("Google Sheetsへの接続設定が未完了です。")
    st.info("`.streamlit/secrets.toml`を作成し、`[gcp_service_account]`および`[gsheets]`の設定を行ってください。詳細はGitHubのREADMEを参照してください。")
    st.stop()

# --- Sidebar info & reset ---
st.sidebar.header("現在の状態")
st.sidebar.write(f"👥 登場人物: {len(state.characters)}人")
st.sidebar.write(f"📝 イベント数: {len(state.timelines)}件")
st.sidebar.write(f"🔍 アイテム数: {len(state.items)}件")
if st.sidebar.button("状態をリセット (スプレッドシートを初期化)"):
    # 空の状態で上書き保存してリセット
    save_state_to_sheet(MysteryState(characters=[], timelines=[], items=[]))
    st.rerun()

# --- Main Layout ---
col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("メモの入力")
    chapter_num = st.number_input("章番号", min_value=1, value=1, step=1)
    notes = st.text_area("章のメモ・出来事を入力してください", height=250, 
                         placeholder="例：第1章。洋館に探偵の佐藤と富豪の鈴木が到着した。その夜、鈴木は密室で殺害された。")
    
    if st.button("メモを解析して状態を更新", type="primary"):
        if not notes.strip():
            st.error("メモを入力してください。")
        else:
            with st.spinner("Gemini APIで論理構造を解析中..."):
                try:
                    # Using google-genai, analyze_notes should handle the initialization
                    updated_state, warnings = analyze_notes(state, chapter_num, notes, st.session_state["api_key"])
                    
                    if warnings:
                        st.session_state["warnings"] = warnings
                        st.session_state["status_msg"] = ("warning", "矛盾や警告が検出されました！")
                    else:
                        st.session_state["warnings"] = []
                        st.session_state["status_msg"] = ("success", "状態が正常に更新されました！")
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"解析エラー: {e}")

    # Show status message if any
    if "status_msg" in st.session_state:
        msg_type, msg_text = st.session_state["status_msg"]
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "warning":
            st.error("⚠️ " + msg_text)
        
        # Show specific warnings
        if "warnings" in st.session_state and st.session_state["warnings"]:
            for w in st.session_state["warnings"]:
                st.warning(w)

with col2:
    st.subheader("人物相関図")
    view_chapter = st.number_input("表示する章番号", min_value=1, value=chapter_num, step=1, key="view_chap")
    
    if len(state.characters) > 0:
        # Auto-generate graph
        output_html = "graph.html"
        generate_relationship_graph(state, view_chapter, output_html)
        
        with open(output_html, "r", encoding="utf-8") as f:
            html_data = f.read()
        
        st.markdown("**(緑: 生存 / 赤: 死亡 / 灰: 不明)** | ノードをホバーで詳細表示")
        components.html(html_data, height=550)
    else:
        st.info("まだデータがありません。メモを入力して解析してください。")
            
st.markdown("---")
st.subheader("🔑 重要なアイテムと所持者")
if len(state.items) > 0:
    for item in state.items:
        with st.expander(f"{item.name} (現在: {item.current_possessor})"):
            st.markdown(f"**説明:** {item.description}")
            st.markdown(f"**発見場所:** {item.location_found}")
else:
    st.info("現在追跡中のアイテムはありません。")

st.markdown("---")
st.subheader("現在の生データ (JSON)")
with st.expander("JSONデータを表示"):
    st.json(state.model_dump())
