def test_get_settings_masks_keys(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "mock"
    assert data["api_key"] == "sk-p...1234" # masked output format
    assert data["github_token"] == "ghp_...7890" # masked output format

def test_update_settings_keeps_key_if_masked(client, db_session):
    # Retrieve current values
    res = client.get("/api/settings")
    data = res.json()
    
    # Update some settings keeping masked passwords intact
    data["model"] = "new-updated-model"
    # Send the masked values back
    data["api_key"] = "sk-p...1234"
    
    update_res = client.put("/api/settings", json=data)
    assert update_res.status_code == 200
    
    # Check database directly to see if the real key was overwritten or kept
    from backend.app.models import Setting
    setting = db_session.query(Setting).first()
    assert setting.model == "new-updated-model"
    assert setting.api_key == "sk-proj-testkey1234" # kept real key!

def test_update_settings_saves_new_key(client, db_session):
    # Send a new unmasked key
    res = client.get("/api/settings")
    data = res.json()
    data["api_key"] = "new-freshly-inputted-key-value"
    
    update_res = client.put("/api/settings", json=data)
    assert update_res.status_code == 200
    
    from backend.app.models import Setting
    setting = db_session.query(Setting).first()
    assert setting.api_key == "new-freshly-inputted-key-value"

def test_test_connection_mock_success(client):
    payload = {
        "provider": "mock",
        "api_key": "",
        "base_url": "",
        "model": "mock-model"
    }
    res = client.post("/api/settings/test-connection", json=payload)
    assert res.status_code == 200
    assert res.json()["success"] is True

def test_get_models_mock_success(client):
    res = client.get("/api/settings/models?provider=mock")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "mock-model-v1" in data["models"]
    assert "limits" in data
    assert "mock-model-v1" in data["limits"]
    assert data["limits"]["mock-model-v1"]["max_output_tokens"] == 4000
    assert data["limits"]["mock-model-v1"]["chunk_size"] == 10000

def test_get_models_sorting_free_first(client):
    res = client.get("/api/settings/models?provider=openrouter")
    assert res.status_code == 200
    models = res.json()["models"]
    assert models[0] == "meta-llama/llama-3-8b-instruct:free"

def test_get_models_ollama_returns_limit_metadata(client):
    from unittest.mock import patch
    import httpx

    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        mock_get.return_value = httpx.Response(200, json={
            "models": [
                {"name": "gemma4:latest"}
            ]
        })
        mock_post.return_value = httpx.Response(200, json={
            "model_info": {
                "gemma4.context_length": 131072,
            }
        })

        res = client.get("/api/settings/models?provider=ollama&base_url=http://localhost:11434")
        assert res.status_code == 200
        data = res.json()
        assert data["limits"]["gemma4:latest"]["source"] == "detected"
        assert data["limits"]["gemma4:latest"]["notes"] == "Discovered from Ollama model metadata."
        assert data["limits"]["gemma4:latest"]["max_output_tokens"] == 16384

def test_api_keys_persistence(client, db_session):
    payload = {
        "provider": "openai",
        "api_key": "sk-openai-originalkey",
        "api_keys": {
            "openai": "sk-openai-originalkey",
            "gemini": "gemini-originalkey"
        },
        "model": "gpt-4o"
    }
    res = client.put("/api/settings", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["api_key"] == "sk-o...lkey"
    assert data["api_keys"]["openai"] == "sk-o...lkey"
    assert data["api_keys"]["gemini"] == "gemi...lkey"
    
    payload2 = {
        "provider": "gemini",
        "api_key": "gemi...lkey",
        "api_keys": {
            "openai": "sk-o...lkey",
            "gemini": "new-gemini-key-unmasked"
        },
        "model": "gemini-1.5-flash"
    }
    res2 = client.put("/api/settings", json=payload2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["api_key"] == "new-...sked"
    assert data2["api_keys"]["openai"] == "sk-o...lkey"
    assert data2["api_keys"]["gemini"] == "new-...sked"
    
    from backend.app.models import Setting
    import json
    setting = db_session.query(Setting).first()
    assert setting.api_key == "new-gemini-key-unmasked"
    
    keys = json.loads(setting.api_keys_json)
    assert keys["openai"] == "sk-openai-originalkey"
    assert keys["gemini"] == "new-gemini-key-unmasked"

def test_get_models_masked_key_resolution(client, db_session):
    from unittest.mock import patch
    import httpx
    from backend.app.models import Setting
    import json
    
    setting = db_session.query(Setting).first()
    setting.provider = "openai"
    setting.api_key = "openai-active-key"
    setting.api_keys_json = json.dumps({
        "openai": "openai-active-key",
        "openrouter": "openrouter-resolved-key-1234"
    })
    db_session.commit()

    with patch("httpx.get") as mock_get:
        mock_response = httpx.Response(200, json={"data": [{"id": "model-1"}]})
        mock_get.return_value = mock_response
        
        res = client.get("/api/settings/models?provider=openrouter&api_key=open...1234")
        assert res.status_code == 200
        
        assert mock_get.called
        args, kwargs = mock_get.call_args
        headers = kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer openrouter-resolved-key-1234"

def test_test_connection_masked_key_resolution(client, db_session):
    from unittest.mock import patch
    import httpx
    from backend.app.models import Setting
    import json
    
    setting = db_session.query(Setting).first()
    setting.provider = "openai"
    setting.api_key = "openai-active-key"
    setting.api_keys_json = json.dumps({
        "openai": "openai-active-key",
        "openrouter": "openrouter-resolved-key-5678"
    })
    db_session.commit()

    with patch("httpx.get") as mock_get:
        mock_response = httpx.Response(200, json={"data": []})
        mock_get.return_value = mock_response
        
        payload = {
            "provider": "openrouter",
            "api_key": "open...5678",
            "base_url": "",
            "model": "google/gemini-2.5-flash"
        }
        res = client.post("/api/settings/test-connection", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True
        
        assert mock_get.called
        args, kwargs = mock_get.call_args
        headers = kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer openrouter-resolved-key-5678"
