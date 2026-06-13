import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.services.summary_service import should_preserve_raw, SummaryMapService
from backend.app.services.reduce_service import ReduceService
from backend.app.services.incremental_generator import IncrementalSpecGenerator
from backend.app.services.providers.mock_provider import MockProvider
from backend.app.services.analysis_service import AnalysisService
from backend.app.models import Setting, Job

def test_should_preserve_raw_rules():
    assert should_preserve_raw("package.json") is True
    assert should_preserve_raw("schema.prisma") is True
    assert should_preserve_raw("backend/app/models.py") is True
    assert should_preserve_raw("frontend/src/routes.ts") is True
    assert should_preserve_raw("src/components/Button.tsx") is False

def test_summary_map_service_raw_vs_mock_summarize(tmp_path):
    provider = MockProvider()
    log_mock = MagicMock()
    progress_mock = MagicMock()
    
    # Create test repo folder
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    
    # Create a raw file (package.json)
    package_json = repo_path / "package.json"
    package_json.write_text('{"name": "test-pkg"}')
    
    # Create a normal source code file to summarize
    helper_file = repo_path / "utils.py"
    helper_file.write_text("def add(a, b): return a + b")
    
    service = SummaryMapService(
        provider=provider,
        workspace_path=tmp_path,
        log_fn=log_mock,
        progress_fn=progress_mock
    )
    
    # Test package.json raw preservation
    res_raw = service.summarize_file("package.json", repo_path)
    assert res_raw["type"] == "raw"
    assert "test-pkg" in res_raw["content"]
    
    # Test utils.py summarization
    res_sum = service.summarize_file("utils.py", repo_path)
    assert res_sum["type"] == "summary" or res_sum["type"] == "text"

def test_reduce_service_grouping_and_synthesis(tmp_path):
    provider = MockProvider()
    log_mock = MagicMock()
    progress_mock = MagicMock()
    
    summaries = [
        {"path": "backend/app/api/auth.py", "type": "summary", "responsibilities": ["Auth API"], "exports": [], "dependencies": []},
        {"path": "backend/app/api/users.py", "type": "summary", "responsibilities": ["Users API"], "exports": [], "dependencies": []},
        {"path": "frontend/src/components/Header.tsx", "type": "summary", "responsibilities": ["Header UI"], "exports": [], "dependencies": []}
    ]
    
    service = ReduceService(
        provider=provider,
        workspace_path=tmp_path,
        log_fn=log_mock,
        progress_fn=progress_mock
    )
    
    # Test grouping
    groups = service.group_by_components(summaries)
    assert "backend/app" in groups
    assert len(groups["backend/app"]) == 2
    assert "frontend/src" in groups
    assert len(groups["frontend/src"]) == 1
    
    # Test synthesis
    specs = service.reduce_summaries(summaries)
    assert "backend/app" in specs
    assert "frontend/src" in specs

def test_incremental_spec_generator_chunks(tmp_path):
    provider = MockProvider()
    log_mock = MagicMock()
    progress_mock = MagicMock()
    
    generator = IncrementalSpecGenerator(
        provider=provider,
        workspace_path=tmp_path,
        log_fn=log_mock,
        progress_fn=progress_mock
    )
    
    blueprint = generator.generate_blueprint(
        repo_url="https://github.com/test/repo",
        repo_name="test-repo",
        file_tree=["package.json", "utils.py"],
        manifests_content="package.json: {}",
        component_specs={"backend/app": "Backend spec details"}
    )
    
    # Verify that the blueprint was assembled and contains mock output
    assert len(blueprint) > 0
    # Direct mock provider output contains title
    assert "# test-repo Rebuild Blueprint" in blueprint

def test_full_hierarchical_analysis_pipeline(client, db_session, tmp_path):
    # Set settings to hierarchical
    setting = db_session.query(Setting).first()
    setting.analysis_strategy = "hierarchical"
    setting.map_batch_size = 2
    setting.generate_chunk_size = 5
    db_session.commit()
    
    # Setup job
    job = Job(
        id="test-job-hierarchical-1234",
        repo_url="https://github.com/mock/repo.git",
        repo_name="mock-repo",
        status="queued"
    )
    db_session.add(job)
    db_session.commit()
    
    # Mock git clone so it returns a mock directory with files
    with patch("backend.app.services.git_service.GitService.clone_repository") as mock_clone:
        # Create mock repo contents
        repo_dir = tmp_path / "cloned_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "package.json").write_text('{"name": "mock"}')
        (repo_dir / "app.py").write_text('print("hello")')
        
        mock_clone.return_value = repo_dir
        
        analysis_service = AnalysisService(db_session, job.id)
        
        # We need to mock JOBS_DIR and OUTPUTS_DIR inside analysis_service
        (tmp_path / "jobs").mkdir(parents=True, exist_ok=True)
        (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
        
        with patch("backend.app.services.analysis_service.JOBS_DIR", tmp_path / "jobs"), \
             patch("backend.app.services.analysis_service.OUTPUTS_DIR", tmp_path / "outputs"):
            
            # Run pipeline
            analysis_service.run_analysis(job.repo_url)
            
            # Retrieve completed job
            db_session.refresh(job)
            assert job.error_message is None
            assert job.status == "completed"
            assert job.progress == 100
            
            # Output file exists
            output_file = Path(job.output_path)
            assert output_file.exists()
            content = output_file.read_text(encoding="utf-8")
            assert "Hierarchical (Map-Reduce)" in content
