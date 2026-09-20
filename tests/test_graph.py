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
