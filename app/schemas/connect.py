from pydantic import BaseModel, EmailStr, Field

class ConnectRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    designation: str
    company: str
    message: str = Field(..., min_length=10)

class ConnectResponse(BaseModel):
    success: bool
    message: str
