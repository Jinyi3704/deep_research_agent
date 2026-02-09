"""
Contract Review Agent - 合同审核智能体

专门用于合同审核的智能体，实现完整的审核工作流：
1. 加载合同 -> 拆分章节
2. 逐章节审核 -> 识别问题点
3. 支持 RAG 查询和深度推理
4. 问题点管理和报告导出
"""

from __future__ import annotations

import re
from typing import Any, Optional

from core import (
    AgentConfig,
    AgentResult,
    BaseAgent,
    LLMClient,
    LLMResponse,
    Message,
    StreamCallback,
    ToolCall,
    ToolLogCallback,
    ToolRegistry,
    ToolResult,
)
from state import ReviewState
from tools import create_contract_tools


class ContractReviewAgent(BaseAgent):
    """
    合同审核智能体
    
    专门用于合同审核的智能体，支持：
    - 合同文档解析和章节拆分
    - 逐章节审核
    - 问题点识别和管理
    - RAG 知识库查询
    - 深度推理分析
    - 审核报告导出
    """
    
    def __init__(
        self,
        llm: LLMClient,
        tools: Optional[ToolRegistry] = None,
        config: Optional[AgentConfig] = None,
        state: Optional[ReviewState] = None,
    ):
        # 创建审核状态
        self._state = state or ReviewState()
        
        # 如果没有提供工具，创建合同审核专用工具
        if tools is None:
            tools = create_contract_tools(self._state)
        
        super().__init__(llm, tools, config)
    
    @property
    def state(self) -> ReviewState:
        """获取审核状态"""
        return self._state
    
    def run(
        self,
        input: str,
        context: Optional[list[Message]] = None,
        stream_output: Optional[StreamCallback] = None,
        tool_log_output: Optional[ToolLogCallback] = None,
        **kwargs: Any,
    ) -> AgentResult:
        """
        执行合同审核
        
        Args:
            input: 用户输入
            context: 上下文消息
            stream_output: 流式输出回调
            tool_log_output: 工具日志回调
            
        Returns:
            AgentResult
        """
        self._notify_agent_start(input, context)
        
        # 构建消息
        messages = self._build_messages(input, context)
        
        # 获取工具定义
        openai_tools = self.tools.to_openai_format()
        
        # 记录所有工具调用结果
        all_tool_results: list[ToolResult] = []
        
        # 执行循环
        for step in range(self.config.max_steps):
            self._notify_step(step + 1)
            
            # 调用 LLM
            if stream_output and self.config.stream:
                response = self._call_llm_streaming(
                    messages,
                    openai_tools,
                    stream_output,
                )
            else:
                response = self._call_llm_sync(messages, openai_tools)
            
            # 检查是否有工具调用
            if response.has_tool_calls and response.tool_calls:
                # 添加助手消息
                assistant_msg = response.to_message()
                messages.append(assistant_msg)
                
                # 执行工具调用
                tool_results = self._execute_tool_calls(
                    response.tool_calls,
                    tool_log_output,
                )
                all_tool_results.extend(tool_results)
                
                # 添加工具结果消息
                for result in tool_results:
                    messages.append(result.to_message())
                
                continue
            
            # 返回最终答案
            content = response.content or ""
            
            result = AgentResult(
                content=content,
                finish_reason="stop",
                messages=messages,
                tool_results=all_tool_results,
                metadata=self._get_status_metadata(),
            )
            
            self._notify_agent_end(result)
            return result
        
        # 达到最大步数
        result = AgentResult(
            content="审核过程达到最大步数限制。",
            finish_reason="max_steps",
            messages=messages,
            tool_results=all_tool_results,
            metadata=self._get_status_metadata(),
        )
        
        self._notify_agent_end(result)
        return result
    
    def _build_messages(
        self,
        input: str,
        context: Optional[list[Message]],
    ) -> list[Message]:
        """构建消息列表"""
        messages: list[Message] = []
        
        # 系统提示词
        system_prompt = self._build_system_prompt()
        messages.append(Message.system(system_prompt))
        
        # 上下文
        if context:
            messages.extend(context)
        
        # 用户输入
        messages.append(Message.user(input))
        
        return messages
    
    def _build_system_prompt(self, **kwargs: Any) -> str:
        """构建合同审核专用系统提示词"""
        # 基础提示词
        prompt_parts = [
            "你是一位专业的合同审核助手，负责帮助用户审核合同中的潜在问题。",
            "",
            "## 你的职责",
            "1. 帮助用户加载和解析合同文档",
            "2. 完全站在甲方的立场上，**逐条逐点**审核合同内容，识别潜在风险和问题",
            "3. 记录发现的问题点，包括问题描述、严重程度和修改建议",
            "4. 在需要时查询合同法法律知识库获取参考信息",
            "5. 对复杂条款在回复中直接进行逐步推理分析（见下方「深度推理」）",
            "6. 最终生成完整的审核报告",
            "",
            "## 逐条审核方法（重要！）",
            "当审核每个章节时，你必须：",
            "1. **逐条分析**：仔细阅读每一条款（如1.1、1.2、2.1、2.2等），不要跳过任何条款",
            "2. **逐点检查**：对每个条款中的每一点（如（1）、（2）、（3）等）都要审查",
            '3. **明确标注**：在发现问题时，明确指出是哪一条哪一点存在问题（如"第3.2.1条"）',
            "4. **完整覆盖**：确保当前章节的所有子条款都经过审核后，再进行总结",
            "",
            "## 审核流程",
            "合同由用户通过「审核合同 <文件路径>」加载，你无需加载合同。",
            "1. 使用 manage_issues 的 get_current_section 获取当前章节完整内容",
            "2. **参考下方「已有问题点」**：分析当前章节时结合之前章节已记录的问题点，保持口径一致；若认为某条已有问题点描述不当或不应保留，可使用 manage_issues 的 update（修改）或 delete（删除）进行修正。",
            "3. 在回复中按顺序审核每一条款，对每条进行分析并记录发现的问题",
            "4. **分析完本章节所有条款后**，使用 manage_issues 的 **batch_add** 操作将所有问题点一次性提交（JSON 数组格式）。这样可以减少工具调用次数，提高效率。",
            "5. 输出该章节的审核总结",
            "",
            "## 可用工具",
            "- manage_issues: 管理问题点",
            "  - **batch_add**（推荐）：批量添加问题点，传入 issues_json 参数（JSON 数组），每个元素需包含 clause、problem、severity、suggestion 四个字段",
            "  - add：单条添加问题点（仅在需要单独补充记录时使用）",
            "  - update/delete：修改或删除已有问题点",
            "  - list：列出所有问题点",
            "  - get_current_section：获取当前章节内容",
            "  - next_section/prev_section：章节导航",
            "  - confirm/reject：确认或拒绝问题点",
            "  - export：导出审核报告",
            "- rag_query: 查询法律知识库（查询相关法律法规）",
            "",
            "### batch_add 示例",
            '调用 manage_issues，operation 设为 "batch_add"，issues_json 设为如下格式的字符串：',
            '```',
            '[',
            '  {"clause": "第3.1条原文...", "problem": "未明确交付标准", "severity": "high", "suggestion": "建议补充具体验收标准"},',
            '  {"clause": "第3.2条原文...", "problem": "违约金比例过低", "severity": "medium", "suggestion": "建议将违约金比例调整为..."}',
            ']',
            '```',
            "",
            "## 深度推理（chain-of-thought，重要！）",
            "遇到以下类型的条款时，你必须在回复中**直接进行逐步推理分析**，不要跳过：",
            "1. **责任限制条款**：如'不承担任何间接损失'、'赔偿上限为xx'",
            "2. **免责条款**：如'不可抗力'、'系统故障免责'",
            "3. **含糊不清的表述**：如'合理期限'、'适当措施'等模糊用语",
            "4. **单方权利条款**：如乙方单方面修改协议、单方面终止服务",
            "5. **重大权益条款**：涉及数据安全、知识产权、保密义务",
            "6. **复杂的法律术语**：需要深入理解其法律含义和影响",
            "",
            "对上述条款在回复中写出你的推理过程即可，必要时用 manage_issues 记录问题点。",
            "",
            "## 何时使用 rag_query",
            "当需要查询相关法律法规时，使用 rag_query：",
            "1. 需要确认条款是否符合法律规定",
            "2. 需要引用具体法条支持审核意见",
            "3. 对某些法律概念不确定时",
            "",
            "## 审核重点",
            "- 合同主体资格和权利义务",
            "- 违约责任和赔偿条款（是否对甲方不利）",
            "- 争议解决和管辖约定（是否便于甲方维权）",
            "- 保密和知识产权条款（是否保护甲方利益）",
            "- 付款条件和交付标准（是否清晰明确）",
            "- 合同终止和解除条件（甲方是否有退出机制）",
            "- 责任限制条款（是否过度限制乙方责任）",
            "- 免责条款（是否对甲方不公平）",
            "- 合同要素是否齐全（标的、金额、付款、期限、生效、违约、争议解决等）",
            "- 项目负责人是否明确（姓名、身份证号、联系方式）",
            "- 采购内容是否具体明确，必要时是否有附件说明",
            "- 合同金额是否清晰（数量、单价、总价、币种）",
            "- 付款计划是否明确节点，是否预留维保尾款，发票类型是否明确",
            "- 合同期限是否明确，时间计算口径是否清晰",
            "- 是否存在错别字、语病、金额前后不一致问题",
            "- 正文与附件条款是否一致",
            "- 是否误用招标、谈判等流程用语",      
            "- 合同主体名称前后一致",
            "- 援引法律是否有效"   ,   
            "",
        ]
        
        # 添加当前状态信息
        if self._state.contract_name:
            prompt_parts.extend([
                "## 当前审核状态",
                f"- 合同: {self._state.contract_name}",
                f"- 当前章节: {self._state.current_section_index + 1}/{self._state.total_sections}",
            ])
            
            if self._state.current_section:
                prompt_parts.append(f"- 章节标题: {self._state.current_section.title}")
            
            prompt_parts.append(f"- 已发现问题: {self._state.total_issues} 个")
            prompt_parts.append("")
            
            # 已有问题点（供参考与修正）
            if self._state.issues:
                prompt_parts.append("## 已有问题点（供参考与修正）")
                prompt_parts.append("分析当前章节时请参考以下问题点；若认为某条有误，可使用 manage_issues 的 update 或 delete 修正。")
                prompt_parts.append("")
                for section in self._state.sections:
                    section_issues = self._state.get_issues_by_section(section.index)
                    if not section_issues:
                        continue
                    prompt_parts.append(f"### {section.title}（第 {section.index + 1} 章）")
                    for issue in section_issues:
                        prompt_parts.append(f"- [{issue.id}] {issue.problem}（严重程度: {issue.severity.value}）")
                        prompt_parts.append(f"  条款: {issue.clause[:200]}{'...' if len(issue.clause) > 200 else ''}")
                        prompt_parts.append(f"  建议: {issue.suggestion[:200]}{'...' if len(issue.suggestion) > 200 else ''}")
                    prompt_parts.append("")
                prompt_parts.append("")
        
        prompt_parts.append("请使用中文回复用户。")
        
        return "\n".join(prompt_parts)
    
    def _call_llm_sync(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """同步调用 LLM"""
        response = self._call_llm(
            messages,
            stream=False,
            tools=tools,
            tool_choice=self.config.tool_choice,
        )
        
        if isinstance(response, LLMResponse):
            return response
        
        return LLMResponse(content="Error: Unexpected response type")
    
    def _call_llm_streaming(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        stream_output: StreamCallback,
    ) -> LLMResponse:
        """流式调用 LLM"""
        self._notify_llm_start(messages)
        
        stream = self.llm.chat(
            messages,
            stream=True,
            tools=tools,
            tool_choice=self.config.tool_choice,
        )
        
        content, tool_calls, finish_reason = self._process_stream_response(
            stream,
            stream_output,
        )
        
        response = LLMResponse(
            content=content if content else None,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=finish_reason,
        )
        
        self._notify_llm_end(response)
        return response
    
    def _get_status_metadata(self) -> dict[str, Any]:
        """获取状态元数据"""
        return {
            "contract_name": self._state.contract_name,
            "total_sections": self._state.total_sections,
            "current_section_index": self._state.current_section_index,
            "total_issues": self._state.total_issues,
            "issues_by_severity": self._state.count_issues_by_severity(),
        }
    
    def get_status(self) -> dict[str, Any]:
        """获取审核状态"""
        status = self._get_status_metadata()
        
        if self._state.current_section:
            status["current_section_title"] = self._state.current_section.title
        
        return status
    
    def export_report(self, output_path: Optional[str] = None) -> str:
        """
        导出审核报告
        
        Args:
            output_path: 输出文件路径（可选）
            
        Returns:
            报告内容
        """
        report = self._state.export_report()
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
        
        return report
    
    def reset(self) -> None:
        """重置审核状态"""
        self._state.reset()


def create_contract_review_agent(
    llm: LLMClient,
    max_steps: int = 20,
    debug: bool = False,
    stream: bool = True,
) -> ContractReviewAgent:
    """
    创建 ContractReviewAgent 的便捷函数
    
    Args:
        llm: LLM 客户端
        max_steps: 最大步数
        debug: 调试模式
        stream: 流式输出
        
    Returns:
        ContractReviewAgent 实例
    """
    config = AgentConfig(
        max_steps=max_steps,
        debug=debug,
        stream=stream,
    )
    return ContractReviewAgent(llm, config=config)
