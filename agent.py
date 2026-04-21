import anthropic
import json
import os
import smtplib
import requests
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
 
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
POSTS_LOG = "posts_log.json"
 
 
def clean_preamble(text: str) -> str:
    """Remove any AI preamble before the actual post starts."""
    lines = text.strip().split("\n")
 
    preamble_signals = [
        "now i'll", "here is", "here's", "perfect", "based on",
        "let me", "following the", "i'll write", "the post:",
        "writing the", "below is", "formula:", "insights:",
        "based on the", "i will", "here's your", "here is your",
        "i'll proceed", "this is mode", "territory", "wake up call",
        "proceeding with", "using the topic", "recent coverage",
        "mode 1", "mode 2", "mode 3", "signals", "let's write",
        "i'm going to", "for this post", "today's post"
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
        with open(POSTS_LOG, "r", encoding="utf-8", errors="ignore") as f:
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
 
    with open(POSTS_LOG, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
 
    print(f" Post saved to {POSTS_LOG}")
 
 
def send_email(post_text: str, image_path: str = None):
    """Send the post and image to email for review."""
    email_user     = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_to       = os.getenv("EMAIL_TO")
 
    if not all([email_user, email_password, email_to]):
        print(" Email not configured — skipping")
        return
 
    date_str = datetime.now().strftime("%B %d, %Y")
 
    msg = MIMEMultipart()
    msg["Subject"] = f"Daily AI Wisdom — Post Ready [{datetime.now().strftime('%b %d')}]"
    msg["From"]    = email_user
    msg["To"]      = email_to
 
    body = (
        f"Daily AI Wisdom — {date_str}\n\n"
        f"{'─' * 50}\n\n"
        f"{post_text}\n\n"
        f"{'─' * 50}\n\n"
        f"Characters: {len(post_text)}/1100\n\n"
        f"The post has been automatically posted to LinkedIn.\n"
        f"Image is attached to this email.\n"
    )
    msg.attach(MIMEText(body, "plain"))
 
    # Normalize path for cross-platform compatibility
    if image_path:
        image_path = os.path.normpath(image_path)
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(image_path)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)
        print(f" Image attached to email")
 
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_password)
            server.send_message(msg)
        print(f" Post emailed to {email_to}")
    except Exception as e:
        print(f" Email error: {e}")
 
 
def post_to_linkedin(post_text: str, image_path: str = None):
    """Post to LinkedIn with optional image."""
    token     = os.getenv("LINKEDIN_TOKEN")
    person_id = os.getenv("LINKEDIN_PERSON_ID")

    if not token or not person_id:
        print(" LinkedIn not configured — skipping")
        return None

    author = f"urn:li:person:{person_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    # Step 1 — Upload image if provided
    media_asset = None
    if image_path and os.path.exists(image_path):
        try:
            # Register the image upload
            register_response = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers=headers,
                json={
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": author,
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }
                        ]
                    }
                }
            )

            if register_response.status_code == 200:
                register_data  = register_response.json()
                upload_url     = register_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                media_asset    = register_data["value"]["asset"]

                # Upload the actual image file
                with open(image_path, "rb") as img_file:
                    upload_response = requests.put(
                        upload_url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "image/png"
                        },
                        data=img_file.read()
                    )

                if upload_response.status_code in [200, 201]:
                    print(f" Image uploaded to LinkedIn")
                else:
                    print(f" Image upload failed: {upload_response.status_code}")
                    media_asset = None
            else:
                print(f" Image register failed: {register_response.status_code}")

        except Exception as e:
            print(f" Image upload error: {e}")
            media_asset = None

    # Step 2 — Create the post
    if media_asset:
        # Post with image
        post_body = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "media": media_asset
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    else:
        # Post text only
        post_body = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=post_body
    )

    if response.status_code == 201:
        post_id = response.json().get("id", "")
        print(f" Posted to LinkedIn! ID: {post_id}")
        return post_id
    else:
        print(f" LinkedIn error: {response.status_code} — {response.text}")
        return None
 
 
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
 
    # 5. Send email with image attached
    send_email(post_text, image_path)
 
    # 6. Post to LinkedIn with image
    post_to_linkedin(post_text, image_path)