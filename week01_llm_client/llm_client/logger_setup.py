"""日志配置：一次配好，全项目共用。

用法：
    from .logger_setup import setup_logger
    log = setup_logger("main")
    log.info("程序启动")

要点（都是踩过坑才总结出来的）：
  - 同时输出到控制台和文件
  - FileHandler 必须写 encoding="utf-8"，否则 Windows 下中文乱码
  - 加 handler 前先判断，否则同一个 logger 会被打两遍
  - propagate=False，否则日志会再被 root logger 打一遍
  - 日志用占位符（log.info("x=%s", x)）而不是 f-string：
    被过滤掉时不浪费拼字符串的开销
"""

import logging
import sys
from pathlib import Path

# 日志文件放在项目根目录的 logs/ 下（该目录被 .gitignore 忽略）
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "app.log"


def setup_logger(name="app", level=logging.INFO, log_file=None):
    """创建（或复用）一个双输出的日志器。"""
    logger = logging.getLogger(name)

    # 已经配过了就直接返回，避免重复添加 handler 导致每行打印多次
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)-14s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # ① 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # ② 文件
    path = Path(log_file) if log_file else LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
