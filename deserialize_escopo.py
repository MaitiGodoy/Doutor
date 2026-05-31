import json
import os

input_file = r"C:\Users\User\Downloads\Escopo Doutor.json"
output_file = r"C:\Users\User\.gemini\antigravity-ide\scratch\doutor\escopo_doutor_deserialized.md"

if not os.path.exists(input_file):
    print(f"Error: {input_file} not found")
    exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# The structure seems to be a list of chat objects
# Each chat object has 'title' and 'chat' which has 'history' which has 'messages'
markdown_content = []

for idx, chat_item in enumerate(data):
    title = chat_item.get("title", f"Chat {idx}")
    markdown_content.append(f"# Chat Thread: {title}\n")
    
    chat_data = chat_item.get("chat", {})
    history = chat_data.get("history", {})
    messages = history.get("messages", {})
    
    # Sort messages by timestamp if available, else by key
    sorted_messages = []
    for msg_id, msg in messages.items():
        sorted_messages.append(msg)
        
    sorted_messages.sort(key=lambda x: x.get("timestamp", 0))
    
    for msg in sorted_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # Filter out empty assistant responses or those with only thinking if desired,
        # but let's include everything that is relevant.
        if content.strip():
            markdown_content.append(f"### 👤 {role.upper()}:\n{content}\n")
            markdown_content.append("\n---\n")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("\n".join(markdown_content))

print(f"Success! Extracted {len(markdown_content)} sections. Written to {output_file}")
