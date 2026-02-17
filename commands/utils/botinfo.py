import discord
from discord import app_commands
from discord.ext import commands

class BotInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="botinfo", description="Mostra informações do bot")
    async def botinfo(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"Informações do Bot: {self.bot.user.name}",
            color=0x040505
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        embed.add_field(name="👤 Bot", value=self.bot.user.name, inline=True)
        embed.add_field(name="🆔 ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="👑 Dono", value="Syrentya", inline=True)
        
        embed.add_field(name="🏓 Latência", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🌐 Servidores", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="📊 Comandos", value="55", inline=True)
        
        embed.set_footer(text=f"Solicitado por {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BotInfo(bot))