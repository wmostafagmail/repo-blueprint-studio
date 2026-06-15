import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Setting
from app.schemas import SettingUpdate, SettingResponse, TestConnectionRequest, TestConnectionResponse
from app.config import mask_secret
from app.services.providers import get_provider

router = APIRouter()


def score_latency(latency_ms: int) -> str:
    if latency_ms <= 1500:
        return "Excellent"
    if latency_ms <= 4000:
        return "Good"
    if latency_ms <= 8000:
        return "Fair"
    return "Slow"


def format_test_connection_error(provider_name: str, model: Optional[str], error: Exception) -> str:
    if isinstance(error, httpx.TimeoutException):
        if model:
            return (
                f"Connected to '{provider_name}', but model '{model}' did not answer the test prompt within 30 seconds. "
                "The model may still be loading, running too slowly, or the local runtime may be overloaded."
            )
        return (
            f"Connected to '{provider_name}', but the live response test timed out after 30 seconds."
        )

    message = str(error).strip()
    if message.lower() == "timed out":
        if model:
            return (
                f"Connected to '{provider_name}', but model '{model}' did not answer the test prompt within 30 seconds. "
                "The model may still be loading, running too slowly, or the local runtime may be overloaded."
            )
        return f"Connected to '{provider_name}', but the live response test timed out after 30 seconds."

    return message

@router.get("/settings", response_model=SettingResponse)
def get_settings(db: Session = Depends(get_db)):
    import json
    setting = db.query(Setting).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    # Return masked secrets
    response_data = SettingResponse.model_validate(setting)
    
    # Load and mask api_keys
    try:
        api_keys = json.loads(setting.api_keys_json or "{}")
    except Exception:
        api_keys = {}
        
    masked_api_keys = {p: mask_secret(k) for p, k in api_keys.items()}
    response_data.api_keys = masked_api_keys
    response_data.api_key = mask_secret(setting.api_key)
    response_data.github_token = mask_secret(setting.github_token)
    return response_data

@router.put("/settings", response_model=SettingResponse)
def update_settings(payload: SettingUpdate, db: Session = Depends(get_db)):
    import json
    setting = db.query(Setting).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Load existing keys
    try:
        api_keys = json.loads(setting.api_keys_json or "{}")
    except Exception:
        api_keys = {}

    # Update provider-specific keys from payload.api_keys
    payload_keys = payload.api_keys or {}
    for prov, key in payload_keys.items():
        if key:
            if "********" not in key and "..." not in key:
                api_keys[prov] = key
        else:
            if prov in api_keys:
                del api_keys[prov]

    # Also check if payload.api_key is sent directly
    if payload.api_key:
        if "********" not in payload.api_key and "..." not in payload.api_key:
            api_keys[payload.provider] = payload.api_key
            setting.api_key = payload.api_key
    else:
        if payload.provider in api_keys:
            del api_keys[payload.provider]
        setting.api_key = ""

    # Ensure main api_key column is updated to match the selected provider's key
    if payload.provider in api_keys:
        setting.api_key = api_keys[payload.provider]

    # Save serialized keys dict
    setting.api_keys_json = json.dumps(api_keys)

    # Update other fields. If GitHub token is masked, do not update it.
    for field, value in payload.model_dump().items():
        if field in ["api_key", "api_keys"]:
            continue
        elif field == "github_token":
            if value and "********" not in value and "..." not in value:
                setting.github_token = value
        else:
            setattr(setting, field, value)

    db.commit()
    db.refresh(setting)
    
    response_data = SettingResponse.model_validate(setting)
    
    # Return masked dict
    masked_api_keys = {p: mask_secret(k) for p, k in api_keys.items()}
    response_data.api_keys = masked_api_keys
    response_data.api_key = mask_secret(setting.api_key)
    response_data.github_token = mask_secret(setting.github_token)
    return response_data

@router.post("/settings/test-connection", response_model=TestConnectionResponse)
def test_connection(payload: TestConnectionRequest, db: Session = Depends(get_db)):
    provider_name = payload.provider
    api_key = payload.api_key
    base_url = payload.base_url
    model = payload.model
    
    # If API key is masked/hidden, pull it from database
    if not api_key or "********" in api_key or "..." in api_key:
        setting = db.query(Setting).first()
        if setting:
            import json
            try:
                api_keys = json.loads(setting.api_keys_json or "{}")
            except Exception:
                api_keys = {}
            if provider_name in api_keys and api_keys[provider_name]:
                api_key = api_keys[provider_name]
            elif setting.provider == provider_name:
                api_key = setting.api_key

    try:
        provider = get_provider(provider_name, api_key, base_url, model)
        success = provider.validate_settings()
        if success:
            probe_data = None
            if model:
                probe_data = provider.probe_model_response()
                latency_ms = probe_data["latency_ms"]
                latency_score = score_latency(latency_ms)
                return TestConnectionResponse(
                    success=True,
                    message=f"Connected successfully and received a live response from '{probe_data['model']}'.",
                    latency_ms=latency_ms,
                    latency_score=latency_score,
                    verified_model=probe_data["model"],
                    response_preview=probe_data["response_preview"],
                )
            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to provider '{provider_name}'. Select a model to test live model response time."
            )
        else:
            return TestConnectionResponse(success=False, message=f"Failed to connect to provider '{provider_name}'. Please verify API key and URL.")
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=format_test_connection_error(provider_name, model, e),
        )

@router.get("/settings/models")
def get_provider_models(
    provider: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Queries the provider directly to get a list of available models.
    """
    # If API key is masked/hidden or empty, pull it from database settings
    if not api_key or "********" in api_key or "..." in api_key:
        setting = db.query(Setting).first()
        if setting:
            import json
            try:
                api_keys = json.loads(setting.api_keys_json or "{}")
            except Exception:
                api_keys = {}
            if provider in api_keys and api_keys[provider]:
                api_key = api_keys[provider]
            elif setting.provider == provider:
                api_key = setting.api_key
            
    # Same for base_url
    if not base_url:
        setting = db.query(Setting).first()
        if setting and setting.provider == provider:
            base_url = setting.base_url

    try:
        provider_instance = get_provider(provider, api_key or "", base_url or "", "")
        models = provider_instance.list_models()
        # Sort models so the ones containing "free" are on top, then sort alphabetically
        models.sort(key=lambda m: ("free" not in m.lower(), m.lower()))
        
        limits = {}
        for m in models:
            limits[m] = provider_instance.get_model_limits(m)
            
        return {"models": models, "limits": limits}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch models: {str(e)}")
