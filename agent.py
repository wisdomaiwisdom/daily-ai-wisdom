import anthropic
import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv

from system_prompt import SYSTEM_PROMPT
from tools import TOOLS, execute_tool
from image_generator import generate_card

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
POSTS_LOG = "posts_log.json"


def clean_preamble(text: str) -> str:
    """Remove any AI preamble before the actual post starts."""
    lines = text.strip().split("\n")

    preamble_signals = [
        "now i'll", "here is", "here's", "perfect", "based on",
        "let me", "following the", "i'll write", "the post:",
        "writing the", "below is", "formula:", "insights:",
        "based on the", "i will", "here's your", "here is your"
    ]

    start_index = 0
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        is_preamble = any(signal in line_lower for signal in preamble_signals)
        is_separator = line.strip() in ["---", "___", "==="]

        if is_preamble or (is_separator and i < 3):
            start_index = i + 1
        else:
            break

    clean = "\n".join(lines[start_index:]).strip()
    return clean if clean else text.strip()


def run_agent() -> str:
    """Run the agent loop — research, write, return post text."""
    print("\n Daily AI Wisdom agent starting...")
    print(f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("-" * 50)

    messages = [
        {
            "role": "user",
            "content": (
                "Write today's Daily AI Wisdom LinkedIn post. "
                "Steps:\n"
                "1. Call get_todays_topic to get today's topic.\n"
                "2. Call check_recent_posts to avoid repetition.\n"
                "3. Call search_web with a focused query for a real example.\n"
                "4. Write the post following the formula exactly.\n\n"
                "IMPORTANT: Output ONLY the post. "
                "Start directly with the hook. "
                "No introduction. No explanation. No preamble."
            )
        }
    ]

    step = 0
    while True:
        step += 1
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        print(f"  Step {step}: {response.stop_reason}", end="")

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    post_text = clean_preamble(block.text.strip())
                    print(f" -> Post ready ({len(post_text)} chars)")
                    return post_text
            return "Error: no text generated"

        if response.stop_reason == "tool_use":
            tool_results = []
            tools_called = []

            for block in response.content:
                if block.type == "tool_use":
                    tools_called.append(block.name)
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            print(f" -> Tools: {', '.join(tools_called)}")
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})


def save_post(post_text: str):
    """Save the post to the log file."""
    try:
        with open(POSTS_LOG, "r") as f:
            posts = json.load(f)
    except FileNotFoundError:
        posts = []

    posts.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "topic": post_text[:60],
        "text": post_text,
        "chars": len(post_text),
        "status": "pending"
    })

    with open(POSTS_LOG, "w") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f" Post saved to {POSTS_LOG}")


def send_email(post_text: str, image_path: str = None):
    """Send the post to email for review."""
    email_user     = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_to       = os.getenv("EMAIL_TO")

    if not all([email_user, email_password, email_to]):
        print(" Email not configured — skipping")
        return

    date_str = datetime.now().strftime("%B %d, %Y")

    body = (
        f"Daily AI Wisdom — {date_str}\n\n"
        f"{'─' * 50}\n\n"
        f"{post_text}\n\n"
        f"{'─' * 50}\n\n"
        f"Characters: {len(post_text)}/1100\n\n"
        f"Image saved at: {image_path}\n\n"
        f"Steps:\n"
        f"1. Copy the post text above\n"
        f"2. Open LinkedIn\n"
        f"3. Paste and attach the image\n"
        f"4. Post!\n"
    )

    msg = MIMEText(body, "plain")
    msg["Subject"] = (
        f"Daily AI Wisdom — Post Ready "
        f"[{datetime.now().strftime('%b %d')}]"
    )
    msg["From"] = email_user
    msg["To"]   = email_to

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_password)
            server.send_message(msg)
        print(f" Post emailed to {email_to}")
    except Exception as e:
        print(f" Email error: {e}")


if __name__ == "__main__":

    # 1. Generate the post
    post_text = run_agent()

    # 2. Print to terminal
    print("\n" + "=" * 60)
    print("DAILY AI WISDOM — TODAY'S POST")
    print("=" * 60)
    print(post_text)
    print("=" * 60)
    print(f"Characters: {len(post_text)}/1100")

    # 3. Save to log
    save_post(post_text)

    # 4. Generate image
    image_path = generate_card(post_text)
    print(f" Image ready: {image_path}")

    # 5. Send email
    send_email(post_text, image_path)