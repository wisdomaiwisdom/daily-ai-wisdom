import json
import re
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


def search_real_story(topic: str) -> str:
    """
    Search for real names, quotes, statistics, and stories
    to anchor the post in reality.
    """
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "Search unavailable. Use your training knowledge of real stories and quotes."

    queries = [
        f'famous quote "{topic}" success failure lesson',
        f'real story {topic} CEO founder lesson learned statistics',
    ]

    all_results = []
    for query in queries[:2]:
        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key
                },
                params={"q": query, "count": 4},
                timeout=10
            )
            data = response.json()
            results = data.get("web", {}).get("results", [])
            for r in results[:2]:
                all_results.append(
                    f"- {r.get('title', '')}: {r.get('description', '')[:200]}"
                )
        except Exception:
            pass

    if not all_results:
        return (
            "No search results. Use your training knowledge: "
            "real names (Jobs, Bezos, Edison, Musk, Blakely), "
            "real stories (Kodak, Blockbuster, Netflix), "
            "real quotes and statistics you know to be true."
        )

    return (
        "REAL ANCHORS FOUND — use one of these in the post:\n\n" +
        "\n".join(all_results) +
        "\n\nExtract: a real name, quote, statistic, or story. "
        "Build the post around it. Do not invent facts."
    )


def get_todays_topic() -> str:
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            topics = json.load(f)
        for topic in topics:
            if not topic.get("used", False):
                topic["used"] = True
                topic["used_date"] = datetime.now().strftime("%Y-%m-%d")
                with open(TOPICS_FILE, "w", encoding="utf-8") as f:
                    json.dump(topics, f, indent=2)
                return json.dumps({
                    "topic":    topic["topic"],
                    "category": topic["category"],
                    "id":       topic["id"]
                })
        for topic in topics:
            topic["used"] = False
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(topics, f, indent=2)
        return json.dumps({
            "topic":    topics[0]["topic"],
            "category": topics[0]["category"],
            "note":     "Topics cycled — starting fresh"
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


def _fallback_hashtags(category: str) -> str:
    defaults = {
        "harsh":        "#DailyAIWisdom #Leadership #GrowthMindset",
        "motivational": "#DailyAIWisdom #Leadership #Motivation",
        "ai_tip":       "#DailyAIWisdom #AIProductivity #FutureOfWork",
        "comedy":       "#DailyAIWisdom #Leadership #WorkLife",
    }
    tags = defaults.get(category, "#DailyAIWisdom #Leadership #AI")
    return f"USE THESE HASHTAGS: {tags}\nUse all 3 exactly as shown."


def get_trending_hashtags(topic: str, category: str = "motivational") -> str:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return _fallback_hashtags(category)
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key
            },
            params={
                "q": f"trending LinkedIn hashtags {topic} 2026",
                "count": 5
            },
            timeout=10
        )
        data = response.json()
        results = data.get("web", {}).get("results", [])

        found_tags = []
        for r in results[:3]:
            text = r.get("title", "") + " " + r.get("description", "")
            tags = re.findall(r'#[A-Za-z][A-Za-z0-9]+', text)
            found_tags.extend(tags)

        seen = set()
        unique_tags = []
        for tag in found_tags:
            tag_lower = tag.lower()
            if tag_lower not in seen and tag_lower != "#dailyaiwisdom":
                seen.add(tag_lower)
                unique_tags.append(tag)

        if len(unique_tags) >= 2:
            top_two = unique_tags[:2]
            return (
                f"USE THESE HASHTAGS: #DailyAIWisdom {top_two[0]} {top_two[1]}\n"
                f"These are trending for this topic. Use all 3 exactly as shown."
            )
        else:
            return _fallback_hashtags(category)

    except Exception:
        return _fallback_hashtags(category)


def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "search_web":
        return search_web(tool_input.get("query", ""))
    if tool_name == "get_todays_topic":
        return get_todays_topic()
    if tool_name == "check_recent_posts":
        return check_recent_posts(tool_input.get("days", 14))
    if tool_name == "get_trending_hashtags":
        return get_trending_hashtags(
            tool_input.get("topic", ""),
            tool_input.get("category", "motivational")
        )
    if tool_name == "search_real_story":
        return search_real_story(tool_input.get("topic", ""))
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
        "name": "search_real_story",
        "description": (
            "Search for real names, quotes, statistics, and stories about today's topic. "
            "Call this BEFORE writing — posts without real anchors are rejected. "
            "Finds CEO stories, company failures, famous quotes, and real data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Today's topic to find real stories about"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "get_trending_hashtags",
        "description": (
            "Search for trending LinkedIn hashtags for today's topic. "
            "Call this AFTER get_todays_topic. "
            "Returns 2 trending hashtags plus #DailyAIWisdom."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Today's post topic"
                },
                "category": {
                    "type": "string",
                    "description": "Topic category: harsh, motivational, ai_tip, or comedy"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "search_web",
        "description": (
            "Search for additional real-world examples and data points. "
            "Use after search_real_story if you need more specific information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A focused search query."
                }
            },
            "required": ["query"]
        }
    }
]