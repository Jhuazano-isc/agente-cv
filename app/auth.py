from fastapi import Header, HTTPException
from app.config import settings

async def verify_token(authorization: str = Header(...)):
    token = authorization.removeprefix("Bearer ")
    if token != settings.api_key:
        raise HTTPException(status_code=401, detail="There are not valid API token")
    
    if token != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token