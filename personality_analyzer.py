class CharacterAnalyzer:
    # ... existing code ...

    def generate_post(self, personality, recent_activity=None) -> str:
        """Generate a post based on channel personality and recent activity"""

        # Create a prompt that incorporates the channel's personality
        prompt = f"""Generate a Telegram post with the following characteristics:

Personality Traits: {', '.join(personality.traits[:3])}
Main Interests: {', '.join(personality.interests[:3])}
Communication Style: {personality.communication_style}

The post should:
1. Match the communication style exactly
2. Focus on topics from the main interests
3. Express the personality traits naturally
4. Be concise and engaging
5. Include relevant emojis
6. Be formatted for Telegram

Generate the post:"""

        # If we have recent activity, add it to the context
        if recent_activity:
            prompt += f"\n\nRecent channel activity:\n{recent_activity}"

        try:
            # Use the AI model to generate the post
            response = self.ai_model.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.7,  # Some creativity but not too random
                stop=["---", "###"]  # Stop markers
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating post: {e}")
            raise ValueError("Failed to generate post")