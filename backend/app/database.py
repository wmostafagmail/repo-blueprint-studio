from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite in multi-threaded environments
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Lazy import of models to register them on Base
    import app.models
    Base.metadata.create_all(bind=engine)
    
    # Migrate existing settings table if api_keys_json column is missing
    from sqlalchemy import text
    db_mig = SessionLocal()
    try:
        db_mig.execute(text("ALTER TABLE settings ADD COLUMN api_keys_json TEXT DEFAULT '{}'"))
        db_mig.commit()
    except Exception:
        pass
        
    try:
        db_mig.execute(text("ALTER TABLE settings ADD COLUMN analysis_strategy VARCHAR(50) DEFAULT 'hierarchical'"))
        db_mig.execute(text("ALTER TABLE settings ADD COLUMN map_batch_size INTEGER DEFAULT 5"))
        db_mig.execute(text("ALTER TABLE settings ADD COLUMN generate_chunk_size INTEGER DEFAULT 5"))
        db_mig.commit()
    except Exception:
        pass

    try:
        db_mig.execute(text("UPDATE settings SET analysis_strategy = 'hierarchical' WHERE analysis_strategy IS NULL"))
        db_mig.commit()
    except Exception:
        pass
        
    try:
        db_mig.execute(text("ALTER TABLE jobs ADD COLUMN provider VARCHAR(50) NULL"))
        db_mig.execute(text("ALTER TABLE jobs ADD COLUMN model VARCHAR(100) NULL"))
        db_mig.commit()
    except Exception:
        pass
    finally:
        db_mig.close()
    
    # Initialize default settings record if empty
    db = SessionLocal()
    try:
        from app.models import Setting
        existing = db.query(Setting).first()
        if not existing:
            default_setting = Setting(
                provider="mock",
                api_key="",
                base_url="",
                model="mock-model",
                temperature=0.2,
                max_output_tokens=4000,
                chunk_size=10000,
                max_repo_size_mb=100,
                max_file_size_kb=200,
                github_token="",
                output_dir=str(backend.app.config.OUTPUTS_DIR),
                keep_cloned_repos=False
            )
            db.add(default_setting)
            db.commit()
    finally:
        db.close()
