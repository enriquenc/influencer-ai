from personality_analyzer.character_template import CharacterAnalyzer
from personality_analyzer.config import load_config
import json
import sys


# This is a test file to test the analyzer
# It will analyze a set of posts and print the results
# It will also demonstrate JSON serialization and deserialization

def test_analyzer():
    try:
        # Load configuration
        config = load_config()

        # Verify API key exists
        if 'openai' not in config or 'api_key' not in config['openai']:
            print("Error: Missing 'openai.api_key' in config.json")
            return False

        if not config['openai']['api_key']:
            print("Error: OpenAI API key is empty in config.json")
            return False

        print(f"Config loaded successfully. API key {'is' if config['openai']['api_key'] else 'is not'} present.")

        # Initialize analyzer with all config parameters
        analyzer = CharacterAnalyzer(
            api_key=config['openai']['api_key'],
            model=config['openai']['model'],
            temperature=config['openai']['temperature']
        )

        # Example telegram posts
        posts = [
            "Just finished my coding session! Built an amazing AI model that can recognize cats in space suits 🐱👨‍🚀",
            "Anyone interested in joining our weekly Python meetup? We'll be discussing neural networks and eating pizza 🍕",
            "Reading 'Clean Code' for the third time. It's amazing how you notice new things with each read!",
            "Just contributed to my first open source project! The community is so welcoming ❤️",
            "3 AM debugging session... Coffee is my best friend right now ☕"
        ]

        print("Analyzing posts...")
        try:
            personality = analyzer.analyze_posts(posts)
        except Exception as e:
            print(f"Error during API call: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            return False

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
        print(f"Error: Config file not found - {e}")
        print("Please ensure config.json exists in the root directory with valid OpenAI API key")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file - {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_analyzer()
    if not success:
        sys.exit(1)