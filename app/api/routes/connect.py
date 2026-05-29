from fastapi import APIRouter, Request, HTTPException
from app.schemas.connect import ConnectRequest, ConnectResponse
from app.services.email_service import email_service
from app.core.redis.client import redis_client
import time

router = APIRouter()

@router.post("/connect", response_model=ConnectResponse)
async def submit_contact(request: Request, data: ConnectRequest):
    # Basic IP-based rate limiting for this endpoint
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rate_limit:connect:{client_ip}"
    
    current_count = await redis_client.llen(rate_limit_key)
    if current_count and current_count > 5:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
        
    # Increment count
    await redis_client.lpush(rate_limit_key, str(time.time()))
    await redis_client.expire(rate_limit_key, 3600)  # 1 hour limit
        
    success, error_msg = await email_service.send_contact_email(
        name=data.name,
        email=data.email,
        designation=data.designation,
        company=data.company,
        message=data.message
    )
    
    if success:
        return ConnectResponse(success=True, message="Message sent successfully.")
    else:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {error_msg}")
