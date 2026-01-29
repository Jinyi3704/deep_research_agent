import os
import sys

from agent import AgentOrchestrator, ReActAgent, Reflector
from llm import LLMClient
from memory import MemoryManager
from memory.supabase_client import SupabaseClient
from skills import SkillLoader, LLMSkillMatcher
from tools import build_default_tools


def main():
    try:
        llm = LLMClient()
    except ValueError as e:
        print(f"Error: {e}")
        return

    print("AI Deep Research Agent - Starter Kit")
    print("=" * 50)
    print("Type 'quit' or 'exit' to end the conversation")
    print("=" * 50)
    print()

    # debug = os.getenv("REACT_DEBUG", "").lower() in {"1", "true", "yes"}
    # tool_log = os.getenv("TOOL_LOG", "").lower() in {"1", "true", "yes"}
    # show_plan = os.getenv("SHOW_PLAN", "").lower() in {"1", "true", "yes"}
    # stream_enabled = os.getenv("STREAM", "1").lower() in {"1", "true", "yes"}
    # reflect_enabled = os.getenv("REFLECT", "").lower() in {"1", "true", "yes"}
    # reflect_debug = os.getenv("REFLECT_DEBUG", "").lower() in {"1", "true", "yes"}
    debug =1 
    tool_log=1
    show_plan=1
    stream_enabled=1
    reflect_enabled=1
    reflect_debug=1
    # if tool_log:
    #     debug = True

    # 初始化 Supabase 客户端
    supabase_client = None
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_API_KEY")
        supabase_client = SupabaseClient(url=supabase_url, api_key=supabase_key)
        print("✓ Supabase connection initialized", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Warning: Failed to initialize Supabase: {e}", file=sys.stderr)
        print("  Conversations will not be saved to database.", file=sys.stderr)

    # 初始化 MemoryManager with Supabase
    memory = MemoryManager(llm, supabase_client=supabase_client)

    # 加载 skills（使用 LLM 智能匹配）
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")
    skill_loader = SkillLoader(skills_dir)
    skills = skill_loader.load_all()
    skill_matcher = LLMSkillMatcher(llm, skills) if skills else None
    if skills:
        print(f"✓ 已加载 {len(skills)} 个技能: {', '.join(s.name for s in skills)}", file=sys.stderr)

    tools = build_default_tools()
    react_agent = ReActAgent(llm, tools, debug=debug)
    reflector = Reflector(llm, debug=reflect_debug) if reflect_enabled else None
    orchestrator = AgentOrchestrator(
        llm,
        tools,
        memory=memory,
        react_agent=react_agent,
        reflector=reflector,
        skill_matcher=skill_matcher,
    )

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break

        try:
            tool_log_output = None
            skill_log_output = None
            if debug:
                tool_log_output = lambda text: print(text, file=sys.stderr, flush=True)
                skill_log_output = lambda text: print(text, file=sys.stderr, flush=True)
            reflection_log_output = None
            if reflect_debug:
                reflection_log_output = (
                    lambda text: print(text, file=sys.stderr, flush=True)
                )

            plan_streamed = False
            if stream_enabled:
                if show_plan:
                    plan_streamed = True
                    print("\nPlan: ", end="", flush=True)
                    plan_stream_output = lambda text: print(text, end="", flush=True)

                    def plan_done(_):
                        print("\n\nAssistant: ", end="", flush=True)

                else:
                    plan_stream_output = None
                    plan_done = None
                    print("\nAssistant: ", end="", flush=True)

                reflection_stream_output = None
                if reflect_enabled:
                    started = False

                    def reflection_stream_output(text):
                        nonlocal started
                        if not started:
                            print("\nRevised: ", end="", flush=True)
                            started = True
                        print(text, end="", flush=True)

                assistant_message = orchestrator.run(
                    user_input,
                    stream_output=lambda text: print(text, end="", flush=True),
                    plan_stream_output=plan_stream_output if show_plan else None,
                    plan_done=plan_done if show_plan else None,
                    tool_log_output=tool_log_output,
                    reflection_log_output=reflection_log_output,
                    reflection_stream_output=reflection_stream_output,
                    skill_log_output=skill_log_output,
                )
                print()
            else:
                print("\nAssistant: ", end="", flush=True)
                assistant_message = orchestrator.run(
                    user_input,
                    tool_log_output=tool_log_output,
                    reflection_log_output=reflection_log_output,
                    skill_log_output=skill_log_output,
                )
                print(assistant_message)

            if show_plan and orchestrator.last_plan and not plan_streamed:
                print("\nPlan:\n" + orchestrator.last_plan)

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
