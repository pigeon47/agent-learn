"""工具定义 (给模型看的 schema) + 真正执行的函数 + 统一分发。"""
from __future__ import annotations
import ast
import json
import operator
from datetime import datetime

# ------------------------------------------------------------------ 工具实现
def get_time() -> str:
    """返回当前本地时间的字符串,模型不会自己执行它,是我们要执行。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

_WEATHER = {
    "北京": {"condition": "晴","temp_c": 18},
    "上海": {"condition": "多云","temp_c": 21},
    "广州": {"condition": "小雨","temp_c": 26},
    "深圳": {"condition": "阴","temp_c": 25},
    "成都": {"condition": "阴","temp_c": 19},
}

def get_weather(city: str) -> dict:
    """mock 天气。城市不在表里就抛错,并在错误里告诉模型有哪些可用城市"""
    if city not in _WEATHER:
        raise ValueError(
            f"没有{city}的天气数据。可用城市{'、'.join(_WEATHER)}"
        )
    return {"city": city, **_WEATHER[city]}

# ------------------------------------------------------------------ 安全计算器
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance (node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("指数太大,拒绝计算(防止卡死)")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _eval(node.operand)
    raise ValueError(f"不支持的表达式成分: {type(node).__name__}")

def calculator(expression: str) -> dict:
    """只允许数字、+-*/ // % ** 和括号; 拒绝函数调用、属性访问、名字。"""
    try:
        tree = ast.parse(expression, mode = "eval")
    except SyntaxError as exc:
        raise ValueError(f"表达式无法解析: {expression} ({exc.msg})") from exc
    value = _eval(tree)
    return {"expression": expression, "value": value}

# ------------------------------------------------------------------ 给模型的声明
# description 要写「什么时候该调用」，而不是「这个函数做什么」——这决定模型选不选它
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "返回当前本地时期和时间。当前用户询问现在几点、今天几号、当前时期时调用。",
            "parameters": {"type": "object","properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "计算数学表达式,支持 + - * / // % ** 和括号。"
                "凡是需要精确计算 (乘方、多位乘除、百分数换算) 时都必须调用它,不要自己心算。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "纯数学表达式,例如 '3**7*2' 或 '(128*64)-300',不要带单位或文字",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type":"function",
        "function": {
            "name": "get_weather",
            "description": (
                "查询城市当前天气与气温,当用户询问某地天气、气温、是否下雨时调用。"
                "只支持少数城市,城市名用中文。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "中文城市名,例如'北京'"}
                },
                "required": ["city"],
            },
        },
    },
]

TOOL_IMPL = {
    "get_time": get_time,
    "calculator": calculator,
    "get_weather": get_weather,
}

def call_tool(name: str, arguments: dict) -> tuple[bool, str]:
    """执行工具,返回(是否成功,给模型看的字符串结果)。
    
    失败不抛异常,而是把错误信息当结果回传——这样模型能读到错误并自我纠正。
    """

    fn = TOOL_IMPL.get(name)
    if fn is None:
        return False, f"未知工具: {name}。可用工具: {','.join(TOOL_IMPL)}"
    try:
        result = fn(**arguments)
        return True, json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return False,f"{type(exc).__name__}: {exc}"