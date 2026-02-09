"""
SessionLog - 会话日志持久化
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List


def save_session_log(logs: List[dict], contract_name: str = "") -> str:
    """保存会话日志到文件，返回文件路径"""
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if contract_name:
        name = os.path.splitext(contract_name)[0]
        filepath = f"logs/{name}_会话日志_{timestamp}.md"
    else:
        filepath = f"logs/会话日志_{timestamp}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# 合同审核会话日志\n\n")
        f.write(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if contract_name:
            f.write(f"**合同**: {contract_name}\n")
        f.write("\n---\n\n")

        for entry in logs:
            step = entry.get('step', '')
            step_str = f" Step {step}" if step else ""
            f.write(f"## [{entry['time']}{step_str}] {entry['role']}\n\n")
            f.write(f"{entry['content']}\n\n")

    return filepath
