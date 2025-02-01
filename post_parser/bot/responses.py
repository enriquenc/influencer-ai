class AIPersonality:
    """AI Influencer personality traits and responses"""

    WELCOME_MESSAGE = """
Hey there! 👋 I'm your AI Influencer Assistant, and I'm here to help you analyze and optimize your social media presence!

Here's what I can do for you:
📊 Parse and analyze your Telegram channel posts
💼 Track Base wallets associated with your channels
🤖 Generate AI posts matching your channel's style
📈 Provide insights about your content

Commands:
/add_channel - Add a Telegram channel
/add_wallet - Link a Base wallet to your channel
/list_channels - Show your channels and wallets
/generate_post - Create AI-generated posts for your channel

Let's make your social media presence amazing! 🚀
    """

    @staticmethod
    def channel_added(channel_name: str) -> str:
        display_name = channel_name[1:] if channel_name.startswith('@') else channel_name
        return f"""
Awesome! 🎉 I've added {display_name} to your collection.
You can now:
• Add Base wallets with /add_wallet
• View channel details with /list_channels

Ready to dive deeper into your channel's analytics? 📊
        """

    @staticmethod
    def wallet_added(channel_name: str, wallet: str) -> str:
        display_name = channel_name[1:] if channel_name.startswith('@') else channel_name
        return f"""
Great! 💼 New wallet linked to {display_name}:
`{wallet}`

I'll keep track of this wallet's activities for you. You can view all linked wallets using:
/list_wallets
        """