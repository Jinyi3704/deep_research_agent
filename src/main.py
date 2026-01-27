from llm import LLMClient

def main():
    try:
        llm = LLMClient()
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    messages = []
    
    print("AI Deep Research Agent - Starter Kit")
    print("=" * 50)
    print("Type 'quit' or 'exit' to end the conversation")
    print("=" * 50)
    print()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        try:
            print("\nAssistant: ", end="", flush=True)
            assistant_message = llm.chat(messages, stream=True)
            stream = llm.chat(messages, stream=True)
            assistant_message = ""
            for chunk in stream:
                chunk_content = chunk.choices[0].delta.content
                if chunk_content:
                    assistant_message += chunk_content
                    print(chunk_content, end="", flush=True)
            print()
            messages.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            print(f"\nAssistant: {assistant_message}\n")
            
        except Exception as e:
            print(f"\nError: {e}\n")
            messages.pop()

if __name__ == "__main__":
    main()
