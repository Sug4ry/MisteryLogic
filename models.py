import json
import uuid
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
    is_ignored: bool = Field(default=False, description="この人物が推理に不要と手動でマークされているかどうか。")
    uncertainty: bool = Field(default=False, description="この人物の存在や状態が不確実・推論の域を出ない場合にTrueとする。")

class Timeline(BaseModel):
    model_config = ConfigDict(extra='forbid')
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="イベントを一意に識別するためのID。")
    chapter_number: int = Field(description="イベントが発生した章番号。")
    event: str = Field(description="発生したイベントの詳細な内容。")
    location: str = Field(description="イベントが発生した場所。")
    involved_persons: List[str] = Field(description="イベントに関与した人物の名前のリスト。")
    uncertainty: bool = Field(default=False, description="このイベントが推論や不確実な証言に基づく場合にTrueとする。")

class Item(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(description="アイテムの名前。")
    description: str = Field(description="アイテムの説明や特徴。")
    location_found: str = Field(description="アイテムが最初に発見された場所。")
    current_possessor: str = Field(description="現在そのアイテムを所持している人物の名前。不明な場合や共有の場所に保管されている場合はその状況。")
    is_ignored: bool = Field(default=False, description="このアイテムが推理に不要と手動でマークされているかどうか。")
    uncertainty: bool = Field(default=False, description="このアイテムの存在や所持者が不確実な場合にTrueとする。")

class Trick(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(description="トリックや謎の名称（例：「密室トリック」「凶器の消失」）")
    method: str = Field(description="推測される手法や実行方法。未解明の場合はその旨を記載。")
    weapon: str = Field(description="使用された凶器。未解明の場合はその旨を記載。")
    unresolved_contradictions: List[str] = Field(description="現状で未解明の矛盾点や謎のリスト。")
    related_evidences: List[str] = Field(description="このトリックや謎に関連する証拠の名称リスト。")
    is_ignored: bool = Field(default=False, description="このトリックを推理から除外するかどうか。")
    uncertainty: bool = Field(default=False, description="このトリックの手法が確定しておらず推論の段階である場合にTrueとする。")

class Motive(BaseModel):
    model_config = ConfigDict(extra='forbid')
    suspect_name: str = Field(description="この動機を持つと推測される人物の名前。")
    motive_content: str = Field(description="動機の詳細内容（怨恨、金銭、口封じなど）。")
    strength: int = Field(description="動機の強さ（1から5までの数値。5が最も強い）。")
    past_karma: str = Field(description="動機に関連する過去の因縁や出来事。")
    is_ignored: bool = Field(default=False, description="この動機を推理から除外するかどうか。")
    uncertainty: bool = Field(default=False, description="この動機が推発であり、裏付けが取れていない場合にTrueとする。")

class Evidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(description="証拠の名称。")
    location_obtained: str = Field(description="証拠が入手・発見された場所。")
    affirming_persons: List[str] = Field(description="この証拠によって主張やアリバイが肯定される・有利になる人物のリスト。")
    denying_persons: List[str] = Field(description="この証拠によって主張やアリバイが否定される・不利になる人物のリスト。")
    is_ignored: bool = Field(default=False, description="この証拠を推理から除外するかどうか。")
    uncertainty: bool = Field(default=False, description="証拠の信憑性が疑わしい場合、または推論に基づく関連付けの場合にTrueとする。")

class MysteryState(BaseModel):
    model_config = ConfigDict(extra='forbid')
    characters: List[Character] = Field(default_factory=list, description="物語の登場人物のリスト。")
    timelines: List[Timeline] = Field(default_factory=list, description="物語の時系列イベント。")
    items: List[Item] = Field(default_factory=list, description="物語に登場する重要なアイテムのリスト。")
    tricks: List[Trick] = Field(default_factory=list, description="物語のトリックや謎解き要素のリスト。")
    motives: List[Motive] = Field(default_factory=list, description="登場人物の動機のリスト。")
    evidences: List[Evidence] = Field(default_factory=list, description="事件に関する証拠のリスト。")

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
