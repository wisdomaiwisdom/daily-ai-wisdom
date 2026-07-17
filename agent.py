"""
Daily AI Wisdom - Main agent that generates LinkedIn posts using Claude API.
Includes topic anti-repeat logic and full workflow.
"""

import json
import os
import random
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from tools import TOOLS, process_tool_call, topic_manager

# Load environment variables
load_dotenv()

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Load system prompt
from system_prompt import SYSTEM_PROMPT


def run_agent():
    """Run the Daily AI Wisdom agent."""
    
    print("\n Daily AI Wisdom agent starting...")
    print(f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("-" * 50)
    
    # Initialize messages
    messages = [
        {
            "role": "user",
            "content": "Generate today's Daily AI Wisdom post. Get the topic, write a powerful 3-sentence post under 300 characters with 3 hashtags. Make it real, dark, funny, or motivational. ONLY output the post. Nothing else."
        }
    ]
    
    # Run the agentic loop
    step = 1
    while True:
        # Call Claude with tools
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )
        
        # Check if we're done
        if response.stop_reason == "end_turn":
            # Extract the final post
            for block in response.content:
                if hasattr(block, 'text'):
                    post = block.text.strip()
                    if post and not post.startswith("Tool") and len(post) > 20:
                        return post
            break
        
        # Process tool calls (silently)
        if response.stop_reason == "tool_use":
            tool_results = []
            
            # First add the assistant's response with all tool_use blocks
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Then collect all tool results
            for block in response.content:
                if block.type == "tool_use":
                    result = process_tool_call(block.name, block.input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            # Add all tool results in one message
            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
            
            step += 1
        else:
            # No more tools, extract final response
            for block in response.content:
                if hasattr(block, 'text'):
                    post = block.text.strip()
                    if post and len(post) > 20:
                        return post
            break
    
    return None


def extract_first_sentence(post):
    """Extract the first sentence for the image."""
    lines = post.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not all(c in '-=_ ' for c in line):
            return line
    return "The work is the answer."


def save_post(post):
    """Save post to posts_log.json."""
    try:
        with open('posts_log.json', 'r') as f:
            posts = json.load(f)
    except:
        posts = []
    
    posts.append({
        "date": datetime.now().isoformat(),
        "post": post,
        "characters": len(post)
    })
    
    with open('posts_log.json', 'w') as f:
        json.dump(posts, f, indent=2)


def generate_image(post):
    """Generate image for the post."""
    try:
        from image_generator import generate_card
        
        image_file = generate_card(post)
        return image_file
    except Exception as e:
        print(f" Error generating image: {e}")
        return None


def send_email(post, image_file):
    """Send email with the post."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.image import MIMEImage
        
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        email_to = os.getenv("EMAIL_TO")
        
        if not all([email_user, email_password, email_to]):
            print(" Skipping email: credentials not set")
            return
        
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = email_to
        msg['Subject'] = "Daily AI Wisdom"
        
        msg.attach(MIMEText(post, 'plain'))
        
        if image_file and os.path.exists(image_file):
            with open(image_file, 'rb') as attachment:
                img = MIMEImage(attachment.read())
                img.add_header('Content-ID', '<image>')
                msg.attach(img)
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        
        print(f" Post emailed to {email_to}")
    except Exception as e:
        print(f" Email error: {e}")


def post_to_linkedin(post, image_file):
    """Post to LinkedIn."""
    try:
        # LinkedIn API would go here
        # For now, just acknowledge
        linkedin_token = os.getenv("LINKEDIN_TOKEN")
        if linkedin_token:
            print(" LinkedIn posting would occur here")
        else:
            print(" LinkedIn token not set - skipping")
    except Exception as e:
        print(f" LinkedIn error: {e}")


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("DAILY AI WISDOM — TODAY'S POST")
    print("="*60)
    
    # Generate post
    post = run_agent()
    
    if not post:
        print("Failed to generate post")
        return
    
    # Calculate character count
    char_count = len(post)
    
    # Display post
    print(post)
    print("="*60)
    print(f"Characters: {char_count}/700")
    
    # Save post
    save_post(post)
    print(" Post saved to posts_log.json")
    
    # Generate image
    image_file = generate_image(post)
    if image_file:
        print(f" Image saved: {image_file}")
    
    # Send email
    send_email(post, image_file)
    
    # Post to LinkedIn
    post_to_linkedin(post, image_file)
    
    print()


if __name__ == "__main__":
    main()