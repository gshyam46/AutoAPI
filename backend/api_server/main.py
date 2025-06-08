from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, text, JSON
from sqlalchemy.orm import sessionmaker
import json
import os
import pandas as pd
import io
from typing import List, Dict, Optional
from pydantic import BaseModel
import shutil

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup (SQLite)
DATABASE_URL = "sqlite:///autoapi.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Tables
metadata = MetaData()
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, unique=True),
    Column("password", String),
)
files = Table(
    "files",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("filename", String, unique=True),
    Column("file_path", String),
    Column("sheets", JSON),
    Column("selected_sheet", String),
    Column("selected_columns", JSON),
    Column("row_count", Integer),
)
data = Table(
    "data",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("file_id", Integer),
    Column("sheet_name", String),
    Column("row_id", Integer),  # Added for row-level identification
    Column("rows", JSON),
)
api_configs = Table(
    "api_configs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("file_id", Integer),
    Column("endpoint_path", String, unique=True),
    Column("method", String),
    Column("query_logic", JSON),
)

# Drop and recreate tables to ensure schema consistency
metadata.drop_all(bind=engine)
metadata.create_all(bind=engine)

# Pydantic models


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
    files: List[int] = []  # List of file IDs for cross-file joins
    sheets: List[str] = []  # List of sheet names for same-file joins
    on: str  # Common column to join on
    type: str = "inner"  # inner, left, right, outer


class QueryRequest(BaseModel):
    file_id: int
    sheet_name: Optional[str] = None
    operation: str
    query_logic: Optional[Dict] = None
    # Support single or bulk payload
    payload: Optional[Dict | List[Dict]] = None
    join_config: Optional[JoinConfig] = None


def validate_data_types(df: pd.DataFrame, row: Dict) -> bool:
    """Validate that row values match DataFrame column data types."""
    for col, value in row.items():
        if col not in df.columns:
            return False
        dtype = df[col].dtype
        try:
            if pd.api.types.is_numeric_dtype(dtype):
                float(value)  # Ensure numeric
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                pd.to_datetime(value)  # Ensure datetime
            elif pd.api.types.is_bool_dtype(dtype):
                if not isinstance(value, bool):
                    raise ValueError
            # String or object types are flexible
        except (ValueError, TypeError):
            return False
    return True


@app.get("/health")
async def health_check():
    return {"status": "OK"}


@app.get("/test-db")
async def test_db():
    with SessionLocal() as session:
        result = session.execute(text("SELECT 1 AS test")).mappings().all()
        return {"db_status": "OK", "result": result}


@app.post("/users")
async def create_user(user: UserInput):
    with SessionLocal() as session:
        try:
            session.execute(users.insert().values(
                email=user.email, password=user.password))
            session.commit()
            return {"message": "User created"}
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
async def login(user: UserInput):
    with SessionLocal() as session:
        result = session.execute(users.select().where(
            users.c.email == user.email)).fetchone()
        if result and result._mapping["password"] == user.password:
            return {"message": "Login successful"}
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.xlsx', '.json')):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Use CSV, Excel, or JSON.")
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        sheets = []
        df = None
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file_path)
            sheets = ["default"]
        elif file.filename.endswith('.json'):
            with open(file_path, 'r') as f:
                json_data = json.load(f)

            # Case 1: List of dicts
            if isinstance(json_data, list):
                try:
                    df = pd.json_normalize(json_data)
                except Exception as e:
                    raise HTTPException(
                        status_code=400, detail=f"Error flattening JSON: {str(e)}")

            # Case 2: Dict of lists
            elif isinstance(json_data, dict):
                if all(isinstance(v, list) for v in json_data.values()):
                    df = pd.DataFrame(json_data)
                else:
                    raise HTTPException(
                        status_code=400, detail="JSON must be a list of objects or dict of lists")
            else:
                raise HTTPException(
                    status_code=400, detail="Unsupported JSON structure")

            sheets = ["default"]

        else:
            xls = pd.ExcelFile(file_path)
            sheets = xls.sheet_names
            df = pd.read_excel(file_path, sheet_name=sheets[0])

        # Add row_id column
        df['row_id'] = range(1, len(df) + 1)
        columns = list(df.columns)
        row_count = len(df)
        preview_rows = df.head(5).to_dict(orient="records")
        rows = df.to_dict(orient="records")

        with SessionLocal() as session:
            result = session.execute(
                files.insert().values(
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
                data.insert().values(
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


@app.get("/files", response_model=List[Dict])
async def list_files():
    with SessionLocal() as session:
        result = session.execute(files.select()).fetchall()
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


@app.get("/files/{file_id}", response_model=Dict)
async def get_file(file_id: int):
    with SessionLocal() as session:
        file = session.execute(files.select().where(
            files.c.id == file_id)).fetchone()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        data_entry = session.execute(
            data.select().where(data.c.file_id == file_id,
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


@app.put("/files/{file_id}", response_model=Dict)
async def update_file(file_id: int, update: FileUpdate):
    with SessionLocal() as session:
        file = session.execute(files.select().where(
            files.c.id == file_id)).fetchone()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        if update.selected_sheet and update.selected_sheet not in file.sheets:
            raise HTTPException(status_code=400, detail="Invalid sheet name")
        if update.selected_columns:
            df = pd.read_csv(file.file_path) if file.filename.endswith('.csv') else \
                pd.read_json(file.file_path) if file.filename.endswith('.json') else \
                pd.read_excel(
                    file.file_path, sheet_name=update.selected_sheet or file.selected_sheet)
            valid_columns = list(df.columns)
            if not all(col in valid_columns for col in update.selected_columns):
                raise HTTPException(
                    status_code=400, detail="Invalid columns selected")
        session.execute(
            files.update()
            .where(files.c.id == file_id)
            .values(
                selected_sheet=update.selected_sheet or file.selected_sheet,
                selected_columns=update.selected_columns or file.selected_columns,
            )
        )
        session.commit()
        updated = session.execute(files.select().where(
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


@app.delete("/files/{file_id}")
async def delete_file(file_id: int):
    with SessionLocal() as session:
        file = session.execute(files.select().where(
            files.c.id == file_id)).fetchone()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        session.execute(data.delete().where(data.c.file_id == file_id))
        session.execute(api_configs.delete().where(
            api_configs.c.file_id == file_id))
        session.execute(files.delete().where(files.c.id == file_id))
        session.commit()
        return {"message": "File metadata deleted"}


@app.post("/api-configs", response_model=Dict)
async def create_api_config(config: APIConfigCreate):
    with SessionLocal() as session:
        try:
            file = session.execute(files.select().where(
                files.c.id == config.file_id)).fetchone()
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            if not config.endpoint_path.startswith("/"):
                config.endpoint_path = "/" + config.endpoint_path
            if config.method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
                raise HTTPException(status_code=400, detail="Invalid method")
            if "filters" in config.query_logic:
                for f in config.query_logic["filters"]:
                    if f["column"] not in file.selected_columns:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid column {f['column']}")
            if "aggregates" in config.query_logic:
                for agg in config.query_logic["aggregates"]:
                    if agg["column"] not in file.selected_columns:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid column {agg['column']}")
            result = session.execute(
                api_configs.insert().values(
                    file_id=config.file_id,
                    endpoint_path=config.endpoint_path,
                    method=config.method.upper(),
                    query_logic=json.dumps(config.query_logic),
                ).returning(api_configs.c.id)
            )
            config_id = result.fetchone().id
            session.commit()
            return {
                "id": config_id,
                "file_id": config.file_id,
                "endpoint_path": config.endpoint_path,
                "method": config.method,
                "query_logic": config.query_logic,
            }
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/api-configs", response_model=List[Dict])
async def list_api_configs():
    with SessionLocal() as session:
        result = session.execute(api_configs.select()).fetchall()
        return [
            {
                "id": row.id,
                "file_id": row.file_id,
                "endpoint_path": row.endpoint_path,
                "method": row.method,
                "query_logic": json.loads(row.query_logic),
            }
            for row in result
        ]


@app.post("/query")
async def execute_query(query: QueryRequest):
    with SessionLocal() as session:
        try:
            # Handle joins
            if query.join_config:
                dfs = []
                if query.join_config.files:  # Cross-file join
                    for fid in query.join_config.files:
                        file = session.execute(files.select().where(
                            files.c.id == fid)).fetchone()
                        if not file:
                            raise HTTPException(
                                status_code=404, detail=f"File {fid} not found")
                        sheet = query.sheet_name or file.selected_sheet
                        if file.filename.endswith('.csv'):
                            df = pd.read_csv(file.file_path)
                        elif file.filename.endswith('.json'):
                            df = pd.read_json(file.file_path)
                        else:
                            df = pd.read_excel(
                                file.file_path, sheet_name=sheet)
                        if 'row_id' not in df.columns:
                            df['row_id'] = range(1, len(df) + 1)
                        df['file_id'] = fid  # Add file_id to distinguish rows
                        dfs.append(df)
                elif query.join_config.sheets:  # Same-file sheet join
                    file = session.execute(files.select().where(
                        files.c.id == query.file_id)).fetchone()
                    if not file:
                        raise HTTPException(
                            status_code=404, detail="File not found")
                    for sheet in query.join_config.sheets:
                        if sheet not in file.sheets:
                            raise HTTPException(
                                status_code=400, detail=f"Sheet {sheet} not found")
                        df = pd.read_excel(file.file_path, sheet_name=sheet)
                        if 'row_id' not in df.columns:
                            df['row_id'] = range(1, len(df) + 1)
                        df['sheet_name'] = sheet
                        dfs.append(df)
                if not dfs:
                    raise HTTPException(
                        status_code=400, detail="No data to join")
                df = dfs[0]
                for other_df in dfs[1:]:
                    if query.join_config.on not in df.columns or query.join_config.on not in other_df.columns:
                        raise HTTPException(
                            status_code=400, detail=f"Join column {query.join_config.on} not found")
                    df = df.merge(other_df, on=query.join_config.on,
                                  how=query.join_config.type)
            else:
                # Single file/sheet
                file = session.execute(files.select().where(
                    files.c.id == query.file_id)).fetchone()
                if not file:
                    raise HTTPException(
                        status_code=404, detail="File not found")
                sheet = query.sheet_name or file.selected_sheet
                if sheet not in file.sheets:
                    raise HTTPException(
                        status_code=400, detail="Invalid sheet name")
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file.file_path)
                elif file.filename.endswith('.json'):
                    df = pd.read_json(file.file_path)
                else:
                    df = pd.read_excel(file.file_path, sheet_name=sheet)
                if 'row_id' not in df.columns:
                    df['row_id'] = range(1, len(df) + 1)

            rows = df.to_dict(orient="records")

            # Update data table
            session.execute(
                data.delete().where(data.c.file_id == query.file_id, data.c.sheet_name == sheet)
            )
            session.execute(
                data.insert().values(
                    file_id=query.file_id,
                    sheet_name=sheet,
                    row_id=max(df['row_id']) if not df.empty else 1,
                    rows=json.dumps(rows),
                )
            )

            if query.operation == "select":
                query_logic = query.query_logic or {}
                if "filters" in query_logic:
                    for f in query_logic["filters"]:
                        col, op, val = f["column"], f["operator"], f["value"]
                        if col not in df.columns:
                            raise HTTPException(
                                status_code=400, detail=f"Column {col} not found")
                        if op == ">":
                            df = df[df[col] > val]
                        elif op == "<":
                            df = df[df[col] < val]
                        elif op == "=":
                            df = df[df[col] == val]
                        elif op == ">=":
                            df = df[df[col] >= val]
                        elif op == "<=":
                            df = df[df[col] <= val]
                        elif op == "!=":
                            df = df[df[col] != val]

                agg_result = {}
                if "aggregates" in query_logic:
                    for agg in query_logic["aggregates"]:
                        col, func = agg["column"], agg["function"]
                        if col not in df.columns:
                            raise HTTPException(
                                status_code=400, detail=f"Column {col} not found")
                        if func == "sum":
                            agg_result[f"{func}_{col}"] = float(df[col].sum())
                        elif func == "avg":
                            agg_result[f"{func}_{col}"] = float(df[col].mean())
                        elif func == "count":
                            agg_result[f"{func}_{col}"] = int(df[col].count())
                        elif func == "min":
                            agg_result[f"{func}_{col}"] = float(
                                df[col].min()) if df[col].dtype.kind in 'if' else str(df[col].min())
                        elif func == "max":
                            agg_result[f"{func}_{col}"] = float(
                                df[col].max()) if df[col].dtype.kind in 'if' else str(df[col].max())

                if "group_by" in query_logic and query_logic["group_by"]:
                    group_cols = query_logic["group_by"]
                    if not all(col in df.columns for col in group_cols):
                        raise HTTPException(
                            status_code=400, detail="Invalid group_by columns")
                    agg_funcs = {agg["column"]: agg["function"]
                                 for agg in query_logic.get("aggregates", [])}
                    if agg_funcs:
                        group_df = df.groupby(group_cols).agg(
                            agg_funcs).reset_index()
                        session.commit()
                        return {"results": group_df.to_dict(orient="records")}

                session.commit()
                if agg_result:
                    return {"results": agg_result}
                return {"results": df.to_dict(orient="records")}

            elif query.operation == "insert":
                if not query.payload:
                    raise HTTPException(
                        status_code=400, detail="Payload required for insert")
                new_rows = query.payload if isinstance(
                    query.payload, list) else [query.payload]
                max_row_id = df['row_id'].max() if not df.empty else 0
                for idx, row in enumerate(new_rows):
                    if not all(col in df.columns for col in row if col != 'row_id'):
                        raise HTTPException(
                            status_code=400, detail="Invalid columns in payload")
                    if not validate_data_types(df, row):
                        raise HTTPException(
                            status_code=400, detail="Invalid data types in payload")
                    row['row_id'] = max_row_id + idx + 1
                    df = pd.concat([df, pd.DataFrame([row])],
                                   ignore_index=True)
                session.execute(
                    data.update()
                    .where(data.c.file_id == query.file_id, data.c.sheet_name == sheet)
                    .values(
                        row_id=df['row_id'].max(),
                        rows=json.dumps(df.to_dict(orient="records"))
                    )
                )
                session.execute(
                    files.update()
                    .where(files.c.id == query.file_id)
                    .values(row_count=len(df))
                )
                if file.filename.endswith('.csv'):
                    df.to_csv(file.file_path, index=False)
                elif file.filename.endswith('.json'):
                    df.to_json(file.file_path, orient='records', lines=False)
                else:
                    df.to_excel(file.file_path, sheet_name=sheet, index=False)
                session.commit()
                return {"message": f"{len(new_rows)} row(s) inserted"}

            elif query.operation == "update":
                if not query.payload or not query.query_logic:
                    raise HTTPException(
                        status_code=400, detail="Payload and query_logic required for update")
                update_rows = query.payload if isinstance(
                    query.payload, list) else [query.payload]
                condition = query.query_logic.get("filters", [])
                if not condition:
                    raise HTTPException(
                        status_code=400, detail="Filters required for update")
                mask = pd.Series([True] * len(df))
                for f in condition:
                    col, op, val = f["column"], f["operator"], f["value"]
                    if col not in df.columns:
                        raise HTTPException(
                            status_code=400, detail=f"Column {col} not found")
                    if op == "=":
                        mask &= df[col] == val
                    elif op == ">":
                        mask &= df[col] > val
                    elif op == "<":
                        mask &= df[col] < val
                for row in update_rows:
                    if not validate_data_types(df, row):
                        raise HTTPException(
                            status_code=400, detail="Invalid data types in payload")
                    for col, val in row.items():
                        if col not in df.columns or col == 'row_id':
                            continue
                        df.loc[mask, col] = val
                session.execute(
                    data.update()
                    .where(data.c.file_id == query.file_id, data.c.sheet_name == sheet)
                    .values(
                        row_id=df['row_id'].max(),
                        rows=json.dumps(df.to_dict(orient="records"))
                    )
                )
                if file.filename.endswith('.csv'):
                    df.to_csv(file.file_path, index=False)
                elif file.filename.endswith('.json'):
                    df.to_json(file.file_path, orient='records', lines=False)
                else:
                    df.to_excel(file.file_path, sheet_name=sheet, index=False)
                session.commit()
                return {"message": "Rows updated"}

            elif query.operation == "delete":
                if not query.query_logic:
                    raise HTTPException(
                        status_code=400, detail="Query_logic required for delete")
                condition = query.query_logic.get("filters", [])
                if not condition:
                    raise HTTPException(
                        status_code=400, detail="Filters required for delete")
                mask = pd.Series([True] * len(df))
                for f in condition:
                    col, op, val = f["column"], f["operator"], f["value"]
                    if col not in df.columns:
                        raise HTTPException(
                            status_code=400, detail=f"Column {col} not found")
                    if op == "=":
                        mask &= df[col] == val
                    elif op == ">":
                        mask &= df[col] > val
                    elif op == "<":
                        mask &= df[col] < val
                df = df[~mask]
                session.execute(
                    data.update()
                    .where(data.c.file_id == query.file_id, data.c.sheet_name == sheet)
                    .values(
                        row_id=df['row_id'].max() if not df.empty else 1,
                        rows=json.dumps(df.to_dict(orient="records"))
                    )
                )
                session.execute(
                    files.update()
                    .where(files.c.id == query.file_id)
                    .values(row_count=len(df))
                )
                if file.filename.endswith('.csv'):
                    df.to_csv(file.file_path, index=False)
                elif file.filename.endswith('.json'):
                    df.to_json(file.file_path, orient='records', lines=False)
                else:
                    df.to_excel(file.file_path, sheet_name=sheet, index=False)
                session.commit()
                return {"message": "Rows deleted"}

            else:
                raise HTTPException(
                    status_code=400, detail="Invalid operation")
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
