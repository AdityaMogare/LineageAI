from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from lineageai.agent.interfaces import MetadataProvider, ModelGenerator, ModelValidator
from lineageai.models import GeneratedModel, MetadataContext, ValidationResult


class AgentState(TypedDict, total=False):
    prompt: str
    context: MetadataContext
    draft: GeneratedModel
    validation: ValidationResult
    retry_count: int
    status: str


def build_generation_graph(
    metadata_provider: MetadataProvider,
    generator: ModelGenerator,
    validator: ModelValidator,
    *,
    max_retries: int = 3,
) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")

    def retrieve_context(state: AgentState) -> AgentState:
        if "context" in state:
            return {}
        return {"context": metadata_provider.retrieve(state["prompt"]), "retry_count": 0}

    def generate_model(state: AgentState) -> AgentState:
        validation = state.get("validation")
        draft = generator.generate(
            state["prompt"],
            state["context"],
            previous=state.get("draft"),
            diagnostics=validation.diagnostics if validation and not validation.success else None,
        )
        return {"draft": draft, "status": "validating"}

    def validate_model(state: AgentState) -> AgentState:
        result = validator.validate(state["draft"], state["context"])
        if result.success:
            return {"validation": result, "status": "awaiting_review"}
        return {
            "validation": result,
            "retry_count": state.get("retry_count", 0) + 1,
            "status": "correcting",
        }

    def mark_failed(state: AgentState) -> AgentState:
        return {"status": "failed"}

    def route_after_validation(state: AgentState) -> Literal["generate", "complete", "failed"]:
        if state["validation"].success:
            return "complete"
        if state.get("retry_count", 0) > max_retries:
            return "failed"
        return "generate"

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("generate", generate_model)
    graph.add_node("validate", validate_model)
    graph.add_node("complete", lambda state: {})
    graph.add_node("failed", mark_failed)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges("validate", route_after_validation)
    graph.add_edge("complete", END)
    graph.add_edge("failed", END)
    return graph.compile()
