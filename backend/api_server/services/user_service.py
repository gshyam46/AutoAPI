from fastapi import HTTPException
from sqlalchemy import select
from models.database import SessionLocal
from models.tables import users
from models.pydantic import UserInput


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


async def login(user: UserInput):
    with SessionLocal() as session:
        result = session.execute(select(users).where(
            users.c.email == user.email)).fetchone()
        if result and result._mapping["password"] == user.password:
            return {"message": "Login successful"}
        raise HTTPException(status_code=401, detail="Invalid credentials")
