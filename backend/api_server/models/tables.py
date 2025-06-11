from sqlalchemy import Column, Integer, String, MetaData, Table, JSON
from .database import engine

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
    Column("row_id", Integer),
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


def init_db():
    metadata.drop_all(bind=engine)
    metadata.create_all(bind=engine)


init_db()
