from bot import Bot
from .ticket import Ticket


async def setup(bot: Bot):
    await bot.add_cog(Ticket(bot))
