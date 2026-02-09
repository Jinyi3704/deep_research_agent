"""
Commands - 命令行命令处理
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from report import export_report
from pineline.contract_loader import load_and_split_contract

from .banner import HELP_TEXT

if TYPE_CHECKING:
    from agents import ContractReviewAgent


def handle_command(user_input: str, agent: "ContractReviewAgent") -> tuple[bool, Optional[str], bool, bool]:
    """
    处理命令

    Returns: (是否已处理, 响应消息, 是否退出, 是否自动审核)
    """
    raw = user_input.strip()
    cmd = raw.lower()

    # 审核合同 / 审查合同 <路径>：硬编码加载并拆分合同，不经过 Agent 工具
    if raw.startswith("审核合同") or raw.startswith("审查合同"):
        path = raw[4:].strip()  # len("审核合同") == len("审查合同") == 4
        if not path:
            return True, "\n请提供合同文件路径，例如：审核合同 合同.docx", False, False
        result = load_and_split_contract(agent.state, path)
        return True, "\n" + result, False, False

    if cmd in ("quit", "exit", "q"):
        if agent.state.total_issues > 0:
            if input("是否导出审核报告？(y/n): ").strip().lower() in ("y", "yes"):
                filepath = export_report(agent)
                print(f"\n审核报告已导出到：{filepath}")
        print("\n再见！")
        return True, None, True, False

    if cmd == "status":
        if not agent.state.contract_name:
            return True, "\n当前没有加载合同。", False, False
        s = agent.get_status()
        issues = s.get("issues_by_severity", {})
        return True, f"""
当前审核状态：
  合同: {s.get('contract_name')}
  章节: {s.get('current_section_index', 0) + 1}/{s.get('total_sections', 0)}
  当前: {s.get('current_section_title')}
  问题: {s.get('total_issues', 0)} 个 (高:{issues.get('high', 0)} 中:{issues.get('medium', 0)} 低:{issues.get('low', 0)})
""", False, False

    if cmd == "export":
        if not agent.state.contract_name:
            return True, "\n当前没有加载合同。", False, False
        filepath = export_report(agent)
        return True, f"\n审核报告已导出到：{filepath}", False, False

    if cmd == "reset":
        agent.reset()
        return True, "\n已重置审核状态。", False, False

    if cmd in ("help", "?"):
        return True, HELP_TEXT, False, False

    if cmd in ("auto", "自动审核", "审核全部", "全部审核"):
        if not agent.state.contract_name:
            return True, "\n当前没有加载合同。请先输入 '审核合同 <文件路径>' 加载合同。", False, False
        return True, None, False, True

    return False, None, False, False
