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
st.subheader("👥 登場人物")
if len(state.characters) > 0:
    active_chars = [c for c in state.characters if not c.is_ignored]
    ignored_chars = [c for c in state.characters if c.is_ignored]
    
    def render_character(char, is_ignored_section=False):
        key_prefix = f"char_{'ignored' if is_ignored_section else 'active'}_{char.name}"
        with st.expander(f"{'❌ ' if char.is_ignored else ''}{char.name} (役割: {char.role} / 状態: {char.status})"):
            new_role = st.text_input("役割を編集:", value=char.role, key=f"{key_prefix}_role")
            
            status_options = ["生存", "死亡", "不明"]
            try:
                status_idx = status_options.index(char.status)
            except ValueError:
                status_idx = 2
            new_status = st.selectbox("状態を編集:", options=status_options, index=status_idx, key=f"{key_prefix}_status")
            
            is_ignored = st.checkbox("この人物を推理から除外する (相関図から消え、下部に移動します)", value=char.is_ignored, key=f"{key_prefix}_ignored")
            
            if new_role != char.role or new_status != char.status or is_ignored != char.is_ignored:
                for s_char in state.characters:
                    if s_char.name == char.name:
                        s_char.role = new_role
                        s_char.status = new_status
                        s_char.is_ignored = is_ignored
                        break
                save_state_to_sheet(state)
                st.rerun()

    for char in active_chars:
        render_character(char, is_ignored_section=False)
        
    if ignored_chars:
        st.markdown("##### 📦 除外された人物")
        for char in ignored_chars:
            render_character(char, is_ignored_section=True)
else:
    st.info("現在追跡中の人物はありません。")

st.markdown("---")
st.subheader("🔑 重要なアイテム")

if len(state.items) > 0:
    active_items = [i for i in state.items if not i.is_ignored]
    ignored_items = [i for i in state.items if i.is_ignored]
    
    def render_item(item, is_ignored_section=False):
        # We use a unique key based on item name and its section
        key_prefix = f"item_{'ignored' if is_ignored_section else 'active'}_{item.name}"
        
        with st.expander(f"{'❌ ' if item.is_ignored else ''}{item.name} (現在: {item.current_possessor})"):
            st.markdown(f"**説明:** {item.description}")
            st.markdown(f"**発見場所:** {item.location_found}")
            
            new_possessor = st.text_input("現在の所持者を編集:", value=item.current_possessor, key=f"{key_prefix}_possessor")
            is_ignored = st.checkbox("このアイテムを推理から除外する (下部に移動します)", value=item.is_ignored, key=f"{key_prefix}_ignored")
            
            if new_possessor != item.current_possessor or is_ignored != item.is_ignored:
                # Find the actual item in the state and update it
                for s_item in state.items:
                    if s_item.name == item.name:
                        s_item.current_possessor = new_possessor
                        s_item.is_ignored = is_ignored
                        break
                save_state_to_sheet(state)
                st.rerun()

    # Render active items first
    for item in active_items:
        render_item(item, is_ignored_section=False)
        
    # Render ignored items at the bottom
    if ignored_items:
        st.markdown("##### 📦 除外されたアイテム")
        for item in ignored_items:
            render_item(item, is_ignored_section=True)

else:
    st.info("現在追跡中のアイテムはありません。")

st.markdown("---")
st.subheader("🕰️ イベント履歴")
if len(state.timelines) > 0:
    sorted_timelines = sorted(state.timelines, key=lambda x: x.chapter_number)
    
    events_to_delete = []
    
    for tl in sorted_timelines:
        key_prefix = f"tl_{tl.uid}"
        with st.expander(f"【第{tl.chapter_number}章】 📍{tl.location} - {tl.event[:20]}..."):
            
            new_chapter = st.number_input("発生章", min_value=1, value=tl.chapter_number, step=1, key=f"{key_prefix}_chap")
            new_location = st.text_input("場所", value=tl.location, key=f"{key_prefix}_loc")
            new_event = st.text_area("出来事の内容", value=tl.event, key=f"{key_prefix}_event")
            
            persons_str = ", ".join(tl.involved_persons)
            new_persons_str = st.text_input("関与者 (カンマ区切り)", value=persons_str, key=f"{key_prefix}_persons")
            new_persons = [p.strip() for p in new_persons_str.split(",") if p.strip()]
            
            col_a, col_b = st.columns([8, 2])
            with col_b:
                if st.button("🗑️ 削除", key=f"{key_prefix}_del"):
                    events_to_delete.append(tl.uid)
            
            # Check for edits
            if (new_chapter != tl.chapter_number or 
                new_location != tl.location or 
                new_event != tl.event or 
                new_persons != tl.involved_persons):
                
                # Apply updates
                for s_tl in state.timelines:
                    if s_tl.uid == tl.uid:
                        s_tl.chapter_number = new_chapter
                        s_tl.location = new_location
                        s_tl.event = new_event
                        s_tl.involved_persons = new_persons
                        break
                save_state_to_sheet(state)
                st.rerun()
                
    # Handle deletions
    if events_to_delete:
        state.timelines = [t for t in state.timelines if t.uid not in events_to_delete]
        save_state_to_sheet(state)
        st.rerun()
        
else:
    st.info("過去のイベントはまだ記録されていません。")

st.markdown("---")
st.subheader("現在の生データ (JSON)")
with st.expander("JSONデータを表示"):
    st.json(state.model_dump())
