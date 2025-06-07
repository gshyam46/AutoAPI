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


class UserInput(BaseModel):
    email: str
    password: str


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

# Example table
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
    Column("sheets", JSON),
    Column("selected_sheet", String),
    Column("selected_columns", JSON),
)

data = Table(
    "data",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("file_id", Integer),
    Column("sheet_name", String),
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

# Create tables
metadata.create_all(bind=engine)


# Pydantic models
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


class QueryRequest(BaseModel):
    file_id: int
    sheet_name: Optional[str] = None
    query_logic: Dict


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/test-db")
async def test_db():
    with SessionLocal() as session:
        result = session.execute(text("SELECT 1 AS test")).mappings().all()
        return {"db_status": "connected", "result": result}


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
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Use CSV or Excel.")
    try:
        contents = await file.read()
        sheets = []
        df = None
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
            sheets = ["default"]
        else:
            xls = pd.ExcelFile(io.BytesIO(contents))
            sheets = xls.sheet_names
            df = pd.read_excel(io.BytesIO(contents), sheet_name=sheets[0])
        columns = list(df.columns)
        rows = df.to_dict(orient="records")
        with SessionLocal() as session:
            result = session.execute(
                files.insert().values(
                    filename=file.filename,
                    sheets=sheets,
                    selected_sheet=sheets[0],
                    selected_columns=columns,
                ).returning(files.c.id)
            )
            file_id = result.fetchone().id
            session.execute(
                data.insert().values(
                    file_id=file_id,
                    sheet_name=sheets[0],
                    rows=json.dumps(rows),
                )
            )
            session.commit()
        return {
            "id": file_id,
            "filename": file.filename,
            "sheets": sheets,
            "selected_sheet": sheets[0],
            "selected_columns": columns,
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
                "sheets": row.sheets,
                "selected_sheet": row.selected_sheet,
                "selected_columns": row.selected_columns,
            }
            for row in result
        ]


@app.get("/files/{file_id}", response_model=Dict)
async def get_file(file_id: int):
    with SessionLocal() as session:
        result = session.execute(files.select().where(
            files.c.id == file_id)).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        return {
            "id": result.id,
            "filename": result.filename,
            "sheets": result.sheets,
            "selected_sheet": result.selected_sheet,
            "selected_columns": result.selected_columns,
        }


@app.put("/files/{file_id}", response_model=Dict)
async def update_file(file_id: int, update: FileUpdate):
    with SessionLocal() as session:
        result = session.execute(files.select().where(
            files.c.id == file_id)).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        if update.selected_sheet and update.selected_sheet not in result.sheets:
            raise HTTPException(status_code=400, detail="Invalid sheet name")
        session.execute(
            files.update()
            .where(files.c.id == file_id)
            .values(
                selected_sheet=update.selected_sheet or result.selected_sheet,
                selected_columns=update.selected_columns or result.selected_columns,
            )
        )
        session.commit()
        updated = session.execute(files.select().where(
            files.c.id == file_id)).fetchone()
        return {
            "id": updated.id,
            "filename": updated.filename,
            "sheets": updated.sheets,
            "selected_sheet": updated.selected_sheet,
            "selected_columns": updated.selected_columns,
        }


@app.delete("/files/{file_id}")
async def delete_file(file_id: int):
    with SessionLocal() as session:
        result = session.execute(files.select().where(
            files.c.id == file_id)).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        session.execute(data.delete().where(data.c.file_id == file_id))
        session.execute(files.delete().where(files.c.id == file_id))
        session.commit()
        return {"message": "File deleted"}


@app.post("/api-configs", response_model=Dict)
async def create_api_config(config: APIConfigCreate):
    with SessionLocal() as session:
        try:
            if not config.endpoint_path.startswith("/"):
                config.endpoint_path = "/" + config.endpoint_path
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


@app.post("/query", response_model=Dict)
async def execute_query(query: QueryRequest):
    with SessionLocal() as session:
        file = session.execute(files.select().where(
            files.c.id == query.file_id)).fetchone()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        sheet = query.sheet_name or file.selected_sheet
        if sheet not in file.sheets:
            raise HTTPException(status_code=400, detail="Invalid sheet name")
        result = session.execute(
            data.select().where(data.c.file_id == query.file_id, data.c.sheet_name == sheet)
        ).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Data not found")
        rows = json.loads(result.rows)
        df = pd.DataFrame(rows)
        query_logic = query.query_logic

        # Apply filters
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

        # Apply aggregates
        agg_result = {}
        if "aggregates" in query_logic:
            for agg in query_logic["aggregates"]:
                col, func = agg["column"], agg["function"]
                if col not in df.columns:
                    raise HTTPException(
                        status_code=400, detail=f"Column {col} not found")
                if func == "sum":
                    agg_result[f"{func}_{col}"] = df[col].sum()
                elif func == "avg":
                    agg_result[f"{func}_{col}"] = df[col].mean()
                elif func == "count":
                    agg_result[f"{func}_{col}"] = df[col].count()
                elif func == "min":
                    agg_result[f"{func}_{col}"] = df[col].min()
                elif func == "max":
                    agg_result[f"{func}_{col}"] = df[col].max()

        # Apply group by
        if "group_by" in query_logic and query_logic["group_by"]:
            group_df = df.groupby(query_logic["group_by"]).agg({
                agg["column"]: agg["function"] for agg in query_logic.get("aggregates", [])
            }).reset_index()
            return group_df.to_dict(orient="records")

        if agg_result:
            return agg_result
        return df.to_dict(orient="records")
