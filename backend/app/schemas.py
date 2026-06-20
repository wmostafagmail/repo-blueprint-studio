from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

from app.services.providers.provider_limits import (
    MAX_RECOMMENDED_CHUNK_SIZE,
    MAX_RECOMMENDED_OUTPUT_TOKENS,
    MIN_SETTINGS_CHUNK_SIZE,
    MIN_SETTINGS_MAX_OUTPUT_TOKENS,
)

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
    analysis_strategy: Optional[str] = "hierarchical"
    map_batch_size: Optional[int] = 5
    generate_chunk_size: Optional[int] = 5

    @field_validator("max_output_tokens")
    @classmethod
    def validate_max_output_tokens(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < MIN_SETTINGS_MAX_OUTPUT_TOKENS:
            raise ValueError(f"max_output_tokens must be at least {MIN_SETTINGS_MAX_OUTPUT_TOKENS}")
        if value > MAX_RECOMMENDED_OUTPUT_TOKENS:
            raise ValueError(f"max_output_tokens must be at most {MAX_RECOMMENDED_OUTPUT_TOKENS}")
        return value

    @field_validator("chunk_size")
    @classmethod
    def validate_chunk_size(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < MIN_SETTINGS_CHUNK_SIZE:
            raise ValueError(f"chunk_size must be at least {MIN_SETTINGS_CHUNK_SIZE}")
        if value > MAX_RECOMMENDED_CHUNK_SIZE:
            raise ValueError(f"chunk_size must be at most {MAX_RECOMMENDED_CHUNK_SIZE}")
        return value

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
    source_job_id: Optional[str] = None
    resume_from_stage: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    parent_job_id: Optional[str] = None
    job_kind: Optional[str] = None
    stage_name: Optional[str] = None
    sort_index: Optional[int] = None
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
    duration_seconds: Optional[int] = None
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


class JobArtifactResponse(BaseModel):
    path: str
    label: str
    category: str


class JobArtifactContentResponse(BaseModel):
    path: str
    label: str
    category: str
    content: str

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
    latency_ms: Optional[int] = None
    latency_score: Optional[str] = None
    verified_model: Optional[str] = None
    response_preview: Optional[str] = None
