"""
AI 合同审核智能体 - 主入口

主线逻辑：配置 → 会话日志(tee) → 横幅 → 初始化(LLM/记忆/智能体) → REPL 主循环
"""

from app import (
    init_components,
    run_repl,
    setup_session_logging,
)
from config import get_config
from ui import print_banner


def main() -> None:
    """主函数：体现程序主线逻辑"""
    config = get_config()
    if errors := config.validate():
        print("配置错误：" + "\n".join(f"  - {e}" for e in errors))
        return

    session_logs = setup_session_logging()
    print_banner()

    llm, memory, agent = init_components(config)
    if llm is None:
        return

    run_repl(config=config, session_logs=session_logs, llm=llm, memory=memory, agent=agent)


if __name__ == "__main__":
    main()
