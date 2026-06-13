from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

# Settings Schemas
class SettingBase(BaseModel):
    provider: str
    api_key: Optional[str] = ""
    base_url: Optional[str] = ""
    model: Optional[str] = ""
    temperature: Optional[float] = 0.2
    max_output_tokens: Optional[int] = 4000
    chunk_size: Optional[int] = 10000
    max_repo_size_mb: Optional[int] = 100
    max_file_size_kb: Optional[int] = 200
    github_token: Optional[str] = ""
    output_dir: Optional[str] = ""
    keep_cloned_repos: Optional[bool] = False
    api_keys: Optional[dict] = {}
    analysis_strategy: Optional[str] = "direct"
    map_batch_size: Optional[int] = 5
    generate_chunk_size: Optional[int] = 5

class SettingUpdate(SettingBase):
    pass

class SettingResponse(SettingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Job Schemas
class JobCreate(BaseModel):
    github_url: str
    github_token: Optional[str] = None
    provider_override: Optional[str] = None
    model_override: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    repo_url: str
    repo_name: str
    status: str
    progress: int
    current_step: str
    provider: Optional[str] = None
    model: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None

    class Config:
        from_attributes = True

# Job Log Schemas
class JobLogResponse(BaseModel):
    id: int
    job_id: str
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

# Test Connection Schemas
class TestConnectionRequest(BaseModel):
    provider: str
    api_key: Optional[str] = ""
    base_url: Optional[str] = ""
    model: Optional[str] = ""
    temperature: Optional[float] = 0.2

class TestConnectionResponse(BaseModel):
    success: bool
    message: str
