import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from models.database import SessionLocal
from models.tables import files


def validate_data_types(df: pd.DataFrame, row: dict) -> bool:
    for col, value in row.items():
        if col not in df.columns or col == 'row_id':
            continue
        dtype = df[col].dtype
        try:
            if pd.api.types.is_numeric_dtype(dtype):
                float(value)
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                pd.to_datetime(value)
            elif pd.api.types.is_bool_dtype(dtype):
                if not isinstance(value, bool):
                    raise ValueError
        except (ValueError, TypeError):
            return False
    return True


def get_file_columns(file_id: int, sheet_name: str) -> list:
    with SessionLocal() as session:
        file = session.execute(select(files).where(
            files.c.id == file_id)).fetchone()
        if not file:
            raise HTTPException(
                status_code=404, detail=f"File {file_id} not found")
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file_path)
        elif file.filename.endswith('.json'):
            df = pd.read_json(file.file_path)
        else:
            if sheet_name not in file.sheets:
                raise HTTPException(
                    status_code=400, detail=f"Sheet {sheet_name} not found")
            df = pd.read_excel(file.file_path, sheet_name=sheet_name)
        return list(df.columns)
