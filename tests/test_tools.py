import json
from unittest.mock import patch, MagicMock
import pytest
from apple_foundation.foundation import _convert_tools_to_schema, generate

def test_convert_tools_to_schema_empty():
    assert _convert_tools_to_schema([]) == {}
    assert _convert_tools_to_schema(None) == {}

def test_convert_tools_to_schema_simple():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    schema = _convert_tools_to_schema(tools)
    
    assert "anyOf" in schema
    assert len(schema["anyOf"]) == 1
    
    option = schema["anyOf"][0]
    assert option["properties"]["function"]["const"] == "get_weather"
    assert option["properties"]["arguments"]["required"] == ["location"]

def test_convert_tools_to_schema_multiple():
    tools = [
        {
            "type": "function",
            "function": {"name": "func_a", "parameters": {}}
        },
        {
            "type": "function",
            "function": {"name": "func_b", "parameters": {}}
        }
    ]
    
    schema = _convert_tools_to_schema(tools)
    assert len(schema["anyOf"]) == 2
    assert schema["anyOf"][0]["properties"]["function"]["const"] == "func_a"
    assert schema["anyOf"][1]["properties"]["function"]["const"] == "func_b"

@patch("subprocess.run")
@patch("apple_foundation.foundation._get_binary")
def test_generate_with_tools(mock_get_binary, mock_run):
    mock_get_binary.return_value = "/path/to/generate"
    mock_run.return_value = MagicMock(returncode=0, stdout='{"function": "test", "arguments": {}}')
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "test_func",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ]
    
    generate("Call test function", tools=tools)
    
    # Check that --json-schema was passed in arguments
    call_args = mock_run.call_args[0][0]
    assert "--json-schema" in call_args
    
    # Find the schema JSON string
    schema_idx = call_args.index("--json-schema") + 1
    schema_str = call_args[schema_idx]
    schema = json.loads(schema_str)
    
    assert "anyOf" in schema
    assert schema["anyOf"][0]["properties"]["function"]["const"] == "test_func"
