import json
from typing import List, Dict, Literal
from pydantic import BaseModel, Field, ConfigDict

class Character(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(description="登場人物の名前。")
    status: Literal["生存", "死亡", "不明"] = Field(description="現在の状態（生存・死亡・不明など）")
    role: str = Field(description="役割や職業（例：探偵、被害者、容疑者など）")
    relationship_history: Dict[int, str] = Field(
        default_factory=dict,
        description="各章ごとの関係性の履歴。キーは章番号、値はその章時点での他の人物との関係性や状況。"
    )

class Timeline(BaseModel):
    model_config = ConfigDict(extra='forbid')
    chapter_number: int = Field(description="イベントが発生した章番号。")
    event: str = Field(description="発生したイベントの詳細な内容。")
    location: str = Field(description="イベントが発生した場所。")
    involved_persons: List[str] = Field(description="イベントに関与した人物の名前のリスト。")

class Item(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(description="アイテムの名前。")
    description: str = Field(description="アイテムの説明や特徴。")
    location_found: str = Field(description="アイテムが最初に発見された場所。")
    current_possessor: str = Field(description="現在そのアイテムを所持している人物の名前。不明な場合や共有の場所に保管されている場合はその状況。")
    is_ignored: bool = Field(default=False, description="このアイテムが推理に不要と手動でマークされているかどうか。")

class MysteryState(BaseModel):
    model_config = ConfigDict(extra='forbid')
    characters: List[Character] = Field(default_factory=list, description="物語の登場人物のリスト。")
    timelines: List[Timeline] = Field(default_factory=list, description="物語の時系列イベント。")
    items: List[Item] = Field(default_factory=list, description="物語に登場する重要なアイテムのリスト。")

    @classmethod
    def load_from_json(cls, filepath: str) -> 'MysteryState':
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return cls(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()

    def save_to_json(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=4))
