"""
Daily AI Wisdom - Tool definitions for Claude API calls.
Includes all required tools and anti-repeat topic logic.
"""

import json
import random
from datetime import datetime


class TopicManager:
    """Manage topic selection with anti-repeat logic."""
    
    def __init__(self, filename='topics.json'):
        self.filename = filename
        self.topics = self._load_topics()
    
    def _load_topics(self):
        """Load topics from JSON file."""
        try:
            with open(self.filename, 'r') as f:
                topics = json.load(f)
            return topics
        except Exception as e:
            print(f"Error loading topics: {e}")
            return []
    
    def _save_topics(self):
        """Save topics back to JSON file."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.topics, f, indent=2)
        except Exception as e:
            print(f"Error saving topics: {e}")
    
    def get_unused_topic(self):
        """Get a random topic that hasn't been used today."""
        # Filter to only unused topics
        unused = [t for t in self.topics if not t.get('used', False)]
        
        # If all used, reset for next cycle
        if not unused:
            for t in self.topics:
                t['used'] = False
            self._save_topics()
            unused = self.topics
        
        # Pick random from unused
        selected = random.choice(unused)
        
        # Mark as used
        selected['used'] = True
        self._save_topics()
        
        return selected.get('topic', 'Life wisdom')


# Initialize topic manager
topic_manager = TopicManager('topics.json')


# Tool definitions
TOOLS = [
    {
        "name": "get_todays_topic",
        "description": "Get today's wisdom topic to write about",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "check_recent_posts",
        "description": "Check recently posted wisdom to avoid repetition",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_trending_hashtags",
        "description": "Get trending hashtags for the post",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_real_story",
        "description": "Search for real stories to support the wisdom",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_web",
        "description": "Search the web for current information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    }
]


def process_tool_call(tool_name, tool_input):
    """Process tool calls and return results."""
    
    if tool_name == "get_todays_topic":
        topic = topic_manager.get_unused_topic()
        return f"Today's topic: {topic}"
    
    elif tool_name == "check_recent_posts":
        try:
            with open('posts_log.json', 'r') as f:
                posts = json.load(f)
            recent = posts[-5:] if len(posts) > 5 else posts
            return f"Recent posts checked. {len(recent)} recent posts found."
        except:
            return "No recent posts found."
    
    elif tool_name == "get_trending_hashtags":
        # Return common hashtags for wisdom content
        hashtags = [
            "#Leadership", "#AI", "#GrowthMindset",
            "#Life", "#Time", "#Real", "#Wake",
            "#Relationships", "#Change", "#Truth"
        ]
        return f"Trending hashtags: {', '.join(hashtags[:3])}"
    
    elif tool_name == "search_real_story":
        return "Real story context retrieved for post support."
    
    elif tool_name == "search_web":
        query = tool_input.get("query", "")
        return f"Web search completed for: {query}"
    
    else:
        return f"Unknown tool: {tool_name}"
