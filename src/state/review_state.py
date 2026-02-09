"""
Review State - 合同审核状态

管理合同审核过程中的状态数据：
- 合同信息
- 章节列表
- 问题点列表
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    """问题严重程度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueStatus(str, Enum):
    """问题状态"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    RESOLVED = "resolved"


@dataclass
class Section:
    """合同章节"""
    index: int
    title: str
    content: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "content": self.content,
        }


@dataclass
class Issue:
    """问题点"""
    id: str
    section_index: int
    clause: str
    problem: str
    severity: Severity
    suggestion: str
    status: IssueStatus = IssueStatus.PENDING
    user_feedback: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "section_index": self.section_index,
            "clause": self.clause,
            "problem": self.problem,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
            "status": self.status.value,
            "user_feedback": self.user_feedback,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Issue:
        return cls(
            id=data["id"],
            section_index=data["section_index"],
            clause=data["clause"],
            problem=data["problem"],
            severity=Severity(data["severity"]),
            suggestion=data["suggestion"],
            status=IssueStatus(data.get("status", "pending")),
            user_feedback=data.get("user_feedback"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class ReviewState:
    """
    合同审核状态
    
    管理整个合同审核过程的状态。
    """
    contract_name: str = ""
    contract_path: str = ""
    sections: list[Section] = field(default_factory=list)
    current_section_index: int = 0
    issues: list[Issue] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    # 统计信息
    @property
    def total_sections(self) -> int:
        return len(self.sections)
    
    @property
    def total_issues(self) -> int:
        return len(self.issues)
    
    @property
    def current_section(self) -> Optional[Section]:
        if 0 <= self.current_section_index < len(self.sections):
            return self.sections[self.current_section_index]
        return None
    
    @property
    def is_complete(self) -> bool:
        """是否已审核完所有章节"""
        return self.current_section_index >= len(self.sections)
    
    def reset(self) -> None:
        """重置状态"""
        self.contract_name = ""
        self.contract_path = ""
        self.sections = []
        self.current_section_index = 0
        self.issues = []
        self.created_at = datetime.now()
    
    def add_section(self, title: str, content: str) -> Section:
        """添加章节"""
        section = Section(
            index=len(self.sections),
            title=title,
            content=content,
        )
        self.sections.append(section)
        return section
    
    def next_section(self) -> Optional[Section]:
        """切换到下一章节"""
        if self.current_section_index < len(self.sections) - 1:
            self.current_section_index += 1
            return self.current_section
        return None
    
    def prev_section(self) -> Optional[Section]:
        """切换到上一章节"""
        if self.current_section_index > 0:
            self.current_section_index -= 1
            return self.current_section
        return None
    
    def go_to_section(self, index: int) -> Optional[Section]:
        """跳转到指定章节"""
        if 0 <= index < len(self.sections):
            self.current_section_index = index
            return self.current_section
        return None
    
    def add_issue(
        self,
        clause: str,
        problem: str,
        severity: Severity,
        suggestion: str,
        section_index: Optional[int] = None,
    ) -> Issue:
        """添加问题点"""
        idx = section_index if section_index is not None else self.current_section_index
        issue_id = f"{idx + 1}-{len([i for i in self.issues if i.section_index == idx]) + 1}"
        
        issue = Issue(
            id=issue_id,
            section_index=idx,
            clause=clause,
            problem=problem,
            severity=severity,
            suggestion=suggestion,
        )
        self.issues.append(issue)
        return issue
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """获取问题点"""
        for issue in self.issues:
            if issue.id == issue_id:
                return issue
        return None
    
    def update_issue(
        self,
        issue_id: str,
        **kwargs: Any,
    ) -> Optional[Issue]:
        """更新问题点"""
        issue = self.get_issue(issue_id)
        if issue:
            for key, value in kwargs.items():
                if hasattr(issue, key):
                    if key == "severity" and isinstance(value, str):
                        value = Severity(value)
                    elif key == "status" and isinstance(value, str):
                        value = IssueStatus(value)
                    setattr(issue, key, value)
            issue.updated_at = datetime.now()
        return issue
    
    def delete_issue(self, issue_id: str) -> bool:
        """删除问题点"""
        for i, issue in enumerate(self.issues):
            if issue.id == issue_id:
                self.issues.pop(i)
                return True
        return False
    
    def confirm_issue(self, issue_id: str) -> Optional[Issue]:
        """确认问题点"""
        return self.update_issue(issue_id, status=IssueStatus.CONFIRMED)
    
    def reject_issue(self, issue_id: str, feedback: Optional[str] = None) -> Optional[Issue]:
        """拒绝问题点"""
        return self.update_issue(issue_id, status=IssueStatus.REJECTED, user_feedback=feedback)
    
    def get_current_section_issues(self) -> list[Issue]:
        """获取当前章节的问题点"""
        return [i for i in self.issues if i.section_index == self.current_section_index]
    
    def get_issues_by_section(self, section_index: int) -> list[Issue]:
        """获取指定章节的问题点"""
        return [i for i in self.issues if i.section_index == section_index]
    
    def get_issues_by_severity(self, severity: Severity) -> list[Issue]:
        """获取指定严重程度的问题点"""
        return [i for i in self.issues if i.severity == severity]
    
    def get_issues_by_status(self, status: IssueStatus) -> list[Issue]:
        """获取指定状态的问题点"""
        return [i for i in self.issues if i.status == status]
    
    def count_issues_by_severity(self) -> dict[str, int]:
        """按严重程度统计问题点数量"""
        return {
            "high": len([i for i in self.issues if i.severity == Severity.HIGH]),
            "medium": len([i for i in self.issues if i.severity == Severity.MEDIUM]),
            "low": len([i for i in self.issues if i.severity == Severity.LOW]),
        }
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "contract_name": self.contract_name,
            "contract_path": self.contract_path,
            "sections": [s.to_dict() for s in self.sections],
            "current_section_index": self.current_section_index,
            "issues": [i.to_dict() for i in self.issues],
            "created_at": self.created_at.isoformat(),
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def export_report(self) -> str:
        """导出审核报告"""
        lines = [
            f"# 合同审核报告",
            f"",
            f"**合同名称**: {self.contract_name}",
            f"**审核时间**: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**章节总数**: {self.total_sections}",
            f"**问题点总数**: {self.total_issues}",
            f"",
        ]
        
        # 按严重程度统计
        severity_counts = self.count_issues_by_severity()
        lines.append("## 问题统计")
        lines.append("")
        lines.append(f"- 高风险: {severity_counts['high']} 个")
        lines.append(f"- 中风险: {severity_counts['medium']} 个")
        lines.append(f"- 低风险: {severity_counts['low']} 个")
        lines.append("")
        
        # 按章节列出问题
        lines.append("## 问题详情")
        lines.append("")
        
        for section in self.sections:
            section_issues = self.get_issues_by_section(section.index)
            if section_issues:
                lines.append(f"### {section.title}")
                lines.append("")
                
                for issue in section_issues:
                    status_icon = {
                        IssueStatus.PENDING: "⏳",
                        IssueStatus.CONFIRMED: "✅",
                        IssueStatus.REJECTED: "❌",
                        IssueStatus.RESOLVED: "✔️",
                    }.get(issue.status, "")
                    
                    severity_icon = {
                        Severity.HIGH: "🔴",
                        Severity.MEDIUM: "🟡",
                        Severity.LOW: "🟢",
                    }.get(issue.severity, "")
                    
                    lines.append(f"#### [{issue.id}] {severity_icon} {issue.problem} {status_icon}")
                    lines.append("")
                    lines.append(f"**相关条款**: {issue.clause}")
                    lines.append("")
                    lines.append(f"**建议**: {issue.suggestion}")
                    lines.append("")
                    if issue.user_feedback:
                        lines.append(f"**用户反馈**: {issue.user_feedback}")
                        lines.append("")
        
        return "\n".join(lines)
