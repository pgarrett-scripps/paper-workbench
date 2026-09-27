"""Restricted manuscript access and bounded deterministic arithmetic checks."""

import ast
import hashlib
import json
import math
import operator
import sys
from pathlib import Path

FUNCTIONS = {"sum": sum, "min": min, "max": max, "len": len, "abs": abs,
             "round": round, "sqrt": math.sqrt, "log": math.log, "exp": math.exp,
             "mean": lambda xs: sum(xs) / len(xs)}
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
          ast.Pow: operator.pow}
COMPARE = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
           ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}


def calculate(expression):
    if not isinstance(expression, str) or len(expression) > 4000:
        raise ValueError("Expression must contain at most 4000 characters")
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > 600:
        raise ValueError("Expression is too large")

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float, bool):
            value = node.value
        elif isinstance(node, (ast.List, ast.Tuple)):
            value = [visit(x) for x in node.elts]
        elif isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub, ast.Not):
            operand = visit(node.operand)
            value = not operand if isinstance(node.op, ast.Not) else operand if isinstance(node.op, ast.UAdd) else -operand
        elif isinstance(node, ast.BinOp) and type(node.op) in BINARY:
            left, right = visit(node.left), visit(node.right)
            if type(left) not in (int, float) or type(right) not in (int, float):
                raise ValueError("Arithmetic operands must be numbers")
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("Exponent exceeds bound")
            value = BINARY[type(node.op)](left, right)
        elif isinstance(node, ast.Compare) and all(type(op) in COMPARE for op in node.ops):
            values = [visit(node.left)] + [visit(x) for x in node.comparators]
            value = all(COMPARE[type(op)](a, b) for op, a, b in zip(node.ops, values, values[1:]))
        elif isinstance(node, ast.BoolOp) and type(node.op) in (ast.And, ast.Or):
            values = [bool(visit(x)) for x in node.values]
            value = all(values) if isinstance(node.op, ast.And) else any(values)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS and not node.keywords:
            value = FUNCTIONS[node.func.id](*[visit(x) for x in node.args])
        else:
            raise ValueError("Only bounded numeric, list, Boolean expressions and documented functions are allowed")
        if isinstance(value, (int, float)) and (abs(value) > 1e100 or not math.isfinite(value)):
            raise ValueError("Numeric result exceeds bound")
        if not isinstance(value, (int, float, bool, list)):
            raise ValueError("Unsupported result type")
        return value

    return visit(tree.body)


class ManuscriptServer:
    def __init__(self, path):
        self.path = Path(path)
        self.lines = self.path.read_text().splitlines()
        self.calls = 0

    def call(self, name, args):
        self.calls += 1
        if self.calls > 18:
            return {"notice": "Tool allowance exhausted. Finish from existing evidence.", "calls_used": self.calls}
        if name == "read_manuscript":
            start, end = args.get("start_line", 1), args.get("end_line", len(self.lines))
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                raise ValueError("Invalid inclusive line range")
            return {"lines_total": len(self.lines), "text": "\n".join(f"{i + 1}: {line}" for i, line in enumerate(self.lines) if start <= i + 1 <= end)}
        if name == "search_manuscript":
            query = args["query"]
            if not isinstance(query, str) or not query:
                raise ValueError("A nonempty literal query is required")
            indices = {j for i, line in enumerate(self.lines) if query.casefold() in line.casefold()
                       for j in range(max(0, i - 2), min(len(self.lines), i + 3))}
            return {"lines_total": len(self.lines), "text": "\n".join(f"{i + 1}: {self.lines[i]}" for i in sorted(indices))}
        if name == "check_calculation":
            expression = args["expression"]
            value = calculate(expression)
            payload = {"expression": expression, "result": value}
            receipt = "T" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
            payload.update(receipt=receipt, limitation="Checks only the supplied expression, not manuscript applicability or correctness.")
            with self.path.with_name("calculation_receipts.jsonl").open("a") as stream:
                stream.write(json.dumps(payload) + "\n")
            return payload
        raise ValueError("Unknown tool")


def main():
    server = ManuscriptServer(sys.argv[1])
    specs = [
        {"name": "read_manuscript", "description": "Read the complete staged manuscript or an inclusive numbered line range. Source IDs are embedded in the text.",
         "inputSchema": {"type": "object", "properties": {"start_line": {"type": "integer", "minimum": 1}, "end_line": {"type": "integer", "minimum": 1}}, "additionalProperties": False}},
        {"name": "search_manuscript", "description": "Literal case-insensitive manuscript search with two context lines on either side.",
         "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}},
        {"name": "check_calculation", "description": "Evaluate numeric arithmetic, lists, comparisons, and/or/not. Functions: sum, mean, min, max, len, abs, round, sqrt, log, exp. No variables, strings, attributes, comprehensions, files or network. Return an execution receipt. A toy calculation does not prove applicability to the paper.",
         "inputSchema": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"], "additionalProperties": False}},
    ]
    for spec in specs:
        spec["annotations"] = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        try:
            method = request.get("method")
            if method == "initialize":
                value = {"protocolVersion": request["params"]["protocolVersion"], "capabilities": {"tools": {}}, "serverInfo": {"name": "paper-investigation", "version": "1.0"}}
            elif method == "tools/list":
                value = {"tools": specs}
            elif method == "tools/call":
                params = request["params"]
                try:
                    body = server.call(params["name"], params.get("arguments", {}))
                except (KeyError, TypeError, ValueError, ArithmeticError, SyntaxError) as exc:
                    body = {"calculation_or_request_rejected": str(exc), "note": "No successful check receipt was produced."}
                value = {"content": [{"type": "text", "text": json.dumps(body)}]}
            elif method == "ping":
                value = {}
            else:
                raise ValueError("Unsupported method")
            response = {"jsonrpc": "2.0", "id": request["id"], "result": value}
        except (KeyError, TypeError, ValueError) as exc:
            response = {"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32602, "message": str(exc)}}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
