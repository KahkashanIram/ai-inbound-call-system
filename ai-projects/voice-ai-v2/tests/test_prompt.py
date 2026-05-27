from app.services.agent_handler import load_prompt

if __name__ == "__main__":
    result = load_prompt("general_response.txt")
    print("\n✅ PROMPT LOADED:\n")
    print(result[:200])  # print first 200 chars