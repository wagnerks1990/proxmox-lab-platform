from pydantic import BaseModel


class ValidationCheck(BaseModel):
    name: str
    status: str
    severity: str
    message: str
    suggested_fix: str
