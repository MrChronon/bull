"""Versioned fixture and an independent, bounded Python-subset verifier.

Generated source is parsed, never exec/eval/imported. The evaluator has no access
to Python objects, attributes, filesystem or network. Use a VM/container adapter
for arbitrary build tasks; -I alone is not a security sandbox.
"""
from __future__ import annotations

import ast
import json
import math
import operator
import os
import subprocess
import sys
from pathlib import Path

TASK_ID = "PYTHON_CART_FIX_001"
TASK_VERSION = "1"
PROMPT = "Fix pricing.py to satisfy REQUIREMENTS.md. Inspect files and run_tests; finish when tests pass."
REQUIREMENTS = """Cart pricing repair, task version 1.
Implement three pure functions in pricing.py:
- subtotal(items): sum price * quantity for dictionaries in items. Empty cart -> 0.
- discount_amount(amount, percent): amount * clamped percent / 100; percent is
  clamped to [0, 100]. Return the unrounded discount amount.
- total(items, percent): subtract discount from subtotal, round once to 2 decimals.
Use Python's round semantics. Inputs have nonnegative finite prices, integer
nonnegative quantities and finite percent. Do not mutate inputs.
Keep the function names. You may define pure helper functions.
Supported Python subset: functions, return, assignment, if, for, list/dict/tuple,
subscripts, arithmetic + - * / // %, comparisons, boolean expressions,
comprehensions, calls to your helpers and sum/min/max/len/round/abs/sorted/range.
No imports, attributes/method calls, classes, exceptions, while loops, decorators,
annotations, recursion without bounds, shell or network. Only pricing.py is writable.
Verification is owned by the harness; editing tests is not supported.
"""
INITIAL_FILES = {
    "REQUIREMENTS.md": REQUIREMENTS,
    "pricing.py": """def subtotal(items):
    return sum(item['price'] for item in items)

def discount_amount(amount, percent):
    return amount * percent

def total(items, percent):
    return subtotal(items) + discount_amount(subtotal(items), percent)
""",
}
CASES = [
    ("subtotal", [[]], 0),
    ("subtotal", [[{"price": 12.5, "quantity": 3}, {"price": 4, "quantity": 0}]], 37.5),
    ("subtotal", [[{"price": 0, "quantity": 10}, {"price": 0.25, "quantity": 4}]], 1),
    ("discount_amount", [200, 10], 20),
    ("discount_amount", [80, -5], 0),
    ("discount_amount", [80, 120], 80),
    ("discount_amount", [0, 50], 0),
    ("total", [[{"price": 12.5, "quantity": 3}], 10], 33.75),
    ("total", [[{"price": 0.125, "quantity": 3}], 0], 0.38),
    ("total", [[], 15], 0),
    ("total", [[{"price": 17, "quantity": 2}], 120], 0),
    ("total", [[{"price": 17, "quantity": 2}], -10], 34),
]


class RejectedCode(ValueError):
    pass


class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value


class Evaluator:
    """Small interpreter with operation, size and call-depth budgets."""
    def __init__(self, source):
        if len(source.encode("utf-8")) > 32768:
            raise RejectedCode("source_size")
        tree = ast.parse(source)
        self.functions = {}
        self.steps = 0
        self.depth = 0
        allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
                   ast.Assign, ast.AugAssign, ast.If, ast.For, ast.Expr, ast.Pass,
                   ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Subscript,
                   ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.IfExp,
                   ast.Call, ast.ListComp, ast.GeneratorExp, ast.comprehension,
                   ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
                   ast.USub, ast.UAdd, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
                   ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.And, ast.Or, ast.Load, ast.Store)
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise RejectedCode("unsupported_syntax")
            if isinstance(node, ast.Name) and node.id.startswith("_"):
                raise RejectedCode("private_name")
            if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.keywords):
                raise RejectedCode("unsupported_call")
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if not isinstance(node, ast.FunctionDef):
                raise RejectedCode("functions_only")
            args = node.args
            if (node.decorator_list or node.returns or args.defaults or args.kwonlyargs or
                    args.vararg or args.kwarg or args.posonlyargs or
                    any(x.annotation for x in args.args) or node.name.startswith("_")):
                raise RejectedCode("plain_functions_only")
            if node.name in self.functions:
                raise RejectedCode("duplicate_function")
            self.functions[node.name] = node

    def tick(self):
        self.steps += 1
        if self.steps > 20000:
            raise RejectedCode("operation_budget")

    def bounded(self, value):
        if isinstance(value, (str, list, tuple, dict)) and len(value) > 1000:
            raise RejectedCode("value_size")
        if type(value) in (int, float) and (not math.isfinite(value) or abs(value) > 1e15):
            raise RejectedCode("numeric_size")
        return value

    def call(self, name, args):
        self.tick()
        if name in self.functions:
            fn = self.functions[name]
            if len(args) != len(fn.args.args) or self.depth >= 20:
                raise RejectedCode("call_signature_or_depth")
            self.depth += 1
            try:
                self.block(fn.body, dict(zip((x.arg for x in fn.args.args), args)))
            except ReturnValue as result:
                return result.value
            finally:
                self.depth -= 1
            return None
        builtins = {"sum": sum, "min": min, "max": max, "len": len,
                    "round": round, "abs": abs, "sorted": sorted}
        if name == "range":
            value = range(*args)
            if len(value) > 1000:
                raise RejectedCode("range_size")
            return list(value)
        if name not in builtins:
            raise RejectedCode("unsupported_function")
        return self.bounded(builtins[name](*args))

    def bind(self, target, value, env):
        if isinstance(target, ast.Name):
            env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)) and len(target.elts) == len(value):
            for node, item in zip(target.elts, value):
                self.bind(node, item, env)
        else:
            raise RejectedCode("assignment_target")

    def block(self, nodes, env):
        for node in nodes:
            self.tick()
            if isinstance(node, ast.Return):
                raise ReturnValue(self.expr(node.value, env) if node.value else None)
            elif isinstance(node, ast.Assign):
                value = self.expr(node.value, env)
                for target in node.targets:
                    self.bind(target, value, env)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                self.bind(node.target, self.binary(node.op, env[node.target.id], self.expr(node.value, env)), env)
            elif isinstance(node, ast.If):
                self.block(node.body if self.expr(node.test, env) else node.orelse, env)
            elif isinstance(node, ast.For):
                for value in self.expr(node.iter, env):
                    self.tick()
                    self.bind(node.target, value, env)
                    self.block(node.body, env)
                self.block(node.orelse, env)
            elif isinstance(node, ast.Expr):
                self.expr(node.value, env)
            elif not isinstance(node, ast.Pass):
                raise RejectedCode("unsupported_statement")

    def binary(self, op, left, right):
        if isinstance(op, ast.Mult):
            if type(left) in (str, list, tuple) and type(right) is int and len(left) * abs(right) > 1000:
                raise RejectedCode("multiply_size")
            if type(right) in (str, list, tuple) and type(left) is int and len(right) * abs(left) > 1000:
                raise RejectedCode("multiply_size")
        if isinstance(op, ast.Mod) and isinstance(left, str):
            raise RejectedCode("formatting_disabled")
        ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
        return self.bounded(ops[type(op)](left, right))

    def expr(self, node, env):
        self.tick()
        if isinstance(node, ast.Constant):
            if type(node.value) not in (str, int, float, bool, type(None)):
                raise RejectedCode("constant_type")
            return self.bounded(node.value)
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return self.bounded([self.expr(x, env) for x in node.elts])
        if isinstance(node, ast.Dict):
            return self.bounded({self.expr(k, env): self.expr(v, env) for k, v in zip(node.keys, node.values)})
        if isinstance(node, ast.Subscript):
            return self.expr(node.value, env)[self.expr(node.slice, env)]
        if isinstance(node, ast.BinOp):
            return self.binary(node.op, self.expr(node.left, env), self.expr(node.right, env))
        if isinstance(node, ast.UnaryOp):
            ops = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}
            return self.bounded(ops[type(node.op)](self.expr(node.operand, env)))
        if isinstance(node, ast.Call):
            return self.call(node.func.id, [self.expr(x, env) for x in node.args])
        if isinstance(node, ast.IfExp):
            return self.expr(node.body if self.expr(node.test, env) else node.orelse, env)
        if isinstance(node, ast.BoolOp):
            result = None
            for value in node.values:
                result = self.expr(value, env)
                if isinstance(node.op, ast.And) and not result or isinstance(node.op, ast.Or) and result:
                    break
            return result
        if isinstance(node, ast.Compare):
            ops = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
                   ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
                   ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
            left = self.expr(node.left, env)
            for op, next_node in zip(node.ops, node.comparators):
                right = self.expr(next_node, env)
                if not ops[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
            out = []
            def generate(index, scope):
                self.tick()
                if index == len(node.generators):
                    out.append(self.expr(node.elt, scope))
                    self.bounded(out)
                    return
                gen = node.generators[index]
                if gen.is_async:
                    raise RejectedCode("async_disabled")
                for value in self.expr(gen.iter, scope):
                    self.tick()
                    inner = dict(scope)
                    self.bind(gen.target, value, inner)
                    if all(self.expr(x, inner) for x in gen.ifs):
                        generate(index + 1, inner)
            generate(0, dict(env))
            return out
        raise RejectedCode("unsupported_expression")


def verify_source(source):
    failed = []
    for index, (name, args, expected) in enumerate(CASES, 1):
        try:
            worker = Evaluator(source)
            result = worker.call(name, json.loads(json.dumps(args)))
            ok = type(result) in (int, float) and abs(result - expected) < 1e-8
        except Exception:
            ok = False
        if not ok:
            failed.append(f"case_{index:02d}_{name}")
    return {"success": not failed, "passed": len(CASES) - len(failed),
            "total": len(CASES), "failed": failed, "verifier_version": "1"}


def verify_external(source, timeout=5):
    env = {k: v for k, v in os.environ.items() if k.upper() in ("SYSTEMROOT", "WINDIR")}
    result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--verify"],
                            input=json.dumps({"source": source}).encode("utf-8"),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, timeout=max(0.01, timeout),
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode not in (0, 1):
        raise RuntimeError("Verifier execution failed")
    data = json.loads(result.stdout.decode("utf-8"))
    data["exit_code"] = result.returncode
    data["success"] = data.get("success") is True and result.returncode == 0
    return data


if __name__ == "__main__":
    payload = json.loads(sys.stdin.buffer.read(100000).decode("utf-8"))
    verdict = verify_source(payload["source"])
    print(json.dumps(verdict))
    raise SystemExit(0 if verdict["success"] else 1)
