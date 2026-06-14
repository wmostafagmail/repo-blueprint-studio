from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), default="mock")
    api_key = Column(String(255), default="")
    base_url = Column(String(255), default="")
    model = Column(String(100), default="")
    temperature = Column(Float, default=0.2)
    max_output_tokens = Column(Integer, default=4000)
    chunk_size = Column(Integer, default=10000)
    max_repo_size_mb = Column(Integer, default=100)
    max_file_size_kb = Column(Integer, default=200)
    github_token = Column(String(255), default="")
    output_dir = Column(String(255), default="")
    keep_cloned_repos = Column(Boolean, default=False)
    api_keys_json = Column(Text, default="{}")
    analysis_strategy = Column(String(50), default="hierarchical")
    map_batch_size = Column(Integer, default=5)
    generate_chunk_size = Column(Integer, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, index=True)
    repo_url = Column(String(255), nullable=False)
    repo_name = Column(String(100), nullable=False)
    status = Column(String(20), default="queued")  # queued, running, completed, failed, cancelled
    progress = Column(Integer, default=0)
    current_step = Column(String(255), default="")
    workspace_path = Column(String(255), default="")
    output_path = Column(String(255), default="")
    error_message = Column(Text, nullable=True)
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    level = Column(String(10), default="INFO")  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
