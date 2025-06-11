from fastapi import HTTPException
from sqlalchemy import select, insert, update, delete
import pandas as pd
import json
from models.database import SessionLocal
from models.tables import files, data
from models.pydantic import QueryRequest
from utils.file_utils import validate_data_types


async def execute_query(query: QueryRequest):
    with SessionLocal() as session:
        try:
            def load_data(file, sheet):
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file.file_path)
                elif file.filename.endswith('.json'):
                    df = pd.read_json(file.file_path)
                else:
                    df = pd.read_excel(file.file_path, sheet_name=sheet)
                if 'row_id' not in df.columns:
                    df['row_id'] = range(1, len(df) + 1)
                return df

            def handle_joins(query):
                dfs = []
                if query.join_config.files:
                    for fid in query.join_config.files:
                        file = session.execute(select(files).where(
                            files.c.id == fid)).fetchone()
                        if not file:
                            raise HTTPException(
                                status_code=404, detail=f"File {fid} not found")
                        sheet = query.sheet_name or file.selected_sheet
                        df = load_data(file, sheet)
                        df['file_id'] = fid
                        dfs.append(df)
                elif query.join_config.sheets:
                    file = session.execute(select(files).where(
                        files.c.id == query.file_id)).fetchone()
                    if not file:
                        raise HTTPException(
                            status_code=404, detail="File not found")
                    for sheet in query.join_config.sheets:
                        if sheet not in file.sheets:
                            raise HTTPException(
                                status_code=400, detail=f"Sheet {sheet} not found")
                        df = load_data(file, sheet)
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
                return df

            # Load data
            file = session.execute(select(files).where(
                files.c.id == query.file_id)).fetchone()
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            sheet = query.sheet_name or file.selected_sheet
            if sheet not in file.sheets:
                raise HTTPException(
                    status_code=400, detail="Invalid sheet name")

            df = handle_joins(
                query) if query.join_config else load_data(file, sheet)
            rows = df.to_dict(orient="records")

            # Update data table
            session.execute(
                delete(data).where(data.c.file_id ==
                                   query.file_id, data.c.sheet_name == sheet)
            )
            session.execute(
                insert(data).values(
                    file_id=query.file_id,
                    sheet_name=sheet,
                    row_id=max(df['row_id']) if not df.empty else 1,
                    rows=json.dumps(rows),
                )
            )

            def apply_filters(df, query_logic):
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
                return df

            def apply_aggregates(df, query_logic):
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
                return agg_result

            if query.operation == "select":
                query_logic = query.query_logic or {}
                df = apply_filters(df, query_logic)
                agg_result = apply_aggregates(df, query_logic)

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
                return {"results": agg_result or df.to_dict(orient="records")}

            elif query.operation == "insert":
                if not query.payload:
                    raise HTTPException(
                        status_code=400, detail="Payload required for insert")
                new_rows = query.payload if isinstance(
                    query.payload, list) else [query.payload]
                max_row_id = df['row_id'].max() if not df.empty else 0

                def validate_insert_rows():
                    nonlocal df
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

                validate_insert_rows()
                session.execute(
                    update(data)
                    .where(data.c.file_id == query.file_id, data.c.sheet_name == sheet)
                    .values(
                        row_id=df['row_id'].max(),
                        rows=json.dumps(df.to_dict(orient="records"))
                    )
                )
                session.execute(
                    update(files)
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

                def apply_update_condition():
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

                apply_update_condition()
                session.execute(
                    update(data)
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

                def apply_delete_condition():
                    nonlocal df
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

                apply_delete_condition()
                session.execute(
                    update(data)
                    .where(data.c.file_id == query.file_id, data.c.sheet_name == sheet)
                    .values(
                        row_id=df['row_id'].max() if not df.empty else 1,
                        rows=json.dumps(df.to_dict(orient="records"))
                    )
                )
                session.execute(
                    update(files)
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
