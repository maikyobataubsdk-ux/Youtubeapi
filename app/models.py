from pydantic import BaseModel, Field, HttpUrl

class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    code: str | None = None

class JobResponse(BaseModel):
    ok: bool
    job_id: str | None = None
    data: dict | None = None
    error: str | None = None
    code: str | None = None

class SearchQuery(BaseModel):
    q: str = Field(min_length=1, max_length=200)
