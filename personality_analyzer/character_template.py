from dataclasses import dataclass
from typing import List, Optional
import json
from datetime import datetime
from openai import OpenAI

@dataclass
class Personality:
    """Class representing a personality analysis result"""

    name: str
    traits: List[str]
    interests: List[str]
    communication_style: str
    created_at: str
    updated_at: str  # New field to track last update
    post_count: int  # New field to track number of analyzed posts
    raw_analysis: dict

    def to_json(self) -> str:
        """Convert personality to JSON string"""
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str: str) -> 'Personality':
        """Create Personality instance from JSON string"""
        data = json.loads(json_str)
        return cls(**data)

class CharacterAnalyzer:
    """Class for analyzing text content and generating personality profiles"""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", temperature: float = 0.7):
        """Initialize with OpenAI API key and optional parameters"""
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def analyze_posts(self, posts: List[str], previous_personality: Optional[Personality] = None) -> Personality:
        """
        Analyze array of posts and generate or update a personality profile

        Args:
            posts: List of text posts to analyze
            previous_personality: Optional existing personality to update

        Returns:
            Updated or new Personality object
        """
        combined_text = "\n".join(posts)
        current_time = datetime.utcnow().isoformat()

        if previous_personality:
            system_message = """You are a personality analyzer. You will be given a previous personality analysis and new posts.
            Update the personality profile considering both the previous analysis and new information from the posts.
            Focus on evolving traits and interests based on new evidence, while maintaining consistency with previous observations where appropriate."""

            user_message = f"""Previous personality analysis:
            Traits: {', '.join(previous_personality.traits)}
            Interests: {', '.join(previous_personality.interests)}
            Communication Style: {previous_personality.communication_style}

            New posts to analyze:
            {combined_text}

            Provide an updated analysis in valid JSON format with the following structure:
            {{
                "name": "{previous_personality.name}",
                "traits": ["trait1", "trait2", ...],
                "interests": ["interest1", "interest2", ...],
                "communication_style": "detailed description",
                "changes_noted": ["change1", "change2", ...]
            }}"""

            post_count = previous_personality.post_count + len(posts)
            created_at = previous_personality.created_at
        else:
            system_message = """You are a personality analyzer. Analyze the social media posts and create a detailed personality profile."""

            user_message = f"""Posts to analyze:
            {combined_text}

            Provide analysis in valid JSON format with the following structure:
            {{
                "name": "Anonymous",
                "traits": ["trait1", "trait2", ...],
                "interests": ["interest1", "interest2", ...],
                "communication_style": "detailed description",
                "changes_noted": []
            }}"""

            post_count = len(posts)
            created_at = current_time

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=self.temperature
        )

        analysis = json.loads(response.choices[0].message.content.strip())

        # Store any noted changes in raw_analysis
        raw_analysis = {
            **analysis,
            "previous_traits": previous_personality.traits if previous_personality else None,
            "previous_interests": previous_personality.interests if previous_personality else None,
            "previous_communication_style": previous_personality.communication_style if previous_personality else None
        }

        return Personality(
            name=analysis["name"],
            traits=analysis["traits"],
            interests=analysis["interests"],
            communication_style=analysis["communication_style"],
            created_at=created_at,
            updated_at=current_time,
            post_count=post_count,
            raw_analysis=raw_analysis
        )