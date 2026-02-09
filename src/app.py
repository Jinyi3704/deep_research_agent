"""
App - 应用主流程与 REPL 循环

提供：会话日志 Tee、组件初始化、REPL 主循环及 run_agent/save_and_exit/run_auto_review。
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import List, Optional, Tuple

from config import AppConfig
from core import LLMClient, LoggingHook, RunLogHook, AgentConfig
from core.types import Message
from agents import ContractReviewAgent
from memory import MemoryManager
from memory.supabase_client import SupabaseClient
from report import export_report
from session import save_session_log
from ui import handle_command, print_banner


def setup_session_logging() -> List[dict]:
    """创建会话日志列表（只记录大模型和工具输出，不捕获终端输出）"""
    session_logs: List[dict] = []
    # 不再使用 TeeStream 捕获终端输出
    # RunLogHook 会自动记录大模型和工具输出到 session_logs
    return session_logs


def init_components(
    config: AppConfig,
) -> Tuple[Optional[LLMClient], Optional[MemoryManager], Optional[ContractReviewAgent]]:
    """
    初始化 LLM、记忆、智能体。
    若 LLM 初始化失败返回 (None, None, None)，否则返回 (llm, memory, agent)。
    """
    try:
        llm = LLMClient(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
    except Exception as e:
        print(f"错误：无法初始化 LLM - {e}")
        return None, None, None

    supabase = None
    if config.supabase.enabled:
        try:
            supabase = SupabaseClient(config.supabase.url, config.supabase.api_key)
        except Exception:
            pass

    memory = MemoryManager(llm, supabase_client=supabase)
    agent_config = AgentConfig(
        max_steps=config.agent.max_steps,
        debug=config.agent.debug,
        stream=config.agent.stream,
    )
    agent = ContractReviewAgent(llm, config=agent_config)

    if config.ui.show_tool_log:
        agent.add_hook(
            LoggingHook(
                log_func=lambda msg: print(f"\n{msg}", file=sys.stderr, flush=True),
                verbose=config.agent.debug,
            )
        )

    print("准备就绪！\n")
    return llm, memory, agent


def run_repl(
    config: AppConfig,
    session_logs: List[dict],
    llm: LLMClient,
    memory: MemoryManager,
    agent: ContractReviewAgent,
) -> None:
    """REPL 主循环：读入命令/用户输入，执行命令或调用智能体，处理退出与 Ctrl+C"""
    assert llm is not None and memory is not None and agent is not None

    # 每次运行智能体时，将大模型输出和工具输出写入会话日志
    agent.add_hook(RunLogHook(session_logs))

    def run_agent(user_input: str) -> str:
        context = memory.get_context()
        context_messages = [Message.from_dict(m) for m in context] if context else None
        stream_output = None
        if config.agent.stream:
            print("\nAssistant: ", end="", flush=True)
            stream_output = lambda text: print(text, end="", flush=True)
        result = agent.run(
            user_input,
            context=context_messages,
            stream_output=stream_output,
        )
        memory.add_interaction(user_input, result.content)
        if not config.agent.stream:
            print(f"\nAssistant: {result.content}")
        else:
            print()
        return result.content

    def save_and_exit() -> None:
        if session_logs:
            sys.stdout.flush()
            sys.stderr.flush()
            log_path = save_session_log(session_logs, agent.state.contract_name)
            print(f"\n会话日志已保存到：{log_path}")

    def run_auto_review() -> None:
        total = agent.state.total_sections
        current = agent.state.current_section_index
        print(f"\n开始自动审核，从第 {current + 1} 章到第 {total} 章...")
        print("按 Ctrl+C 可随时中断\n")
        while agent.state.current_section_index < agent.state.total_sections:
            current_idx = agent.state.current_section_index
            current_title = agent.state.current_section.title if agent.state.current_section else "未知"
            print(f"\n{'='*60}")
            print(f"正在审核: [{current_idx + 1}/{total}] {current_title}")
            print(f"{'='*60}")
            run_agent("请审核当前章节，识别所有潜在问题点")
            if agent.state.current_section_index < agent.state.total_sections - 1:
                run_agent("下一章")
            else:
                break
        print(f"\n{'='*60}")
        print("自动审核完成！")
        print(f"共审核 {total} 个章节，发现 {agent.state.total_issues} 个问题点")
        print(f"{'='*60}")
        print("\n输入 'export' 导出审核报告，或 'status' 查看详情")

    while True:
        try:
            if agent.state.contract_name:
                prompt = f"[{agent.state.current_section_index + 1}/{agent.state.total_sections}]> "
            else:
                prompt = "> "
            user_input = input(prompt).strip()
            if not user_input:
                continue
            handled, response, should_exit, auto_review = handle_command(user_input, agent)
            if handled:
                if response:
                    print(response)
                if should_exit:
                    save_and_exit()
                    break
                if auto_review:
                    run_auto_review()
                continue
            run_agent(user_input)
        except KeyboardInterrupt:
            print("\n\n中断...")
            if agent.state.total_issues > 0:
                if input("导出报告？(y/n): ").strip().lower() in ("y", "yes"):
                    filepath = export_report(agent)
                    print(f"\n已导出到：{filepath}")
            save_and_exit()
            print("再见！")
            break
        except Exception as e:
            print(f"\n错误: {e}\n")
            if config.agent.debug:
                import traceback
                traceback.print_exc()
