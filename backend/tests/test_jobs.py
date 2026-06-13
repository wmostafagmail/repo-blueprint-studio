def test_create_job_invalid_url(client):
    res = client.post("/api/jobs", json={"github_url": "ftp://malicious.url/repo"})
    assert res.status_code == 400
    assert "Invalid or unsafe GitHub URL" in res.json()["detail"]

def test_create_job_and_list(client):
    # Post a job
    res = client.post("/api/jobs", json={
        "github_url": "https://github.com/octocat/Spoon-Knife"
    })
    assert res.status_code == 201
    data = res.json()
    job_id = data["id"]
    assert data["repo_name"] == "Spoon-Knife"
    assert data["status"] == "queued"
    assert "provider" in data
    assert "model" in data

    # List jobs
    list_res = client.get("/api/jobs")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data) >= 1
    assert list_data[0]["id"] == job_id
    assert "provider" in list_data[0]
    assert "model" in list_data[0]

def test_cancel_job(client, db_session):
    res = client.post("/api/jobs", json={
        "github_url": "https://github.com/octocat/Spoon-Knife"
    })
    job_id = res.json()["id"]

    # Explicitly set status to 'running' in DB to avoid race condition (mock task completes instantly)
    from backend.app.models import Job
    job = db_session.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = "running"
        db_session.commit()

    # Cancel it
    cancel_res = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    
    # Verify status changed
    status_res = client.get(f"/api/jobs/{job_id}")
    assert status_res.json()["status"] == "cancelled"
