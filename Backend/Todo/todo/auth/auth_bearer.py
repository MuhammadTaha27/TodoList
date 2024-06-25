import jwt
from jwt.exceptions import PyJWTError
from datetime import datetime, timedelta
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException



SECRET_KEY = "your_secret_key_here"

def create_jwt_token(user_id: int, username: str, expires_delta: timedelta = timedelta(days=1)) -> str:

        expires_at = datetime.utcnow() + expires_delta

        payload = {
            "user_id": user_id,
            "username": username,
            "exp": expires_at  
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")




async def get_current_user(token = Depends(HTTPBearer())):
        decoded_token  = jwt.decode(token.credentials, SECRET_KEY, algorithms=['HS256'])
        return decoded_token
