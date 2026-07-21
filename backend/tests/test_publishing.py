from types import SimpleNamespace
from typing import Any

from lineageai.config import Settings
from lineageai.integrations.datahub import DataHubPublisher
from lineageai.integrations.github import GitHubPublisher
from lineageai.integrations.publishing import PublicationCoordinator
from lineageai.models import GeneratedModel


class NotFound(Exception):
    status = 404


class FakeRepository:
    owner = SimpleNamespace(login="acme")

    def __init__(self) -> None:
        self.branches = {"main": SimpleNamespace(commit=SimpleNamespace(sha="base-sha"))}
        self.files: dict[str, str] = {}
        self.pulls: list[Any] = []

    def get_pulls(self, **kwargs: Any) -> list[Any]:
        return self.pulls

    def get_branch(self, branch: str) -> Any:
        if branch not in self.branches:
            raise NotFound
        return self.branches[branch]

    def create_git_ref(self, ref: str, sha: str) -> None:
        self.branches[ref.removeprefix("refs/heads/")] = SimpleNamespace(
            commit=SimpleNamespace(sha=sha)
        )

    def get_contents(self, path: str, ref: str) -> Any:
        if path not in self.files:
            raise NotFound
        return SimpleNamespace(sha="file-sha")

    def create_file(self, path: str, message: str, content: str, *, branch: str) -> None:
        self.files[path] = content

    def update_file(self, path: str, message: str, content: str, sha: str, *, branch: str) -> None:
        self.files[path] = content

    def create_pull(self, **kwargs: Any) -> Any:
        pull = SimpleNamespace(html_url="https://github.test/acme/repo/pull/1")
        self.pulls.append(pull)
        return pull


class FakeEmitter:
    def __init__(self) -> None:
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        self.events.append(event)


def model() -> GeneratedModel:
    return GeneratedModel(
        name="customer_revenue",
        sql="select id from main.orders",
        schema_yml="version: 2\nmodels:\n  - name: customer_revenue\n",
        input_datasets=["orders", "customers"],
        explanation="Customer revenue",
    )


def test_github_publisher_creates_branch_files_and_pr() -> None:
    repository = FakeRepository()
    publisher = GitHubPublisher(Settings(), repository=repository)

    url = publisher.publish("run-123", model())

    assert url.endswith("/pull/1")
    assert "models/generated/customer_revenue.sql" in repository.files
    assert "models/generated/customer_revenue.yml" in repository.files
    assert "lineageai/run-123" in repository.branches


def test_github_publisher_reuses_existing_pr() -> None:
    repository = FakeRepository()
    repository.pulls.append(SimpleNamespace(html_url="https://github.test/existing"))

    url = GitHubPublisher(Settings(), repository=repository).publish("run-123", model())

    assert url == "https://github.test/existing"
    assert repository.files == {}


def test_datahub_publisher_emits_properties_tag_and_lineage() -> None:
    emitter = FakeEmitter()

    urn = DataHubPublisher(Settings(), emitter=emitter).publish(model(), "https://github.test/pr/1")

    assert urn.endswith(",main.customer_revenue,DEV)")
    assert len(emitter.events) == 3
    assert {event.aspectName for event in emitter.events} == {
        "datasetProperties",
        "globalTags",
        "upstreamLineage",
    }


def test_coordinator_retries_only_failed_datahub_step() -> None:
    class GitHub:
        calls = 0

        def publish(self, run_id: str, generated: GeneratedModel) -> str:
            self.calls += 1
            return "https://github.test/pr/1"

    class DataHub:
        calls = 0

        def publish(self, generated: GeneratedModel, pull_request_url: str) -> str:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("DataHub unavailable")
            return "urn:li:dataset:test"

    github = GitHub()
    datahub = DataHub()
    coordinator = PublicationCoordinator(github, datahub)

    first = coordinator.publish("run-123", model())
    second = coordinator.publish("run-123", model())

    assert first["status"] == "failed"
    assert second["status"] == "published"
    assert github.calls == 1
    assert datahub.calls == 2
