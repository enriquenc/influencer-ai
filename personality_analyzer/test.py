from personality_analyzer.character_template import CharacterAnalyzer
from personality_analyzer.config import load_config
import json


# This is a test file to test the analyzer
# It will analyze a set of posts and print the results
# It will also demonstrate JSON serialization and deserialization

def test_analyzer():
    try:
        # Load configuration
        config = load_config()

        # Initialize analyzer
        api_key = config['openai']['api_key']
        analyzer = CharacterAnalyzer(api_key=api_key)

        # Example telegram posts
        posts = [
            "Just finished my coding session! Built an amazing AI model that can recognize cats in space suits 🐱👨‍🚀",
            "Anyone interested in joining our weekly Python meetup? We'll be discussing neural networks and eating pizza 🍕",
            "Reading 'Clean Code' for the third time. It's amazing how you notice new things with each read!",
            "Just contributed to my first open source project! The community is so welcoming ❤️",
            "3 AM debugging session... Coffee is my best friend right now ☕"
        ]

        print("Analyzing posts...")
        personality = analyzer.analyze_posts(posts)

        # Print results in a formatted way
        print("\n=== Personality Analysis Results ===")
        print(f"\nName: {personality.name}")
        print("\nTraits:")
        for trait in personality.traits:
            print(f"- {trait}")

        print("\nInterests:")
        for interest in personality.interests:
            print(f"- {interest}")

        print(f"\nCommunication Style:\n{personality.communication_style}")

        # Demonstrate JSON serialization
        print("\n=== Testing JSON Serialization ===")
        json_data = personality.to_json()
        print("\nSerialized to JSON:")
        print(json.dumps(json.loads(json_data), indent=2))

        # Demonstrate deserialization
        restored_personality = personality.from_json(json_data)
        print("\nDeserialized successfully!")
        print(f"Restored name: {restored_personality.name}")
        print(f"Restored traits count: {len(restored_personality.traits)}")

        return True

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure config.json exists in the root directory with valid OpenAI API key")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    test_analyzer()