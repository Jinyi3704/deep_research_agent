"""
Banner - 启动横幅与帮助文案
"""

HELP_TEXT = """
可用命令：
  - 审核合同 <文件路径>: 加载并开始审核合同
  - 下一章 / 继续: 审核下一章节
  - auto / 自动审核: 自动连续审核所有章节
  - status: 查看当前审核状态
  - export: 导出审核报告
  - reset: 重置审核状态
  - quit/exit: 退出程序
"""


def print_banner() -> None:
    """打印启动横幅"""
    print("=" * 60)
    print("    AI 合同审核智能体")
    print("=" * 60)
    print("\n使用: 输入 '审核合同 <文件路径>' 开始")
    print("命令: auto(自动审核) | status | export | reset | quit | help")
    print("=" * 60 + "\n")
