def _create_task(data_manager, task_id: str, customer: str = "Acme Corp", status: str = "running"):
    request_body = {"customer_info": customer, "org_name": "FuseSell Org"}
    data_manager.create_task(
        task_id=task_id,
        plan_id="plan-456",
        org_id="org-123",
        request_body=request_body,
        status=status,
    )
    return request_body


def test_create_task_and_get_task_by_id(data_manager):
    task_id = "task-001"
    request_body = _create_task(data_manager, task_id)

    record = data_manager.get_task_by_id(task_id)
    assert record is not None
    assert record["task_id"] == task_id
    assert record["status"] == "running"
    assert record["request_body"]["customer_info"] == request_body["customer_info"]
    assert record["messages"] == []


def test_update_task_status_tracks_runtime(data_manager):
    task_id = "task-002"
    _create_task(data_manager, task_id)

    data_manager.update_task_status(task_id, "completed", runtime_index=4)

    record = data_manager.get_task_by_id(task_id)
    assert record["status"] == "completed"
    assert record["current_runtime_index"] == 4


def test_create_operation_and_update_status(data_manager):
    task_id = "task-003"
    _create_task(data_manager, task_id)

    operation_id = data_manager.create_operation(
        task_id, "gs_161_data_acquisition", runtime_index=0, chain_index=0, input_data={"step": 1}
    )
    operation = data_manager.get_operation(operation_id)
    assert operation is not None
    assert operation["execution_status"] == "running"
    assert operation["input_data"]["step"] == 1

    data_manager.update_operation_status(operation_id, "done", {"result": "ok"})
    updated = data_manager.get_operation(operation_id)
    assert updated["execution_status"] == "done"
    assert updated["output_data"]["result"] == "ok"


def test_get_task_with_operations_returns_summary(data_manager):
    task_id = "task-ops"
    _create_task(data_manager, task_id)

    op_a = data_manager.create_operation(
        task_id, "gs_161_data_acquisition", runtime_index=0, chain_index=0, input_data={"stage": "acquire"}
    )
    op_b = data_manager.create_operation(
        task_id, "gs_161_data_preparation", runtime_index=0, chain_index=1, input_data={"stage": "prepare"}
    )
    data_manager.update_operation_status(op_a, "done", {"status": "ok"})
    data_manager.update_operation_status(op_b, "running")

    record = data_manager.get_task_with_operations(task_id)
    assert record is not None
    assert record["task_id"] == task_id
    assert len(record["operations"]) == 2
    assert record["summary"]["completed_operations"] == 1
    assert record["summary"]["running_operations"] == 1


def test_find_sales_processes_by_customer(data_manager):
    task_acme = "task-acme"
    task_beta = "task-beta"
    _create_task(data_manager, task_acme, customer="Acme Corp")
    _create_task(data_manager, task_beta, customer="Beta LLC")

    results = data_manager.find_sales_processes_by_customer("Acme")
    assert len(results) == 1
    assert results[0]["task_id"] == task_acme
    assert results[0]["request_body"]["customer_info"] == "Acme Corp"


def test_list_tasks_filters_by_status(data_manager):
    running_id = "task-running"
    completed_id = "task-completed"
    _create_task(data_manager, running_id, status="running")
    _create_task(data_manager, completed_id, status="running")
    data_manager.update_task_status(completed_id, "completed")

    running_tasks = data_manager.list_tasks(status="running")
    completed_tasks = data_manager.list_tasks(status="completed")

    assert {task["task_id"] for task in running_tasks} == {running_id}
    assert {task["task_id"] for task in completed_tasks} == {completed_id}


def test_get_execution_timeline_orders_by_indices(data_manager):
    task_id = "task-timeline"
    _create_task(data_manager, task_id)

    op_first = data_manager.create_operation(
        task_id, "gs_161_data_acquisition", runtime_index=0, chain_index=0, input_data={"order": 1}
    )
    op_second = data_manager.create_operation(
        task_id, "gs_161_data_preparation", runtime_index=0, chain_index=1, input_data={"order": 2}
    )
    data_manager.update_operation_status(op_first, "done")
    data_manager.update_operation_status(op_second, "done")

    timeline = data_manager.get_execution_timeline(task_id)
    assert [entry["input_data"]["order"] for entry in timeline] == [1, 2]