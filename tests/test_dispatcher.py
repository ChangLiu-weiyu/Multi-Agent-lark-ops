from multi_agent_lark_ops.state import WorkItem
from multi_agent_lark_ops.workflows.dispatcher import route_work_item


def test_routes_education_item() -> None:
    decision = route_work_item(WorkItem(title="完善课程课件和试讲安排"))

    assert decision.role_key == "education"
    assert decision.work_item.assigned_role == "education"


def test_routes_unclear_item_to_coordinator() -> None:
    decision = route_work_item(WorkItem(title="整理下周事项"))

    assert decision.role_key == "coordinator"
    assert decision.confidence < 0.5
