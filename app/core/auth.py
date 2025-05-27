from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    验证API Key
    """
    if not settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key未配置"
        )
    
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials