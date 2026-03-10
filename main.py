import streamlit as st
import os
from models import MysteryState
from analyzer import analyze_notes, generate_hypothesis
from visualizer import generate_relationship_graph, generate_murder_board_graph
import streamlit.components.v1 as components
from sheets_db import load_state_from_sheet, save_state_to_sheet, get_all_books

st.set_page_config(page_title="Mystery Logic Analyzer", layout="wide", page_icon="🕵️", initial_sidebar_state="expanded")

# --- Custom CSS for Darker Theme Alignments ---
st.markdown("""
<style>
/* Make Streamlit closer to the dark theme board */
.stApp {
    background-color: #121212;
    color: #ecf0f1;
}
</style>
""", unsafe_allow_html=True)

st.title("🕵️ Mystery Logic Analyzer")
st.markdown("ミステリー小説の断片的なメモから情報を抽出し、矛盾を検知して本格的な捜査ボードを生成します。")

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

# --- Book Selection UI ---
try:
    available_books = get_all_books()
except Exception as e:
    st.error("Google Sheetsへの接続設定が未完了です。")
    st.info("`.streamlit/info`")
    st.stop()

if not available_books:
    available_books = ["デフォルトのミステリー"]

st.sidebar.header("📕 ミステリーの選択")
selected_book = st.sidebar.selectbox("記録する本を選んでください", options=available_books)

new_book_name = st.sidebar.text_input("💡 新しい本を追加する")
if st.sidebar.button("追加"):
    if new_book_name and new_book_name not in available_books:
        # Create an empty state for the new book
        save_state_to_sheet(MysteryState(characters=[], timelines=[], items=[]), new_book_name)
        st.session_state["current_book"] = new_book_name
        st.rerun()

if "current_book" not in st.session_state or (new_book_name and st.session_state["current_book"] == new_book_name):
    pass # Will be handled below, default to selected
    
if "current_book" not in st.session_state:
    st.session_state["current_book"] = selected_book

# Update session state if the user changes the dropdown manually
if selected_book != st.session_state.get("current_book"):
    st.session_state["current_book"] = selected_book

current_book = st.session_state["current_book"]

# --- State Loading via Google Sheets ---
try:
    state = load_state_from_sheet(current_book)
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

# --- Sidebar info & reset ---
st.sidebar.header(f"「{current_book}」の状態")
st.sidebar.write(f"👥 登場人物: {len(state.characters)}人")
st.sidebar.write(f"📝 イベント数: {len(state.timelines)}件")
st.sidebar.write(f"🔍 アイテム数: {len(state.items)}件")
st.sidebar.write(f"🧩 トリック/謎: {len(getattr(state, 'tricks', []))}件")
st.sidebar.write(f"🖤 動機: {len(getattr(state, 'motives', []))}件")
st.sidebar.write(f"💼 証拠: {len(getattr(state, 'evidences', []))}件")
if st.sidebar.button("この本の状態をリセット"):
    save_state_to_sheet(MysteryState(characters=[], timelines=[], items=[]), current_book)
    st.rerun()

# --- Suspect Filter ---
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 容疑者フィルタ")
filter_suspect = "すべて"
if len(state.characters) > 0:
    active_char_names_for_filter = ["すべて"] + [c.name for c in state.characters if not getattr(c, 'is_ignored', False)]
    filter_suspect = st.sidebar.selectbox("特定の人物に関連する要素を強調", options=active_char_names_for_filter)
st.sidebar.markdown("*(選んだ人物に関連する線や証拠のみ強調表示されます)*")

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
    st.subheader("可視化ボード")
    
    if len(state.characters) > 0:
        tab_board, tab_timeline = st.tabs(["捜査ボード表示", "タイムライン表示"])
        
        with tab_board:
            output_board_html = "board.html"
            generate_murder_board_graph(state, output_board_html, filter_suspect=filter_suspect)
            with open(output_board_html, "r", encoding="utf-8") as f:
                board_html_data = f.read()
            st.markdown("**(緑:生存・有利 / 赤:死亡・不利 / 橙:動機 / 青:証拠 / 点線:不確実・推論)**")
            components.html(board_html_data, height=650)
            
        with tab_timeline:
            st.markdown("### 🕰️ イベント履歴")
            if len(state.timelines) > 0:
                sorted_timelines = sorted(state.timelines, key=lambda x: x.chapter_number)
                
                def save_timeline_edit(uid, chap_key, loc_key, event_key, persons_key):
                    n_chap = st.session_state[chap_key]
                    n_loc = st.session_state[loc_key]
                    n_evt = st.session_state[event_key]
                    n_pers = [p.strip() for p in st.session_state[persons_key].split(",") if p.strip()]
                    for s_tl in state.timelines:
                        if s_tl.uid == uid:
                            s_tl.chapter_number = n_chap
                            s_tl.location = n_loc
                            s_tl.event = n_evt
                            s_tl.involved_persons = n_pers
                            break
                    save_state_to_sheet(state, current_book)

                def delete_timeline(uid):
                    state.timelines = [t for t in state.timelines if t.uid != uid]
                    save_state_to_sheet(state, current_book)

                for tl in sorted_timelines:
                    key_prefix = f"tl_{tl.uid}"
                    uncertain_mark = "👻(不確実) " if getattr(tl, 'uncertainty', False) else ""
                    with st.expander(f"【第{tl.chapter_number}章】 📍{tl.location} - {uncertain_mark}{tl.event[:20]}..."):
                        
                        st.number_input("発生章", min_value=1, value=tl.chapter_number, step=1, key=f"{key_prefix}_chap_input")
                        st.text_input("場所", value=tl.location, key=f"{key_prefix}_loc_input")
                        st.text_area("出来事の内容", value=tl.event, key=f"{key_prefix}_event_input")
                        
                        persons_str = ", ".join(tl.involved_persons)
                        st.text_input("関与者 (カンマ区切り)", value=persons_str, key=f"{key_prefix}_persons_input")
                        
                        col_a, col_b = st.columns([8, 2])
                        with col_a:
                            st.button("💾 変更を保存", key=f"{key_prefix}_save_btn", on_click=save_timeline_edit, args=(tl.uid, f"{key_prefix}_chap_input", f"{key_prefix}_loc_input", f"{key_prefix}_event_input", f"{key_prefix}_persons_input"))
                                
                        with col_b:
                            st.button("🗑️ 削除", key=f"{key_prefix}_del_btn", on_click=delete_timeline, args=(tl.uid,))
            else:
                st.info("過去のイベントはまだ記録されていません。")
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
                save_state_to_sheet(state, current_book)
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
                save_state_to_sheet(state, current_book)
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
st.subheader("🧩 トリック・謎")
tricks_list = getattr(state, "tricks", [])
if len(tricks_list) > 0:
    active_tricks = [t for t in tricks_list if not getattr(t, 'is_ignored', False)]
    ignored_tricks = [t for t in tricks_list if getattr(t, 'is_ignored', False)]
    
    def render_trick(trick, is_ignored_section=False):
        key_prefix = f"trick_{'ignored' if is_ignored_section else 'active'}_{trick.name}"
        with st.expander(f"{'❌ ' if getattr(trick, 'is_ignored', False) else ''}{trick.name}"):
            st.markdown(f"**使用凶器:** {trick.weapon}")
            st.markdown(f"**未解明の矛盾:** {', '.join(trick.unresolved_contradictions)}")
            updated_method = st.text_input("手法/実行方法を編集:", value=trick.method, key=f"{key_prefix}_method")
            is_ignored = st.checkbox("この謎を推理から除外する", value=getattr(trick, 'is_ignored', False), key=f"{key_prefix}_ignored")
            
            if updated_method != trick.method or is_ignored != getattr(trick, 'is_ignored', False):
                for s_t in state.tricks:
                    if s_t.name == trick.name:
                        s_t.method = updated_method
                        s_t.is_ignored = is_ignored
                        break
                save_state_to_sheet(state, current_book)
                st.rerun()

    for t in active_tricks: render_trick(t)
    if ignored_tricks:
        st.markdown("##### 📦 除外された謎")
        for t in ignored_tricks: render_trick(t, True)
else:
    st.info("トリックや謎はまだ抽出されていません。")

st.markdown("---")
st.subheader("🖤 動機")
motives_list = getattr(state, "motives", [])
if len(motives_list) > 0:
    active_motives = [m for m in motives_list if not getattr(m, 'is_ignored', False)]
    ignored_motives = [m for m in motives_list if getattr(m, 'is_ignored', False)]
    
    def render_motive(motive, is_ignored_section=False):
        key_prefix = f"motive_{'ignored' if is_ignored_section else 'active'}_{motive.suspect_name}_{motive.strength}"
        with st.expander(f"{'❌ ' if getattr(motive, 'is_ignored', False) else ''}{motive.suspect_name} (強さ: {motive.strength})"):
            st.markdown(f"**内容:** {motive.motive_content}")
            st.markdown(f"**因縁:** {motive.past_karma}")
            is_ignored = st.checkbox("この動機を推理から除外する", value=getattr(motive, 'is_ignored', False), key=f"{key_prefix}_ignored")
            
            if is_ignored != getattr(motive, 'is_ignored', False):
                for s_m in state.motives:
                    if s_m.suspect_name == motive.suspect_name and s_m.motive_content == motive.motive_content:
                        s_m.is_ignored = is_ignored
                        break
                save_state_to_sheet(state, current_book)
                st.rerun()

    for m in active_motives: render_motive(m)
    if ignored_motives:
        st.markdown("##### 📦 除外された動機")
        for m in ignored_motives: render_motive(m, True)
else:
    st.info("動機はまだ抽出されていません。")

st.markdown("---")
st.subheader("💼 証拠")
evidences_list = getattr(state, "evidences", [])
if len(evidences_list) > 0:
    active_evidences = [e for e in evidences_list if not getattr(e, 'is_ignored', False)]
    ignored_evidences = [e for e in evidences_list if getattr(e, 'is_ignored', False)]
    
    def render_evidence(evidence, is_ignored_section=False):
        key_prefix = f"evidence_{'ignored' if is_ignored_section else 'active'}_{evidence.name}"
        with st.expander(f"{'❌ ' if getattr(evidence, 'is_ignored', False) else ''}{evidence.name} (発見場所: {evidence.location_obtained})"):
            st.markdown(f"**肯定/有利:** {', '.join(evidence.affirming_persons)}")
            st.markdown(f"**否定/不利:** {', '.join(evidence.denying_persons)}")
            is_ignored = st.checkbox("この証拠を推理から除外する", value=getattr(evidence, 'is_ignored', False), key=f"{key_prefix}_ignored")
            
            if is_ignored != getattr(evidence, 'is_ignored', False):
                for s_e in state.evidences:
                    if s_e.name == evidence.name:
                        s_e.is_ignored = is_ignored
                        break
                save_state_to_sheet(state, current_book)
                st.rerun()

    for e in active_evidences: render_evidence(e)
    if ignored_evidences:
        st.markdown("##### 📦 除外された証拠")
        for e in ignored_evidences: render_evidence(e, True)
else:
    st.info("証拠はまだ抽出されていません。")

st.markdown("---")
st.subheader("💡 仮説生成モード")
active_char_names_for_hyp = [c.name for c in state.characters if not getattr(c, 'is_ignored', False)]
if active_char_names_for_hyp:
    target_suspect = st.selectbox("犯人と仮定する人物を選択:", options=active_char_names_for_hyp)
    if st.button("仮説シミュレーションを実行"):
        with st.spinner(f"{target_suspect} 犯行説を検証中..."):
            try:
                hyp_result = generate_hypothesis(state, target_suspect, st.session_state["api_key"])
                st.markdown(hyp_result)
            except Exception as e:
                st.error(f"シミュレーションエラー: {e}")
else:
    st.info("人物データがありません。")

# Note: Events history moved to Timeline Tab

st.markdown("---")
st.subheader("現在の生データ (JSON)")
with st.expander("JSONデータを表示"):
    st.json(state.model_dump())
