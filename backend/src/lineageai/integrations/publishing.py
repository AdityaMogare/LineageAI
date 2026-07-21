from typing import Protocol

from pydantic import BaseModel

from lineageai.models import GeneratedModel


class GitHubModelPublisher(Protocol):
    def publish(self, run_id: str, model: GeneratedModel) -> str: ...


class DataHubModelPublisher(Protocol):
    def publish(self, model: GeneratedModel, pull_request_url: str) -> str: ...


class PublicationResult(BaseModel):
    status: str
    pull_request_url: str | None = None
    dataset_urn: str | None = None
    error: str | None = None


class PublicationCoordinator:
    def __init__(
        self,
        github: GitHubModelPublisher,
        datahub: DataHubModelPublisher,
    ) -> None:
        self.github = github
        self.datahub = datahub
        self.results: dict[str, PublicationResult] = {}

    def publish(self, run_id: str, model: GeneratedModel) -> dict[str, str | None]:
        existing = self.results.get(run_id)
        if existing and existing.status == "published":
            return existing.model_dump()

        pull_request_url = existing.pull_request_url if existing else None
        try:
            if not pull_request_url:
                pull_request_url = self.github.publish(run_id, model)
                self.results[run_id] = PublicationResult(
                    status="github_published",
                    pull_request_url=pull_request_url,
                )
            dataset_urn = self.datahub.publish(model, pull_request_url)
            result = PublicationResult(
                status="published",
                pull_request_url=pull_request_url,
                dataset_urn=dataset_urn,
            )
        except Exception as error:
            result = PublicationResult(
                status="failed",
                pull_request_url=pull_request_url,
                error=str(error),
            )
        self.results[run_id] = result
        return result.model_dump()
