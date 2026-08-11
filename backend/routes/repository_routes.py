from fastapi import APIRouter, Depends
from schemas.repository import AnalyzeRequest, AnalyzeResponse, RepositoryResponse, RepositoryListItem
from services.repository_service import RepositoryService
from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/repository", tags=["Repository"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repository(
    data: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    service = RepositoryService()
    return service.analyze(data.url, str(current_user._id))


@router.get("", response_model=list[RepositoryListItem])
async def list_repositories(current_user: User = Depends(get_current_user)):
    service = RepositoryService()
    return service.list_repositories(str(current_user._id))


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
):
    service = RepositoryService()
    return service.get_repository(repo_id, str(current_user._id))
