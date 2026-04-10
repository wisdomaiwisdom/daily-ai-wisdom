import json
import requests
import os
from datetime import datetime

TOPICS_FILE = "topics.json"
POSTS_LOG   = "posts_log.json"


def search_web(query: str) -> str:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "Web search unavailable — no API key. Use your training knowledge."
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key
            },
            params={"q": query, "count": 5},
            timeout=10
        )
        data = response.json()
        results = data.get("web", {}).get("results", [])
        if not results:
            return "No results found."
        output = []
        for r in results[:3]:
            output.append(f"- {r.get('title','')}: {r.get('description','')[:150]}")
        return "\n".join(output)
    except Exception as e:
        return f"Search failed: {str(e)}"


def get_todays_topic() -> str:
    try:
        with open(TOPICS_FILE, "r") as f:
            topics = json.load(f)
        for topic in topics:
            if not topic["used"]:
                topic["used"] = True
                topic["used_date"] = datetime.now().strftime("%Y-%m-%d")
                with open(TOPICS_FILE, "w") as f:
                    json.dump(topics, f, indent=2)
                return json.dumps({
                    "topic": topic["topic"],
                    "category": topic["category"],
                    "id": topic["id"]
                })
        # All used — reset
        for topic in topics:
            topic["used"] = False
        with open(TOPICS_FILE, "w") as f:
            json.dump(topics, f, indent=2)
        return json.dumps({
            "topic": topics[0]["topic"],
            "category": topics[0]["category"],
            "note": "Topics cycled — starting fresh"
        })
    except FileNotFoundError:
        return json.dumps({"error": "topics.json not found"})


def check_recent_posts(days: int = 14) -> str:
    try:
        with open(POSTS_LOG, "r", encoding="utf-8", errors="ignore") as f:
            posts = json.load(f)
        recent = [p.get("topic", p.get("text", "")[:50]) for p in posts[-days:]]
        if not recent:
            return "No recent posts — this is the first post."
        return "Recent topics covered:\n" + "\n".join(f"- {t}" for t in recent)
    except FileNotFoundError:
        return "No post history yet — this is the first post."


def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "search_web":
        return search_web(tool_input.get("query", ""))
    if tool_name == "get_todays_topic":
        return get_todays_topic()
    if tool_name == "check_recent_posts":
        return check_recent_posts(tool_input.get("days", 14))
    return f"Unknown tool: {tool_name}"


TOOLS = [
    {
        "name": "get_todays_topic",
        "description": "Get today's topic from the topic bank. Call this first.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "check_recent_posts",
        "description": "Check what topics were recently covered to avoid repetition.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "How many recent posts to check. Default 14."
                }
            }
        }
    },
    {
        "name": "search_web",
        "description": "Search for real-world examples and data to make the post feel current and grounded.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A focused search query to find relevant examples."
                }
            },
            "required": ["query"]
        }
    }
]