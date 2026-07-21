from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from lineageai.agent.kimi import KimiModelGenerator
from lineageai.api.run_service import (
    InvalidRunTransitionError,
    ReviewDecision,
    RunNotFoundError,
    RunService,
    RunView,
)
from lineageai.config import get_settings
from lineageai.integrations.datahub import DataHubMetadataProvider, DataHubPublisher
from lineageai.integrations.demo import DemoMetadataProvider
from lineageai.integrations.github import GitHubPublisher
from lineageai.integrations.publishing import PublicationCoordinator
from lineageai.validation import DbtValidator

router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)


@lru_cache
def get_run_service() -> RunService:
    settings = get_settings()
    metadata_provider = (
        DataHubMetadataProvider(settings, settings.datahub_datasets)
        if settings.metadata_mode == "datahub"
        else DemoMetadataProvider()
    )
    publisher = None
    if settings.github_token and settings.github_repository:
        publisher = PublicationCoordinator(
            GitHubPublisher(settings),
            DataHubPublisher(settings),
        )
    return RunService(
        metadata_provider,
        KimiModelGenerator(settings),
        DbtValidator(),
        publisher,
    )


@router.post("", response_model=RunView, status_code=status.HTTP_201_CREATED)
def create_run(
    request: CreateRunRequest,
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunView:
    return service.start(request.prompt)


@router.get("/{run_id}", response_model=RunView)
def get_run(run_id: str, service: Annotated[RunService, Depends(get_run_service)]) -> RunView:
    try:
        return service.get(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail="Run not found") from error


@router.post("/{run_id}/review", response_model=RunView)
def review_run(
    run_id: str,
    decision: ReviewDecision,
    service: Annotated[RunService, Depends(get_run_service)],
) -> RunView:
    try:
        return service.review(run_id, decision)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail="Run not found") from error
    except InvalidRunTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
