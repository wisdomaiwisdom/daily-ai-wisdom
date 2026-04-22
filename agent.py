import anthropic
import json
import os
import smtplib
import requests
import random
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

from system_prompt import SYSTEM_PROMPT
from tools import TOOLS, execute_tool
from image_generator import generate_card

load_dotenv()

client    = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
POSTS_LOG = "posts_log.json"

BANNED_NAMES = [
    "einstein", "musk", "elon", "jobs", "steve jobs", "edison",
    "bezos", "jeff", "blakely", "sara", "buffett", "warren",
    "gates", "bill gates", "zuckerberg", "mark zuckerberg",
    "oprah", "winfrey", "schultz", "howard schultz",
    "knight", "phil knight", "feynman", "aristotle",
    "napoleon", "churchill", "gandhi", "tesla", "nikola",
    "newton", "darwin", "freud", "jung",
    "kodak", "nokia", "polaroid", "blockbuster",
    "netflix", "amazon", "apple", "google",
    "microsoft", "facebook", "twitter", "instagram",
    "mckinsey", "harvard", "mit", "stanford",
]


def has_banned_names(text: str) -> bool:
    text_lower = text.lower()
    return any(name in text_lower for name in BANNED_NAMES)


def emergency_clean(text: str) -> str:
    """Nuclear option — remove every line that isn't actual post content."""
    bad_phrases = [
        "let me", "i'll", "i will", "here's the post", "here is the post",
        "here's the", "here is the", "the post:", "post:",
        "writing", "below is", "now i", "based on",
        "i'm going to", "anchor", "mode 1", "mode 2",
        "step 1", "step 2", "character count", "let me write",
        "i have found", "i'll write", "i will write",
        "here's my", "draft:", "version:", "analysis:", "refined",
        "i'll now", "now let me", "here is my", "post content:",
        "here it is", "here it is:", "the following", "as follows",
        "i've crafted", "i've written", "i've created",
    ]

    lines              = text.strip().split("\n")
    clean_lines        = []
    found_real_content = False

    for line in lines:
        stripped   = line.strip()
        line_lower = stripped.lower()

        # Stop at hashtag block
        if stripped.startswith("#") and "DailyAIWisdom" in stripped:
            clean_lines.append(stripped)
            break

        # Skip blank lines before content starts
        if not stripped and not found_real_content:
            continue

        # Skip separators always
        if all(c in "-=_ :" for c in stripped) and len(stripped) > 0:
            continue

        # Skip any line containing bad phrases — before OR after content starts
        if any(phrase in line_lower for phrase in bad_phrases):
            continue  # skip it regardless of position

        found_real_content = True
        clean_lines.append(stripped)

    result = "\n".join(clean_lines).strip()
    return result if len(result) > 50 else text.strip()

def clean_preamble(text: str) -> str:
    """Strip top preamble then cut at hashtag block."""
    lines = text.strip().split("\n")

    preamble_signals = [
        "now i'll", "here is", "here's", "perfect", "based on",
        "let me", "following the", "i'll write", "the post:",
        "writing the", "below is", "formula:", "insights:",
        "i will", "here's your", "here is your", "i'll proceed",
        "mode 1", "mode 2", "mode 3", "i'm going to",
        "i'll use", "i will use", "training knowledge",
        "anchor this post", "here's the post", "here is the post",
        "let me count", "the post has", "let me refine",
        "final post:", "i'll write the post", "✓",
    ]

    start_index = 0
    for i, line in enumerate(lines):
        line_lower   = line.strip().lower()
        is_preamble  = any(signal in line_lower for signal in preamble_signals)
        is_separator = line.strip() in ["---", "___", "==="]
        if is_preamble or (is_separator and i < 5):
            start_index = i + 1
        else:
            break

    remaining    = "\n".join(lines[start_index:]).strip()
    result_lines = remaining.split("\n")
    final_lines  = []

    for line in result_lines:
        final_lines.append(line)
        stripped = line.strip()
        if stripped.startswith("#") and "DailyAIWisdom" in stripped:
            break

    clean = "\n".join(final_lines).strip()
    return clean if clean else text.strip()


def run_agent() -> str:
    print("\n Daily AI Wisdom agent starting...")
    print(f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("-" * 50)

    messages = [
        {
            "role": "user",
            "content": (
                "Write today's Daily AI Wisdom LinkedIn post.\n"
                "Steps:\n"
                "1. Call get_todays_topic\n"
                "2. Call check_recent_posts\n"
                "3. Call get_trending_hashtags\n"
                "4. Output ONLY the post. Nothing else.\n\n"
                "RULES:\n"
                "- Maximum 700 characters\n"
                "- ZERO names of any person or company — ever\n"
                "- No Einstein, Musk, Jobs, Edison, Bezos, Buffett, Gates\n"
                "- No Kodak, Netflix, Amazon, Apple, Google, Microsoft\n"
                "- Use universal truths, statistics, and observations only\n"
                "- Start with hook — first word = first word of post\n"
                "- End with 3 hashtags — then STOP completely\n"
                "- No preamble, no analysis, no commentary\n\n"
                f"SEED: {random.randint(1, 9999)}"
            )
        }
    ]

    step        = 0
    max_retries = 5

    while True:
        step += 1
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1500,
            temperature=1.0,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        print(f"  Step {step}: {response.stop_reason}", end="")

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    raw       = block.text.strip()
                    post_text = clean_preamble(raw)
                    post_text = emergency_clean(post_text)

                    if has_banned_names(post_text) and step < max_retries * 3:
                        print(f" -> REJECTED (banned name). Retrying...")
                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({
                            "role": "user",
                            "content": (
                                "REJECTED. Your post contained a banned name. "
                                "Rewrite completely with ZERO names of people or companies. "
                                "No person names. No company names. No brand names. "
                                "Only universal truths and anonymous observations. "
                                "Start directly with the hook."
                            )
                        })
                        break

                    print(f" -> Post ready ({len(post_text)} chars)")
                    return post_text
            else:
                return "Error: no text generated"
            continue

        if response.stop_reason == "tool_use":
            tool_results = []
            tools_called = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_called.append(block.name)
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result
                    })
            print(f" -> Tools: {', '.join(tools_called)}")
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})


def save_post(post_text: str):
    try:
        with open(POSTS_LOG, "r", encoding="utf-8", errors="ignore") as f:
            posts = json.load(f)
    except FileNotFoundError:
        posts = []

    posts.append({
        "date":   datetime.now().strftime("%Y-%m-%d"),
        "time":   datetime.now().strftime("%H:%M"),
        "topic":  post_text[:60],
        "text":   post_text,
        "chars":  len(post_text),
        "status": "pending"
    })

    with open(POSTS_LOG, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f" Post saved to {POSTS_LOG}")


def send_email(post_text: str, image_path: str = None):
    email_user     = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_to       = os.getenv("EMAIL_TO")

    if not all([email_user, email_password, email_to]):
        print(" Email not configured — skipping")
        return

    date_str = datetime.now().strftime("%B %d, %Y")
    msg      = MIMEMultipart()
    msg["Subject"] = f"Daily AI Wisdom — Post Ready [{datetime.now().strftime('%b %d')}]"
    msg["From"]    = email_user
    msg["To"]      = email_to

    body = (
        f"Daily AI Wisdom — {date_str}\n\n"
        f"{'─' * 50}\n\n"
        f"{post_text}\n\n"
        f"{'─' * 50}\n\n"
        f"Characters: {len(post_text)}/700\n"
        f"Posted to LinkedIn. Image attached.\n"
    )
    msg.attach(MIMEText(body, "plain"))

    if image_path:
        image_path = os.path.normpath(image_path)
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(image_path)}"
            )
            msg.attach(part)
        print(" Image attached to email")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_password)
            server.send_message(msg)
        print(f" Post emailed to {email_to}")
    except Exception as e:
        print(f" Email error: {e}")


def post_to_linkedin(post_text: str, image_path: str = None):
    token     = os.getenv("LINKEDIN_TOKEN")
    person_id = os.getenv("LINKEDIN_PERSON_ID")

    if not token or not person_id:
        print(" LinkedIn not configured — skipping")
        return None

    author  = f"urn:li:person:{person_id}"
    headers = {
        "Authorization":             f"Bearer {token}",
        "Content-Type":              "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    media_asset = None
    if image_path:
        norm_path = os.path.normpath(image_path)
        if os.path.exists(norm_path):
            try:
                reg = requests.post(
                    "https://api.linkedin.com/v2/assets?action=registerUpload",
                    headers=headers,
                    json={
                        "registerUploadRequest": {
                            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                            "owner":   author,
                            "serviceRelationships": [{
                                "relationshipType": "OWNER",
                                "identifier":       "urn:li:userGeneratedContent"
                            }]
                        }
                    }
                )
                if reg.status_code == 200:
                    upload_url  = reg.json()["value"]["uploadMechanism"][
                        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
                    ]["uploadUrl"]
                    media_asset = reg.json()["value"]["asset"]
                    with open(norm_path, "rb") as img:
                        up = requests.put(
                            upload_url,
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type":  "image/png"
                            },
                            data=img.read()
                        )
                    if up.status_code not in [200, 201]:
                        media_asset = None
                    else:
                        print(" Image uploaded to LinkedIn")
            except Exception as e:
                print(f" Image upload error: {e}")
                media_asset = None

    if media_asset:
        body = {
            "author":          author,
            "lifecycleState":  "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary":    {"text": post_text},
                    "shareMediaCategory": "IMAGE",
                    "media": [{"status": "READY", "media": media_asset}]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
    else:
        body = {
            "author":          author,
            "lifecycleState":  "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary":    {"text": post_text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=body
    )

    if response.status_code == 201:
        post_id = response.json().get("id", "")
        print(f" Posted to LinkedIn! ID: {post_id}")
        return post_id
    else:
        print(f" LinkedIn error: {response.status_code} — {response.text}")
        return None


if __name__ == "__main__":
    post_text = run_agent()

    print("\n" + "=" * 60)
    print("DAILY AI WISDOM — TODAY'S POST")
    print("=" * 60)
    print(post_text)
    print("=" * 60)
    print(f"Characters: {len(post_text)}/700")

    save_post(post_text)
    image_path = generate_card(post_text)
    print(f" Image ready: {image_path}")
    send_email(post_text, image_path)
    post_to_linkedin(post_text, image_path)