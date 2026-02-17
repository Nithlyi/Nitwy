import discord
from discord import app_commands
from discord.ext import commands
import random

class CoinFlipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="coinflip", description="Joga uma moeda cara ou coroa")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Cara", "Coroa"])
        await interaction.response.send_message(f"**{interaction.user.mention} jogou a moeda...** {result}!")

async def setup(bot):
    await bot.add_cog(CoinFlipCog(bot))