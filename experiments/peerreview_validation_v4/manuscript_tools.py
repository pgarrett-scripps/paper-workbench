"""Read-only MCP tools exposing exactly one staged manuscript."""

import json
import sys
from pathlib import Path


def tool_result(lines, name, args):
    if name == "read_manuscript":
        start = args.get("start_line", 1)
        end = args.get("end_line", len(lines))
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            raise ValueError("Invalid inclusive line range")
        body = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines) if start <= i+1 <= end)
    elif name == "search_manuscript":
        query = args["query"]
        if not isinstance(query, str) or not query:
            raise ValueError("A nonempty literal search query is required")
        body = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines) if query.casefold() in line.casefold())
    else:
        raise ValueError("Unknown tool")
    return {"content": [{"type": "text", "text": f"Manuscript has {len(lines)} lines.\n{body}"}]}


def main():
    lines = Path(sys.argv[1]).read_text().splitlines()
    specs = [
        {"name": "read_manuscript", "description": "Read the complete manuscript or an inclusive numbered line range.",
         "inputSchema": {"type": "object", "properties": {
             "start_line": {"type": "integer", "minimum": 1},
             "end_line": {"type": "integer", "minimum": 1}}, "additionalProperties": False}},
        {"name": "search_manuscript", "description": "Find case-insensitive literal text in the manuscript.",
         "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}},
                         "required": ["query"], "additionalProperties": False}},
    ]
    for spec in specs:
        spec["annotations"] = {"readOnlyHint": True, "destructiveHint": False,
                               "idempotentHint": True, "openWorldHint": False}
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request.get("method")
        try:
            if method == "initialize":
                value = {"protocolVersion": request["params"]["protocolVersion"],
                         "capabilities": {"tools": {}},
                         "serverInfo": {"name": "manuscript-only", "version": "1.0"}}
            elif method == "tools/list":
                value = {"tools": specs}
            elif method == "tools/call":
                params = request["params"]
                value = tool_result(lines, params["name"], params.get("arguments", {}))
            elif method == "ping":
                value = {}
            else:
                raise ValueError("Unsupported method")
            response = {"jsonrpc": "2.0", "id": request["id"], "result": value}
        except (KeyError, TypeError, ValueError) as exc:
            response = {"jsonrpc": "2.0", "id": request["id"],
                        "error": {"code": -32602, "message": str(exc)}}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
