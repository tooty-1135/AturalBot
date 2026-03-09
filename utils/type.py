from bot import Bot



class PartialMessage:
    channel_id = None
    id = None

    def __init__(self, channel_id, message_id):
        self.channel_id = channel_id
        self.id = message_id

    async def get(self, bot:Bot):
        channel = await bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.id)
        return message