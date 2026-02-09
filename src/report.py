"""
Report - 审核报告导出
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import ContractReviewAgent


def export_report(agent: "ContractReviewAgent") -> str:
    """导出审核报告到文件，返回文件路径"""
    report = agent.export_report()

    os.makedirs("reports", exist_ok=True)
    contract_name = os.path.splitext(agent.state.contract_name)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"reports/{contract_name}_审核报告_{timestamp}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    return filepath
