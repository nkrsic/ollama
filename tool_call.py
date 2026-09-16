# Scaffolded by Claude Sonnet
import requests, json, re

tools = [{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"]
        }
    }
}]

def try_parse_tool_call(content):
    """Attempt to extract a tool call from model text output,
    handling the several formats qwen2.5-coder is known to produce."""
    content = content.strip()

    try:
        parsed = json.loads(content)
        if "name" in parsed and "arguments" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1))
            if "name" in parsed and "arguments" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    xml_match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
    if xml_match:
        try:
            parsed = json.loads(xml_match.group(1))
            if "name" in parsed and "arguments" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    return None

messages = [{"role": "user", "content": "Explain what's going on in ./main.py"}]

response = requests.post("http://localhost:11434/api/chat", json={
    "model": "qwen2.5-coder:7b",
    "messages": messages,
    "tools": tools,
    "stream": False
})

data = response.json()

# Normalize: get real tool_calls if present, otherwise try parsing them from content
if data["message"].get("tool_calls"):
    tool_calls = data["message"]["tool_calls"]
else:
    fallback = try_parse_tool_call(data["message"]["content"])
    tool_calls = [{"function": fallback}] if fallback else None

if tool_calls:
    print("Tool call detected:", tool_calls)

    messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})

    for call in tool_calls:
        name = call["function"]["name"]
        args = call["function"]["arguments"]
        if name == "read_file":
            try:
                with open(args["path"]) as f:
                    result = f.read()
            except FileNotFoundError:
                result = f"Error: file not found at {args['path']}"
        else:
            result = f"Error: unknown tool {name}"

        messages.append({"role": "tool", "content": result})

    final = requests.post("http://localhost:11434/api/chat", json={
        "model": "qwen2.5-coder:7b",
        "messages": messages,
        "tools": tools,
        "stream": False
    })
    print(final.json()["message"]["content"])
else:
    print("No tool call — model responded directly:")
    print(data["message"]["content"])