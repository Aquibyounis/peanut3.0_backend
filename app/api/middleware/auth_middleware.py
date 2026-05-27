from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from app.core.security.jwt import verify_token
from jose import JWTError

class AuthMiddleware(BaseHTTPMiddleware):
    """Optional middleware to parse JWT token without blocking public routes."""
    
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        
        request.state.user = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = verify_token(token)
                request.state.user = payload
            except JWTError:
                # We don't fail here, we let the route's dependency handle auth enforcement
                pass
                
        return await call_next(request)
