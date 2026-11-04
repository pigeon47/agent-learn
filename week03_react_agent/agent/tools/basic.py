"""基础工具：时间、计算器、天气。"""
from __future__ import annotations

import ast
import operator
from datetime import datetime

import httpx

_UA = "AgentLearn/1.0"
_TIMEOUT = 12


_WMO = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "冻雾",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    56: "冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "米雪",
    80: "小阵雨", 81: "阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷暴伴冰雹",
}



def get_time() -> str:
    """返回当前本地时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")



def _geocode(city: str) -> dict:
    """中文城市名 → 经纬度 (Open-Meteo geocoding, 免费无 Key)。"""
    resp = httpx.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": 1, "language": "zh", "format": "json"},
                     timeout=_TIMEOUT, headers={"User-Agent": _UA})
    resp.raise_for_status()
    hits = resp.json().get("results") or []
    if not hits:
        raise ValueError(f"找不到城市 [{city}] ,请换一个中文城市名")
    return hits[0]



def get_weather(city: str) -> dict:
    """联网查询城市实时天气 (Open-Meteo，免费无 Key)。"""
    g = _geocode(city)
    resp = httpx.get("https://api.open-meteo.com/v1/forecast",
                     params={"latitude": g['latitude'], "longitude": g["longitude"],
                             "current": ("temperature_2m,apparent_temperature,"
                                         "relative_humidity_2m,weather_code,wind_speed_10m"),
                                         "timezone": "auto"},
                                         timeout=_TIMEOUT, headers={"User-Agent": _UA})
    resp.raise_for_status()
    cur = resp.json().get("current") or {}
    code = cur.get("weather_code")
    return {
        "city": g["name"],
        "region": " ".join(x for x in (g.get("admin1"), g.get("country")) if x),
        "condition": _WMO.get(code, f"未知({code})"),
        "temp_c": cur.get("temperature_2m"),
        "feels_like_c": cur.get("apparent_temperature"),
        "humidity": cur.get("relative_humidity_2m"),
        "wind_kmh": cur.get("wind_speed_10m"),
        "observed_at": cur.get("time"),
        "source": "open-meteo",
        }




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
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("指数太大，拒绝计算 (防止卡死) ")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _eval(node.operand)
    raise ValueError(f"不支持的表达式成分：{type(node).__name__}")



def calculator(expression: str) -> dict:
    """只允许数字和 + - * / // % ** 及括号。"""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"表达式无法解析：{expression} ({exc:msg})") from exc
    return {"expression": expression, "value": _eval(tree)}



SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "返回当前本地日期和时间，用户问现在几点，今天几点时调用。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "计算数学表达式，支持 + - * / // % ** 和括号。"
                "简单精确计算用它; 复杂计算或数据处理用 python_exec。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "纯数学表达式，如 3**7*2 "},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "查询城市实时天气 (温度、体感、湿度、风力)。"
                "用户问某地天气、气温、是否下雨、要不要带伞时调用。"
                "支持任意中文城市名"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京 / 上海 / 拉萨"},
                },
                "required": ["city"],
            },
        },
    },
]

IMPL = {"get_time": get_time, "calculator": calculator, "get_weather": get_weather}
