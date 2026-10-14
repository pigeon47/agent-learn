r"""加分项：提交前扫描项目里有没有硬编码的密钥。

运行（必须在项目根目录）：
    ..\env\python.exe -m scripts.check_secrets

约定：发现可疑内容时以退出码 1 结束，这样可以直接挂到 git 钩子或 CI 上：

    # .git/hooks/pre-commit （文件没有扩展名，内容如下两行）
    #!/bin/sh
    python -m scripts.check_secrets || exit 1

实现要求：

  1. 用 pathlib 从项目根目录递归遍历所有文件
     - 项目根目录 = Path(__file__).resolve().parent.parent
     - 跳过这些目录：.git、env、__pycache__、logs、.venv

  2. 只检查这些后缀：.py .md .json .txt .yml .yaml .toml .cfg .ini .example
     不要扫 .env（那是放真密钥的地方，而且已被 .gitignore 忽略）

  3. 用正则找两类可疑模式：
       真实 key 形态：  sk- 后面跟 16 个以上的字母数字下划线连字符
       赋值形态：       api_key / secret / token 后面跟等号或冒号，再接一个长字符串

  4. 命中时逐条打印： 文件路径、行号、该行内容（截断到 100 字符）
     并在结尾汇总"共发现 N 处可疑内容"，然后 sys.exit(1)

  5. 没命中就打印"未发现硬编码密钥"，正常退出（退出码 0）

小提示：
  - 逐行读文件：with open(p, encoding="utf-8", errors="ignore") as f
  - 正则用 re.compile 预编译，循环里直接 .search(line)
  - 别担心扫到自己源码里的正则字符串：本文件里写的模式并没有真的 key

（文档字符串前面加了字母 r，因为里面有 Windows 路径 ..\env\...。）
"""

import re
import sys
from pathlib import Path

# TODO: 实现扫描逻辑（要求见上面的 docstring）
raise SystemExit("请实现 scripts/check_secrets.py 的扫描逻辑")
