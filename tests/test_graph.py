import json
from types import SimpleNamespace
from datetime import date
from langgraph.graph import END
from agent import graph


def _fake_completion(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_tool_call(call_id, name, arguments):
    function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(id=call_id, type="function", function=function)


def test_route_after_model_with_tool_calls():
    state = {"messages": [{"role": "assistant", "content": None, "tool_calls": [{"id": "1"}]}]}
    assert graph.route_after_model(state) == "execute_tools"


def test_route_after_model_without_tool_calls():
    state = {"messages": [{"role": "assistant", "content": "done"}]}
    assert graph.route_after_model(state) == END


def test_call_model_without_tool_calls(monkeypatch):
    monkeypatch.setattr(
        graph.client.chat.completions, "create", lambda **kwargs: _fake_completion(content="hello")
    )
    result = graph.call_model({"messages": [{"role": "user", "content": "hi"}]})
    assert result == {"messages": [{"role": "assistant", "content": "hello"}]}


def test_call_model_with_tool_calls(monkeypatch):
    tool_call = _fake_tool_call("call_1", "search_flights", '{"code_type": "icao"}')
    monkeypatch.setattr(
        graph.client.chat.completions, "create", lambda **kwargs: _fake_completion(tool_calls=[tool_call])
    )
    result = graph.call_model({"messages": [{"role": "user", "content": "flights?"}]})
    message = result["messages"][0]
    assert message["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "search_flights", "arguments": '{"code_type": "icao"}'},
        }
    ]


def test_execute_tools_passes_through_string_result(monkeypatch):
    monkeypatch.setattr(graph, "AVAILABLE_TOOLS", {"str_tool": lambda **kwargs: "plain text"})
    state = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "call_1", "type": "function", "function": {"name": "str_tool", "arguments": "{}"}}
                ],
            }
        ]
    }
    result = graph.execute_tools(state)
    assert result["messages"] == [
        {"role": "tool", "tool_call_id": "call_1", "name": "str_tool", "content": "plain text"}
    ]


def test_execute_tools_json_encodes_dict_result(monkeypatch):
    monkeypatch.setattr(graph, "AVAILABLE_TOOLS", {"dict_tool": lambda **kwargs: {"foo": "bar"}})
    state = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "call_2", "type": "function", "function": {"name": "dict_tool", "arguments": "{}"}}
                ],
            }
        ]
    }
    result = graph.execute_tools(state)
    assert result["messages"][0]["content"] == json.dumps({"foo": "bar"})


def test_build_system_message_contains_today_and_tool_hint():
    message = graph.build_system_message()
    assert message["role"] == "system"
    assert date.today().isoformat() in message["content"]
    assert "search_airport" in message["content"]


def test_run_tool_unknown_tool():
    result = json.loads(graph.run_tool("does_not_exist", "{}"))
    assert "Unknown tool" in result["error"]


def test_run_tool_invalid_json():
    result = json.loads(graph.run_tool("search_airport", "{not json"))
    assert "Invalid JSON" in result["error"]


def test_run_tool_non_object_arguments():
    result = json.loads(graph.run_tool("search_airport", "[1, 2]"))
    assert "JSON object" in result["error"]


def test_run_tool_wrong_arguments(monkeypatch):
    monkeypatch.setattr(graph, "AVAILABLE_TOOLS", {"strict_tool": lambda query: query})
    result = json.loads(graph.run_tool("strict_tool", '{"wrong": 1}'))
    assert "Invalid arguments" in result["error"]


def test_create_completion_with_retry_recovers_from_rate_limit(monkeypatch):
    calls = {"count": 0}

    def flaky_create(**kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise graph.RateLimitError("slow down", response=SimpleNamespace(request=None, status_code=429, headers={}), body=None)
        return "ok"

    monkeypatch.setattr(graph.client.chat.completions, "create", flaky_create)
    monkeypatch.setattr(graph.time, "sleep", lambda seconds: None)
    assert graph.create_completion_with_retry(model="m", messages=[]) == "ok"
    assert calls["count"] == 3


def test_create_completion_with_retry_gives_up(monkeypatch):
    def always_limited(**kwargs):
        raise graph.RateLimitError("slow down", response=SimpleNamespace(request=None, status_code=429, headers={}), body=None)

    monkeypatch.setattr(graph.client.chat.completions, "create", always_limited)
    monkeypatch.setattr(graph.time, "sleep", lambda seconds: None)
    try:
        graph.create_completion_with_retry(model="m", messages=[])
    except graph.RateLimitError:
        return
    raise AssertionError("expected RateLimitError")
