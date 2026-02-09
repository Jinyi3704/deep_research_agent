"""
Contract Tools - 合同审核工具

提供合同审核相关的工具：
- manage_issues: 问题点管理
- rag_query: 知识库查询
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from core.tool import BaseTool, ToolRegistry, ToolSchema
from state import ReviewState, Severity, IssueStatus


class ManageIssuesTool(BaseTool):
    """
    问题点管理工具
    
    支持添加、更新、删除、列出问题点，
    以及章节导航和报告导出。
    """
    
    def __init__(self, state: ReviewState):
        self._state = state
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="manage_issues",
            description="管理合同审核问题点。支持的操作：add（添加）、update（更新）、delete（删除）、list（列出）、confirm（确认）、reject（拒绝）、get_current_section（获取当前章节）、next_section（下一章节）、prev_section（上一章节）、export（导出报告）",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "操作类型",
                        "enum": ["add", "update", "delete", "list", "confirm", "reject", "get_current_section", "next_section", "prev_section", "export"],
                    },
                    "issue_id": {
                        "type": "string",
                        "description": "问题点 ID（用于 update/delete/confirm/reject 操作）",
                    },
                    "clause": {
                        "type": "string",
                        "description": "相关条款内容（用于 add 操作）",
                    },
                    "problem": {
                        "type": "string",
                        "description": "问题描述（用于 add/update 操作）",
                    },
                    "severity": {
                        "type": "string",
                        "description": "严重程度：high/medium/low（用于 add/update 操作）",
                        "enum": ["high", "medium", "low"],
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "修改建议（用于 add/update 操作）",
                    },
                    "feedback": {
                        "type": "string",
                        "description": "用户反馈（用于 reject 操作）",
                    },
                },
                "required": ["operation"],
            },
        )
    
    def execute(
        self,
        operation: str,
        issue_id: Optional[str] = None,
        clause: Optional[str] = None,
        problem: Optional[str] = None,
        severity: Optional[str] = None,
        suggestion: Optional[str] = None,
        feedback: Optional[str] = None,
    ) -> str:
        """执行问题点管理操作"""
        
        if operation == "get_current_section":
            return self._get_current_section()
        
        elif operation == "next_section":
            return self._next_section()
        
        elif operation == "prev_section":
            return self._prev_section()
        
        elif operation == "add":
            return self._add_issue(clause, problem, severity, suggestion)
        
        elif operation == "update":
            return self._update_issue(issue_id, problem, severity, suggestion)
        
        elif operation == "delete":
            return self._delete_issue(issue_id)
        
        elif operation == "list":
            return self._list_issues()
        
        elif operation == "confirm":
            return self._confirm_issue(issue_id)
        
        elif operation == "reject":
            return self._reject_issue(issue_id, feedback)
        
        elif operation == "export":
            return self._export_report()
        
        else:
            return f"错误：未知操作 '{operation}'"
    
    def _get_current_section(self) -> str:
        """获取当前章节"""
        section = self._state.current_section
        if not section:
            return "当前没有加载合同，请先通过「审核合同 <文件路径>」加载合同。"
        
        issues = self._state.get_current_section_issues()
        
        return json.dumps({
            "section_index": section.index,
            "section_title": section.title,
            "section_content": section.content,
            "total_sections": self._state.total_sections,
            "current_issues_count": len(issues),
            "issues": [i.to_dict() for i in issues],
        }, ensure_ascii=False, indent=2)
    
    def _next_section(self) -> str:
        """切换到下一章节"""
        section = self._state.next_section()
        if not section:
            return "已经是最后一个章节了。"
        
        return f"已切换到章节 {section.index + 1}/{self._state.total_sections}：{section.title}"
    
    def _prev_section(self) -> str:
        """切换到上一章节"""
        section = self._state.prev_section()
        if not section:
            return "已经是第一个章节了。"
        
        return f"已切换到章节 {section.index + 1}/{self._state.total_sections}：{section.title}"
    
    def _add_issue(
        self,
        clause: Optional[str],
        problem: Optional[str],
        severity: Optional[str],
        suggestion: Optional[str],
    ) -> str:
        """添加问题点"""
        if not all([clause, problem, severity, suggestion]):
            return "错误：添加问题点需要提供 clause、problem、severity、suggestion 参数"
        
        try:
            sev = Severity(severity)
        except ValueError:
            return f"错误：无效的严重程度 '{severity}'，应为 high/medium/low"
        
        issue = self._state.add_issue(
            clause=clause,
            problem=problem,
            severity=sev,
            suggestion=suggestion,
        )
        
        return f"已添加问题点 [{issue.id}]：{problem}"
    
    def _update_issue(
        self,
        issue_id: Optional[str],
        problem: Optional[str],
        severity: Optional[str],
        suggestion: Optional[str],
    ) -> str:
        """更新问题点"""
        if not issue_id:
            return "错误：更新问题点需要提供 issue_id 参数"
        
        kwargs = {}
        if problem:
            kwargs["problem"] = problem
        if severity:
            kwargs["severity"] = severity
        if suggestion:
            kwargs["suggestion"] = suggestion
        
        issue = self._state.update_issue(issue_id, **kwargs)
        if not issue:
            return f"错误：未找到问题点 '{issue_id}'"
        
        return f"已更新问题点 [{issue_id}]"
    
    def _delete_issue(self, issue_id: Optional[str]) -> str:
        """删除问题点"""
        if not issue_id:
            return "错误：删除问题点需要提供 issue_id 参数"
        
        if self._state.delete_issue(issue_id):
            return f"已删除问题点 [{issue_id}]"
        return f"错误：未找到问题点 '{issue_id}'"
    
    def _list_issues(self) -> str:
        """列出所有问题点"""
        issues = self._state.issues
        if not issues:
            return "当前没有问题点。"
        
        severity_counts = self._state.count_issues_by_severity()
        
        result = {
            "total": len(issues),
            "by_severity": severity_counts,
            "issues": [i.to_dict() for i in issues],
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _confirm_issue(self, issue_id: Optional[str]) -> str:
        """确认问题点"""
        if not issue_id:
            return "错误：确认问题点需要提供 issue_id 参数"
        
        issue = self._state.confirm_issue(issue_id)
        if not issue:
            return f"错误：未找到问题点 '{issue_id}'"
        
        return f"已确认问题点 [{issue_id}]"
    
    def _reject_issue(self, issue_id: Optional[str], feedback: Optional[str]) -> str:
        """拒绝问题点"""
        if not issue_id:
            return "错误：拒绝问题点需要提供 issue_id 参数"
        
        issue = self._state.reject_issue(issue_id, feedback)
        if not issue:
            return f"错误：未找到问题点 '{issue_id}'"
        
        return f"已拒绝问题点 [{issue_id}]"
    
    def _export_report(self) -> str:
        """导出审核报告"""
        return self._state.export_report()


class RagQueryTool(BaseTool):
    """
    RAG 知识库查询工具
    
    使用 LlamaCloud API 查询法律知识库。
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        index_id: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("LLAMACLOUD_API_KEY")
        self._index_id = index_id or os.getenv("LLAMACLOUD_INDEX_ID")
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="rag_query",
            description="查询法律知识库，获取相关法律条文和判例。用于辅助合同条款分析。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询内容，例如：'关于违约金上限的规定'",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量，默认 3",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        )
    
    def execute(self, query: str, top_k: int = 1) -> str:
        """执行知识库查询"""
        if not self._api_key or not self._index_id:
            return "错误：未配置 LLAMACLOUD_API_KEY 或 LLAMACLOUD_INDEX_ID"
        
        try:
            import requests
            
            response = requests.post(
                f"https://api.cloud.llamaindex.ai/api/v1/pipelines/{self._index_id}/retrieve",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "top_k": top_k,
                },
                timeout=30,
            )
            
            if response.status_code != 200:
                return f"错误：知识库查询失败 (HTTP {response.status_code})"
            
            data = response.json()
            results = data.get("retrieval_nodes", [])
            
            if not results:
                return f"未找到与 '{query}' 相关的知识"
            
            output = [f"【知识库查询结果】查询：{query}\n"]
            
            for i, node in enumerate(results, 1):
                text = node.get("text", node.get("node", {}).get("text", ""))
                score = node.get("score", 0)
                output.append(f"\n--- 结果 {i} (相关度: {score:.2f}) ---")
                output.append(text)
            
            return "\n".join(output)
            
        except ImportError:
            return "错误：未安装 requests 库"
        except Exception as e:
            return f"错误：知识库查询异常 - {e}"


def create_contract_tools(state: ReviewState) -> ToolRegistry:
    """
    创建合同审核工具注册表

    Args:
        state: 审核状态对象

    Returns:
        包含所有合同审核工具的 ToolRegistry
    """
    registry = ToolRegistry()
    registry.register(ManageIssuesTool(state))
    registry.register(RagQueryTool())
    return registry
