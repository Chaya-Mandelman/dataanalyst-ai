"""LangGraph StateGraph for DataAnalyst AI.

sql_generator -> sql_validator
  -> not safe: back to sql_generator (up to 3 times, then END with an error)
  -> safe: human_approval (interrupt)
     -> not approved: END
     -> approved: sql_executor
        -> error: error_handler -> sql_executor (loop, up to 3 fixes, then END)
        -> success: visualization_selector -> response_generator -> END

Human-in-the-loop: human_approval calls langgraph.types.interrupt(). The graph
pauses there; resume it with:
    graph.invoke(Command(resume=True), config)    # approve
    graph.invoke(Command(resume=False), config)   # cancel
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    error_handler,
    human_approval,
    response_generator,
    sql_executor,
    sql_generator,
    sql_validator,
    visualization_selector,
)
from agent.state import MAX_RETRIES, AgentState


def route_after_validation(state: AgentState) -> str:
    if state.get("is_safe"):
        return "human_approval"
    if state.get("safety_retries", 0) >= MAX_RETRIES:
        return END
    return "sql_generator"


def route_after_approval(state: AgentState) -> str:
    return "sql_executor" if state.get("approved") else END


def route_after_execution(state: AgentState) -> str:
    return "error_handler" if state.get("error") else "visualization_selector"


def route_after_error(state: AgentState) -> str:
    if (state.get("final_response") or {}).get("status") == "failed":
        return END
    return "sql_executor"


def make_checkpointer() -> MemorySaver:
    """In-memory checkpointer. `results` holds a pandas DataFrame, which msgpack
    can't encode, so pickle fallback is enabled (data never leaves this process)."""
    return MemorySaver(serde=JsonPlusSerializer(pickle_fallback=True))


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)

    graph.add_node("sql_generator", sql_generator)
    graph.add_node("sql_validator", sql_validator)
    graph.add_node("human_approval", human_approval)
    graph.add_node("sql_executor", sql_executor)
    graph.add_node("error_handler", error_handler)
    graph.add_node("visualization_selector", visualization_selector)
    graph.add_node("response_generator", response_generator)

    graph.add_edge(START, "sql_generator")
    graph.add_edge("sql_generator", "sql_validator")
    graph.add_conditional_edges("sql_validator", route_after_validation,
                                ["human_approval", "sql_generator", END])
    graph.add_conditional_edges("human_approval", route_after_approval, ["sql_executor", END])
    graph.add_conditional_edges("sql_executor", route_after_execution,
                                ["error_handler", "visualization_selector"])
    graph.add_conditional_edges("error_handler", route_after_error, ["sql_executor", END])
    graph.add_edge("visualization_selector", "response_generator")
    graph.add_edge("response_generator", END)

    # NOTE: the pause comes from interrupt() inside human_approval. Adding
    # interrupt_before=["human_approval"] as well would pause twice (once before
    # the node and once inside it), so it is intentionally not used.
    return graph.compile(checkpointer=checkpointer if checkpointer is not None else make_checkpointer())


checkpointer = make_checkpointer()
app = build_graph(checkpointer)
