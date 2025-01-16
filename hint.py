import http.client
import json
import argparse
import os
import sqlite3
import platform
from datetime import datetime

#TODO: add base repo where hint is used in db so we can filter on the specific repo to get past conversations for better context

def get_user_data_directory():
    if platform.system() == 'Windows':
        return os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
    elif platform.system() == 'Darwin':  # macOS
        return os.path.expanduser('~/Library/Application Support/hint/')
    else:  # Assume Linux or other Unix-like system
        return os.path.expanduser('~/.local/share/hint/')

# Set the path for the SQLite database
DB_DIR = get_user_data_directory()
assert DB_DIR is not None, "Location for DB_DIR not set correctly"
DB_FILE = os.path.join(DB_DIR, 'conversations.db')
os.makedirs(DB_DIR, exist_ok=True)

COLORS = {
    'blue'   : '\033[94m',
    'red'    : '\033[91m',
    'green'  : '\033[92m',
    'yellow' : '\033[93m',
    'magenta': '\033[95m',
    'cyan'   : '\033[96m',
    'white'  : '\033[97m' 
}

# Set your OpenAI API key
API_KEY = os.getenv("OPENAI_API_KEY")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def load_conversations():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT role, content, metadata, timestamp FROM conversations ORDER BY id DESC LIMIT 10')
    conversations = [{"role": row[0], "content": row[1], "metadata": json.loads(row[2]) if row[2] else {}, "timestamp": row[3]}
                     for row in c.fetchall()]
    conn.close()
    return conversations

def save_conversation(conversation):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    metadata_json = json.dumps(conversation['metadata'])
    c.execute('INSERT INTO conversations (role, content, metadata, timestamp) VALUES (?, ?, ?, ?)',
              (conversation['role'], conversation['content'], metadata_json, conversation['timestamp']))
    conn.commit()
    conn.close()

def color_response(content):
    # Split the content to extract and colorize Python code blocks
    res = []
    parts = content.split("```")
    for i, part in enumerate(parts):
        if i % 2 != 0:
            code = part[part.find("\n"):]
            res.append(colored(code, "white"))
        else:
            res.append(colored(part, "blue"))
    return "".join(res)

def get_response(prompt, past_conversations):
    conn = http.client.HTTPSConnection("api.openai.com")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}',
    }
    messages = past_conversations[::-1][:10] + [
        {"role": 'system', "content": 'You are HINT (Higher INTelligence) the most intelligent computer in the world. God given you the ability to remember the 10 last prompts. You go straight to the answer'},
        {"role": 'user', "content": prompt},
    ]
    data = json.dumps({
        "model": "gpt-4o",
        "temperature": 0.7,
        "messages": messages
    })
    conn.request("POST", "/v1/chat/completions", data, headers)
    response = conn.getresponse()
    response_data = response.read()
    conn.close()
    json_response = json.loads(response_data)
    content = json_response['choices'][0]['message']['content'].strip()
    return color_response(content)

def create_log_entry(role, content, metadata={}):
    return {
        "role": role,
        "content": content,
        "metadata": metadata,
        "timestamp": datetime.now().isoformat(),
    }

def colored(text, color):
    RESET = '\033[0m'
    return f"{COLORS[color]}{text}{RESET}"

def rainbow(text):
    colors = list(COLORS.keys())
    return "".join(colored(letter, colors[i % len(colors)]) for i,letter in enumerate(text))

def read_multiline_input():
    print(colored("you", "magenta") + ": ", end="", flush=True)
    lines = []
    while True:
        try:
            line = input()
            if line.endswith("wq"):
                lines.append(line[:-2].strip())
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines)

def main():
    init_db()

    parser = argparse.ArgumentParser(description='Send prompts to ChatGPT')
    parser.add_argument('-s', action='store_true', help='Start a session for interactive prompts')
    parser.add_argument('-f', help='Put file in prompt')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='Arguments in hint format')

    args = parser.parse_args()
    hintstr = colored("H","red")+colored("INT","green")

    if args.s:
        print("Starting session mode. Type your prompt, end it with 'wq' and press 'enter'. Type 'exit' to end the session.")
        while True:
            prompt = read_multiline_input()
            if prompt.lower() == 'exit':
                print("Ending session.")
                break
            save_conversation(create_log_entry("user", prompt))
            past_conversations = load_conversations()
            response = get_response(prompt, past_conversations)
            print(hintstr + ": " + response)
            save_conversation(create_log_entry("system", response))
    else:
        prompt = ' '.join(args.args)

        file_content = ''
        if args.f:
            try:
                with open(args.f, 'r') as f:
                    file_content += f.read() + '\n'
            except (ValueError, IndexError):
                print("Error processing file argument.")
                return

        full_prompt = file_content + prompt
        past_conversations = load_conversations()
        save_conversation(create_log_entry("user", full_prompt))
        response = get_response(full_prompt, past_conversations)
        print(hintstr + ": " + colored(response, "blue"))
        save_conversation(create_log_entry("system", response))

if __name__ == '__main__':
    main()

