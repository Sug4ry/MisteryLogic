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

def load_state_from_sheet() -> MysteryState:
    """Google SheetsのA1セルからJSON文字列を読み込み、MysteryStateオブジェクトとして返す"""
    try:
        sheet = get_google_sheet()
        # A1セルの値を取得（データがない場合はNoneや空文字が返る）
        val = sheet.acell('A1').value
        
        if val:
            data = json.loads(val)
            return MysteryState(**data)
        else:
            return MysteryState(characters=[], timelines=[])
    except Exception as e:
        st.error(f"スプレッドシートからのデータ読み込みに失敗しました: {e}")
        # 読み込めない場合は初期状態を返す
        return MysteryState(characters=[], timelines=[])

def save_state_to_sheet(state: MysteryState):
    """MysteryStateオブジェクトをJSON文字列に変換し、Google SheetsのA1セルに保存する"""
    try:
        sheet = get_google_sheet()
        json_data = state.model_dump_json()
        # A1セルを更新
        sheet.update_acell('A1', json_data)
    except Exception as e:
        st.error(f"スプレッドシートへのデータ保存に失敗しました: {e}")
        raise
