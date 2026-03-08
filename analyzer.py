import json
import os
import google.genai as genai
from google.genai import types
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Tuple
from models import MysteryState, Character, Timeline, Item
from sheets_db import save_state_to_sheet

class AnalyzerResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    updated_state: MysteryState = Field(description="The fully updated mystery state parsing the previous state and new notes.")
    warnings: List[str] = Field(description="A list of warnings if there are contradictions (e.g., dead character reappears or invalid timeline). Empty if no warnings.")

def analyze_notes(current_state: MysteryState, chapter: int, notes: str, api_key: str) -> Tuple[MysteryState, List[str]]:
    
    # Using gemini-2.5-pro or flash via new SDK for better reasoning and JSON schema output
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
あなたはミステリー小説の論理構造を詳細に分析するAIアシスタントです。
以下の現在の`状態(state.json)`と、ユーザーが新たに入力した`第{chapter}章のメモ`を読み込み、状態を更新してJSONで返してください。

現在の状態:
{current_state.model_dump_json(indent=2)}

第{chapter}章のメモ:
{notes}

以下のルールに従って更新を行ってください。
1. 登場人物(characters)が新しく登場した場合はリストに追加し、既存の人物は状態(status: 生存/死亡/不明)、役割、各章ごとの関係性(relationship_history)を適切に更新してください。過去の章の関係性履歴は消さずに保持し、今回の章における関係性や心情の変化を relationship_history の "キー={chapter}" の値に追加してください。ただし、is_ignored が true になっている人物の情報は一切変更・追加せず、そのままの状態で保持してください。
2. イベントの時系列(timelines)に、メモから読み取れるイベントを1つ以上追加してください。
3. 重要なアイテム(items)が登場した場合はリストに追加し、既存のアイテムの場合は説明(description)、発見場所(location_found)、現在の所持者(current_possessor)を適切に更新してください。ただし、is_ignored が true になっているアイテムは変更せず、そのままの状態で保持してください。
4. 過去の状態と明らかな矛盾がある場合（例：すでに`死亡`となっているはずの人物が以降の章で生存して行動している、またはアリバイが成立しない場所の移動など）は、`warnings`リストに具体的な警告メッセージを追加してください。矛盾がない場合は空のリストにしてください。

必ず以下のJSONスキーマの構造に完全に一致させて出力してください。
追加のプロパティを含めたり、キー名を変更したりしないでください。

スキーマ:
{AnalyzerResponse.model_json_schema()}
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    
    try:
        data = json.loads(response.text)
        analyzer_resp = AnalyzerResponse(**data)
        
        # ユーザーの要望通り、analyzer内部でGoogle Sheetsへの保存・同期を実行する
        save_state_to_sheet(analyzer_resp.updated_state)
        
        return analyzer_resp.updated_state, analyzer_resp.warnings
    except Exception as e:
        raise RuntimeError(f"Failed to parse Gemini response: {e}\nResponse text: {response.text}")
