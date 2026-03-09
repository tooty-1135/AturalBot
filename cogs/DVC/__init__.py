from bot import Bot
from .dvc import DVC


async def setup(bot: Bot):
    await bot.add_cog(DVC(bot))
