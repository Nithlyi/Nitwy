import discord
from discord import app_commands
from discord.ext import commands

class MemeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meme", description="Envia um meme aleatório (placeholder)")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Aqui vai um meme épico! 🐸 (adicione uma API como Reddit ou Imgflip depois)",
            ephemeral=False
        )

async def setup(bot):
    await bot.add_cog(MemeCog(bot))