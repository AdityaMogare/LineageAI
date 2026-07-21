from typing import Any, cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command
from pydantic import BaseModel, Field

from lineageai.agent.graph import AgentState, build_generation_graph
from lineageai.agent.interfaces import MetadataProvider, ModelGenerator, ModelValidator
from lineageai.models import GeneratedModel, ValidationResult


class RunView(BaseModel):
    id: str
    prompt: str
    status: str
    retry_count: int = 0
    draft: GeneratedModel | None = None
    validation: ValidationResult | None = None
    feedback: str | None = None
    publication: dict[str, Any] | None = None


class ReviewDecision(BaseModel):
    approved: bool
    feedback: str | None = Field(default=None, max_length=2000)


class RunNotFoundError(KeyError):
    pass


class InvalidRunTransitionError(RuntimeError):
    pass


class RunService:
    def __init__(
        self,
        metadata_provider: MetadataProvider,
        generator: ModelGenerator,
        validator: ModelValidator,
    ) -> None:
        self.checkpointer = InMemorySaver(
            serde=JsonPlusSerializer(
                allowed_msgpack_modules=[
                    ("lineageai.models", "ColumnMetadata"),
                    ("lineageai.models", "DatasetMetadata"),
                    ("lineageai.models", "ForeignKeyMetadata"),
                    ("lineageai.models", "GeneratedModel"),
                    ("lineageai.models", "MetadataContext"),
                    ("lineageai.models", "ValidationDiagnostic"),
                    ("lineageai.models", "ValidationResult"),
                ]
            )
        )
        self.graph = build_generation_graph(
            metadata_provider,
            generator,
            validator,
            pause_for_review=True,
            checkpointer=self.checkpointer,
        )
        self.prompts: dict[str, str] = {}
        self.feedback: dict[str, str | None] = {}

    def start(self, prompt: str) -> RunView:
        run_id = str(uuid4())
        self.prompts[run_id] = prompt
        config = self._config(run_id)
        initial: AgentState = {"prompt": prompt}
        self.graph.invoke(initial, config=config)
        return self.get(run_id)

    def get(self, run_id: str) -> RunView:
        if run_id not in self.prompts:
            raise RunNotFoundError(run_id)
        snapshot = self.graph.get_state(self._config(run_id))
        state = cast(AgentState, snapshot.values)
        return self._view(run_id, state)

    def review(self, run_id: str, decision: ReviewDecision) -> RunView:
        current = self.get(run_id)
        if current.status != "awaiting_review":
            raise InvalidRunTransitionError(
                f"Run {run_id} cannot be reviewed from status {current.status}"
            )
        self.feedback[run_id] = decision.feedback
        resume: Command[Any] = Command(resume=decision.model_dump())
        self.graph.invoke(
            resume,
            config=self._config(run_id),
        )
        return self.get(run_id)

    @staticmethod
    def _config(run_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": run_id}}

    def _view(self, run_id: str, state: AgentState) -> RunView:
        return RunView(
            id=run_id,
            prompt=self.prompts[run_id],
            status=state.get("status", "running"),
            retry_count=state.get("retry_count", 0),
            draft=state.get("draft"),
            validation=state.get("validation"),
            feedback=self.feedback.get(run_id),
        )
