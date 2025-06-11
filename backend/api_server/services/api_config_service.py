from fastapi import HTTPException
from sqlalchemy import select, insert
import json
from models.database import SessionLocal
from models.tables import files, api_configs
from models.pydantic import APIConfigCreate


async def create_api_config(config: APIConfigCreate):
    with SessionLocal() as session:
        try:
            file = session.execute(select(files).where(
                files.c.id == config.file_id)).fetchone()
            if not file:
                raise HTTPException(status_code=404, detail="File not found")

            def validate_config(file, config):
                if not config.endpoint_path.startswith("/"):
                    config.endpoint_path = "/" + config.endpoint_path
                if config.method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
                    raise HTTPException(
                        status_code=400, detail="Invalid method")
                valid_columns = set(file.selected_columns)
                join_config = config.query_logic.get("join_config", {})

                def validate_join_config():
                    if join_config.get("files"):
                        for fid in join_config["files"]:
                            other_file = session.execute(
                                select(files).where(files.c.id == fid)).fetchone()
                            if not other_file:
                                raise HTTPException(
                                    status_code=404, detail=f"File {fid} not found")
                            valid_columns.update(other_file.selected_columns)
                    elif join_config.get("sheets"):
                        for sheet in join_config["sheets"]:
                            if sheet not in file.sheets:
                                raise HTTPException(
                                    status_code=400, detail=f"Sheet {sheet} not found")
                            df = pd.read_excel(
                                file.file_path, sheet_name=sheet)
                            valid_columns.update(df.columns)
                    if "on" in join_config and join_config["on"] not in valid_columns:
                        raise HTTPException(
                            status_code=400, detail=f"Join column {join_config['on']} not found")

                validate_join_config()

                if "filters" in config.query_logic:
                    for f in config.query_logic["filters"]:
                        if f["column"] not in valid_columns:
                            raise HTTPException(
                                status_code=400, detail=f"Invalid column {f['column']}")
                if "aggregates" in config.query_logic:
                    for agg in config.query_logic["aggregates"]:
                        if agg["column"] not in valid_columns:
                            raise HTTPException(
                                status_code=400, detail=f"Invalid column {agg['column']}")
                if "group_by" in config.query_logic and config.query_logic["group_by"]:
                    for col in config.query_logic["group_by"]:
                        if col not in valid_columns:
                            raise HTTPException(
                                status_code=400, detail=f"Invalid group_by column {col}")

            validate_config(file, config)
            result = session.execute(
                insert(api_configs).values(
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


async def list_api_configs():
    with SessionLocal() as session:
        result = session.execute(select(api_configs)).fetchall()
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
