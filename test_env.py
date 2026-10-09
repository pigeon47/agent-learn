"""环境自检脚本 —— 在 VSCode 里按 Ctrl+F5 运行。

三行都对了,说明环境配置成功。
"""

import sys

print("解释器:", sys.executable)
print("版本:", sys.version.split()[0])

import httpx

print("httpx:", httpx.__version__)
print()
print("如果'解释器'那行显示的是 E:\\agent-learn\\env\\python.exe,就说明配好了。")
