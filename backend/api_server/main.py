from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from models.pydantic import UserInput, FileUpdate, APIConfigCreate, QueryRequest
from services.user_service import create_user, login
from services.file_service import upload_file, list_files, get_file, update_file, delete_file
from services.api_config_service import create_api_config, list_api_configs
from services.query_service import execute_query

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "OK"}


@app.get("/test-db")
async def test_db():
    from models.database import SessionLocal
    with SessionLocal() as session:
        from sqlalchemy import text
        result = session.execute(text("SELECT 1 AS test")).mappings().all()
        return {"db_status": "OK", "result": result}


@app.post("/users")
async def create_user_route(user: UserInput):
    return await create_user(user)


@app.post("/login")
async def login_route(user: UserInput):
    return await login(user)


@app.post("/upload")
async def upload_file_route(file: UploadFile = File(...)):
    return await upload_file(file)


@app.get("/files")
async def list_files_route():
    return await list_files()


@app.get("/files/{file_id}")
async def get_file_route(file_id: int):
    return await get_file(file_id)


@app.put("/files/{file_id}")
async def update_file_route(file_id: int, update: FileUpdate):
    return await update_file(file_id, update)


@app.delete("/files/{file_id}")
async def delete_file_route(file_id: int):
    return await delete_file(file_id)


@app.post("/api-configs")
async def create_api_config_route(config: APIConfigCreate):
    return await create_api_config(config)


@app.get("/api-configs")
async def list_api_configs_route():
    return await list_api_configs()


@app.post("/query")
async def execute_query_route(query: QueryRequest):
    return await execute_query(query)
