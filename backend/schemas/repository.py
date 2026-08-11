from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1)


class ImportantFile(BaseModel):
    file_name: str
    purpose: str
    importance: str
    explanation: str


class TechnologyItem(BaseModel):
    name: str
    reason: str


class AIInsights(BaseModel):
    complexity: str
    code_quality: str
    strengths: list[str]
    weaknesses: list[str]
    improvements: list[str]


class ArchitectureSection(BaseModel):
    folder_structure: str
    main_folders: list[dict]
    important_files: list[str]


class RepositoryAnalysis(BaseModel):
    project_summary: str
    how_it_works: str
    architecture: ArchitectureSection
    important_files: list[ImportantFile]
    technology_stack: list[TechnologyItem]
    ai_insights: AIInsights


class RepositoryResponse(BaseModel):
    id: str
    repository_name: str
    repository_url: str
    owner: str
    summary: Optional[RepositoryAnalysis] = None
    created_at: str


class RepositoryListItem(BaseModel):
    id: str
    repository_name: str
    owner: str
    repository_url: str
    created_at: str


class AnalyzeResponse(BaseModel):
    id: str
    repository_name: str
    owner: str
    repository_url: str
    status: str
    message: str


class ProgressStep(BaseModel):
    step: str
    status: str  # pending, in_progress, completed, error
