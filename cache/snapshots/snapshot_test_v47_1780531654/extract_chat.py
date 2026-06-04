import json
import os

transcript_path = r"C:\Users\User\.gemini\antigravity-ide\brain\b8dbe8d5-9048-484b-a1dd-2751c6872ef7\.system_generated\logs\transcript.jsonl"
output_path = r"C:\Users\User\.gemini\antigravity-ide\scratch\doutor\last_conversation_summary.md"

if not os.path.exists(transcript_path):
    print(f"Error: {transcript_path} does not exist")
    exit(1)

messages = []
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line.strip())
            source = data.get("source")
            step_type = data.get("type")
            content = data.get("content", "")
            
            if step_type == "USER_INPUT":
                messages.append(f"### 👤 USER:\n{content}\n")
            elif step_type == "PLANNER_RESPONSE":
                # Check if it has tool calls or text
                tool_calls = data.get("tool_calls", [])
                if tool_calls:
                    calls_str = ", ".join([call.get("name", "") for call in tool_calls])
                    messages.append(f"🤖 **Model called tools**: {calls_str}\n")
                if content:
                    messages.append(f"### 🤖 Antigravity:\n{content}\n")
        except Exception as e:
            pass

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("# Histórico da Conversa Anterior\n\n")
    f.write("\n---\n".join(messages))

print("Done! Summary written to last_conversation_summary.md")
