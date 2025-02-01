from dataclasses import dataclass
from typing import List
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

    def __init__(self, api_key: str):
        """Initialize with OpenAI API key"""
        self.client = OpenAI(api_key=api_key)

    def analyze_posts(self, posts: List[str]) -> Personality:
        """
        Analyze array of posts and generate a personality profile

        Args:
            posts: List of text posts to analyze

        Returns:
            Personality object containing the analysis
        """
        # Combine posts into single text for analysis
        combined_text = "\n".join(posts)

        # Create prompt for GPT
        system_message = """You are a personality analyzer. Analyze the social media posts and create a detailed personality profile.
        Provide the analysis in valid JSON format with the following structure:
        {
            "name": "Anonymous",
            "traits": ["trait1", "trait2", ...],
            "interests": ["interest1", "interest2", ...],
            "communication_style": "detailed description"
        }"""

        user_message = f"Posts to analyze:\n{combined_text}"

        # Get analysis from GPT using new API format
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )

        # Parse response
        analysis = json.loads(response.choices[0].message.content.strip())

        # Create Personality object
        return Personality(
            name=analysis["name"],
            traits=analysis["traits"],
            interests=analysis["interests"],
            communication_style=analysis["communication_style"],
            created_at=datetime.utcnow().isoformat(),
            raw_analysis=analysis
        )