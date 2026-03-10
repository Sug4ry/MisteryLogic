import json
import os
import google.genai as genai
from google.genai import types
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Tuple
from models import MysteryState, Character, Timeline, Item, Trick, Motive, Evidence
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
2. イベントの時系列(timelines)に、メモから読み取れるイベントを1つ以上追加してください。既存のイベントを更新する場合は、既存の `uid` を絶対に変更しないでください。新しく追加するイベントには自動で `uid` が振られるため `uid` の指定は不要です。
3. 重要なアイテム(items)が登場した場合はリストに追加し、既存のアイテムの場合は説明(description)、発見場所(location_found)、現在の所持者(current_possessor)を適切に更新してください。ただし、is_ignored が true になっているアイテムは変更せず、そのままの状態で保持してください。
4. メモから「これはトリックの断片だ」「これは動機の示唆だ」を自動判別し、トリック(tricks)、動機(motives)、証拠(evidences)を抽出・更新してください。既存のもので is_ignored が true のものは変更せず保持してください。
   - トリック(tricks): 推測される手法、凶器、未解明の矛盾点、関連する証拠を管理します。
   - 動機(motives): 誰がどのような動機を持つか、その強さ(1-5)、過去の因縁などを管理します。
   - 証拠(evidences): 証拠の入手場所、それを肯定・否定する人物を管理します。アイテムが証拠の性質を持った場合は、新たな証拠として登録してください。
5. 過去の状態と明らかな矛盾がある場合（例：すでに`死亡`となっているはずの人物が以降の章で生存して行動している、またはアリバイが成立しない場所の移動など）は、`warnings`リストに具体的な警告メッセージを追加してください。矛盾がない場合は空のリストにしてください。

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

def generate_hypothesis(current_state: MysteryState, target_suspect: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
あなたは名探偵の助手です。
以下の現在の`状態(state.json)`に基づき、「もし犯人が {target_suspect} だとした場合、How（どうやって殺したか・犯行に及んだか）とWhy（なぜ殺したか・動機は十分か）にどのような矛盾や不自然な点が生じるか」を論理的にシミュレーションしてください。

現在の状態:
{current_state.model_dump_json(indent=2)}

シミュレーションの出力形式はマークダウンとし、以下の構成に従ってください。
### 🔍 {target_suspect} 犯行説の前提
なぜ {target_suspect} が疑わしいのか、現状の動機や証拠からの支持。

### ⚙️ How（手法・機会）の検証
時系列や証拠、トリックと照らし合わせて、単独または共犯で実行可能か。生じる矛盾点。

### 🖤 Why（動機）の検証
動機の強さや過去の記録から見て、犯行に及ぶほど十分な理由があるか。

### ⚖️ 結論
{target_suspect} が犯人である可能性の高さ（高・中・低）と、今後捜査すべきポイント。
"""
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt
    )
    return response.text
