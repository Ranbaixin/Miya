"""One broken tool family must not remove unrelated tool families."""

from webnet.ToolNet.registry import ToolRegistry


def test_tool_family_failure_does_not_stop_later_families(monkeypatch):
    registry = ToolRegistry()
    called = []
    loaders = [name for name in dir(registry) if name.startswith("_load_") and name.endswith("_tools")]

    for name in loaders:
        if name == "_load_basic_tools":
            def fail():
                raise ImportError("optional tool dependency missing")

            monkeypatch.setattr(registry, name, fail)
        else:
            monkeypatch.setattr(registry, name, lambda name=name: called.append(name))

    registry.load_all_tools()

    assert "_load_message_tools" in called
    assert registry.load_failures["_load_basic_tools"] == "optional tool dependency missing"
