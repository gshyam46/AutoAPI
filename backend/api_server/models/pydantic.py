from pydantic import BaseModel
from typing import List, Dict, Optional


class UserInput(BaseModel):
    email: str
    password: str


class FileCreate(BaseModel):
    filename: str
    sheets: List[str]
    selected_sheet: Optional[str] = None
    selected_columns: Optional[List[str]] = None


class FileUpdate(BaseModel):
    selected_sheet: Optional[str] = None
    selected_columns: Optional[List[str]] = None


class APIConfigCreate(BaseModel):
    file_id: int
    endpoint_path: str
    method: str
    query_logic: Dict


class JoinConfig(BaseModel):
    files: List[int] = []
    sheets: List[str] = []
    on: str
    type: str = "inner"


class QueryRequest(BaseModel):
    file_id: int
    sheet_name: Optional[str] = None
    operation: str
    query_logic: Optional[Dict] = None
    payload: Optional[Dict | List[Dict]] = None
    join_config: Optional[JoinConfig] = None
