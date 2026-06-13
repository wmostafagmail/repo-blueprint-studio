from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def get_health():
    return {"status": "ok", "message": "Repo Blueprint Studio API is running"}
