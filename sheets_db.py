import json
import streamlit as st
from models import MysteryState
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheetsの認証スコープ
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_google_sheet():
    """Streamlitのsecretsから認証情報を読み込み、スプレッドシートのワークシートオブジェクトを取得する"""
    try:
        # st.secretsからサービスアカウント情報を辞書として取得
        creds_dict = st.secrets["gcp_service_account"]
        # secrets内のスプレッドシートのキー（URLの/d/と/editの間の文字列）
        sheet_key = st.secrets["gsheets"]["spreadsheet_key"]
    except KeyError as e:
        raise ValueError(f"StreamlitのSecretsに認証情報が設定されていません: {e}")

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
    client = gspread.authorize(creds)
    
    # スプレッドシートを開き、最初のワークシートを取得
    sheet = client.open_by_key(sheet_key).sheet1
    return sheet

def _migrate_legacy_if_needed(sheet):
    """A1セルに直接JSONが入っている古い形式を検知して一覧表形式に移行する"""
    a1_val = sheet.acell('A1').value
    if a1_val and a1_val.startswith('{'):
        # 従来のJSONが直接入っている場合
        legacy_data = a1_val
        sheet.update('A1:B1', [['Book Title', 'State JSON']])
        sheet.update('A2:B2', [['デフォルトのミステリー', legacy_data]])

def get_all_books() -> list:
    """保存されているすべてのミステリーのタイトルを取得する"""
    try:
        sheet = get_google_sheet()
        _migrate_legacy_if_needed(sheet)
        
        # A列の2行目以降を取得
        titles = sheet.col_values(1)[1:]
        return [t for t in titles if t.strip()]
    except Exception as e:
        st.error(f"ブック一覧の取得に失敗しました: {e}")
        return []

def load_state_from_sheet(book_title: str = "デフォルトのミステリー") -> MysteryState:
    """指定されたタイトルのMysteryStateをGoogle Sheetsから読み込む"""
    try:
        sheet = get_google_sheet()
        _migrate_legacy_if_needed(sheet)
        
        # ヘッダーがない場合は作成
        if not sheet.acell('A1').value:
            sheet.update('A1:B1', [['Book Title', 'State JSON']])
            
        cell = sheet.find(book_title, in_column=1)
        if cell:
            val = sheet.cell(cell.row, 2).value
            if val:
                import json
                data = json.loads(val)
                return MysteryState(**data)
                
        # 見つからない場合は空の状態を返す
        return MysteryState(characters=[], timelines=[], items=[])
    except Exception as e:
        st.error(f"スプレッドシートからのデータ読み込みに失敗しました: {e}")
        return MysteryState(characters=[], timelines=[], items=[])

def save_state_to_sheet(state: MysteryState, book_title: str = "デフォルトのミステリー"):
    """MysteryStateオブジェクトをJSON文字列に変換し、指定されたタイトルで保存する"""
    try:
        sheet = get_google_sheet()
        _migrate_legacy_if_needed(sheet)
        
        json_data = state.model_dump_json()
        
        # ヘッダーの確認
        if sheet.acell('A1').value != 'Book Title':
            sheet.update('A1:B1', [['Book Title', 'State JSON']])
            
        cell = sheet.find(book_title, in_column=1)
        if cell:
            # 既存の行を更新
            sheet.update_cell(cell.row, 2, json_data)
        else:
            # 新しい行に追加
            sheet.append_row([book_title, json_data])
            
    except Exception as e:
        st.error(f"スプレッドシートへのデータ保存に失敗しました: {e}")
        raise
