from fastapi import HTTPException, UploadFile
from sqlalchemy import select, insert, update, delete
import os
import pandas as pd
import json
import shutil
from models.database import SessionLocal
from models.tables import files, data
from utils.constants import UPLOAD_DIR, ALLOWED_FILE_TYPES
from utils.file_utils import validate_data_types, get_file_columns


async def upload_file(file: UploadFile):
    if not any(file.filename.endswith(ext) for ext in ALLOWED_FILE_TYPES):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Use CSV, Excel, or JSON.")

    def process_file(file, file_path):
        sheets = []
        df = None
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file_path)
            sheets = ["default"]
        elif file.filename.endswith('.json'):
            with open(file_path, 'r') as f:
                json_data = json.load(f)
            if isinstance(json_data, list):
                try:
                    df = pd.json_normalize(json_data)
                except Exception as e:
                    raise HTTPException(
                        status_code=400, detail=f"Error flattening JSON: {str(e)}")
            elif isinstance(json_data, dict) and all(isinstance(v, list) for v in json_data.values()):
                df = pd.DataFrame(json_data)
            else:
                raise HTTPException(
                    status_code=400, detail="Unsupported JSON structure")
            sheets = ["default"]
        else:
            xls = pd.ExcelFile(file_path)
            sheets = xls.sheet_names
            df = pd.read_excel(file_path, sheet_name=sheets[0])
        return df, sheets

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        df, sheets = process_file(file, file_path)
        df['row_id'] = range(1, len(df) + 1)
        columns = list(df.columns)
        row_count = len(df)
        preview_rows = df.head(5).to_dict(orient="records")
        rows = df.to_dict(orient="records")

        with SessionLocal() as session:
            result = session.execute(
                insert(files).values(
                    filename=file.filename,
                    file_path=file_path,
                    sheets=sheets,
                    selected_sheet=sheets[0],
                    selected_columns=columns,
                    row_count=row_count,
                ).returning(files.c.id)
            )
            file_id = result.fetchone().id
            session.execute(
                insert(data).values(
                    file_id=file_id,
                    sheet_name=sheets[0],
                    row_id=max(df['row_id']),
                    rows=json.dumps(rows),
                )
            )
            session.commit()
        return {
            "id": file_id,
            "filename": file.filename,
            "file_path": file_path,
            "sheets": sheets,
            "selected_sheet": sheets[0],
            "selected_columns": columns,
            "row_count": row_count,
            "preview_rows": preview_rows,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def list_files():
    with SessionLocal() as session:
        result = session.execute(select(files)).fetchall()
        return [
            {
                "id": row.id,
                "filename": row.filename,
                "file_path": row.file_path,
                "sheets": row.sheets,
                "selected_sheet": row.selected_sheet,
                "selected_columns": row.selected_columns,
                "row_count": row.row_count,
            }
            for row in result
        ]


async def get_file(file_id: int):
    with SessionLocal() as session:
        file = session.execute(select(files).where(
            files.c.id == file_id)).fetchone()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        data_entry = session.execute(
            select(data).where(data.c.file_id == file_id,
                               data.c.sheet_name == file.selected_sheet)
        ).fetchone()
        preview_rows = []
        if data_entry:
            rows = json.loads(data_entry.rows)
            preview_rows = rows[:5]
        return {
            "id": file.id,
            "filename": file.filename,
            "file_path": file.file_path,
            "sheets": file.sheets,
            "selected_sheet": file.selected_sheet,
            "selected_columns": file.selected_columns,
            "row_count": file.row_count,
            "preview_rows": preview_rows,
        }


async def update_file(file_id: int, update):
    with SessionLocal() as session:
        file = session.execute(select(files).where(
            files.c.id == file_id)).fetchone()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        def validate_update(file, update):
            if update.selected_sheet and update.selected_sheet not in file.sheets:
                raise HTTPException(
                    status_code=400, detail="Invalid sheet name")
            if update.selected_columns:
                df = pd.read_csv(file.file_path) if file.filename.endswith('.csv') else \
                    pd.read_json(file.file_path) if file.filename.endswith('.json') else \
                    pd.read_excel(
                        file.file_path, sheet_name=update.selected_sheet or file.selected_sheet)
                valid_columns = list(df.columns)
                if not all(col in valid_columns for col in update.selected_columns):
                    raise HTTPException(
                        status_code=400, detail="Invalid columns selected")

        validate_update(file, update)
        session.execute(
            update(files)
            .where(files.c.id == file_id)
            .values(
                selected_sheet=update.selected_sheet or file.selected_sheet,
                selected_columns=update.selected_columns or file.selected_columns,
            )
        )
        session.commit()
        updated = session.execute(select(files).where(
            files.c.id == file_id)).fetchone()
        return {
            "id": updated.id,
            "filename": updated.filename,
            "file_path": updated.file_path,
            "sheets": updated.sheets,
            "selected_sheet": updated.selected_sheet,
            "selected_columns": updated.selected_columns,
            "row_count": updated.row_count,
        }


async def delete_file(file_id: int):
    with SessionLocal() as session:
        file = session.execute(select(files).where(
            files.c.id == file_id)).fetchone()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        session.execute(delete(data).where(data.c.file_id == file_id))
        session.execute(delete(files).where(files.c.id == file_id))
        session.commit()
        return {"message": "File metadata deleted"}
