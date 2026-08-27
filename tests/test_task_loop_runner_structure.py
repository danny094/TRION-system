from importlib import import_module


def test_execution_runner_is_the_only_private_owner() -> None:
    facade = import_module("core.task_loop.runner")
    execution_runner = import_module("core.task_loop.execution_runner")

    assert not hasattr(facade, "_execute_with_reflection")
    assert not hasattr(facade, "_append_completed")
    assert callable(execution_runner._execute_with_reflection)
    assert callable(execution_runner._append_completed)


def test_runner_facade_keeps_the_public_api() -> None:
    facade = import_module("core.task_loop.runner")

    assert callable(facade.run_task_loop)
    assert callable(facade.run_task_loop_with_outcome)
