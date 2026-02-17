import discord
from discord import app_commands
from discord.ext import commands

class BalanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Veja seu saldo de moedas")
    @app_commands.describe(member="Usuário (opcional, padrão: você)")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        guild_id = interaction.guild_id
        user_id = target.id

        user_data = self.bot.db.economy.find_one({"guild_id": guild_id, "user_id": user_id}) or {"coins": 0}
        coins = user_data["coins"]

        embed = discord.Embed(title="Saldo", color=discord.Color.gold())
        embed.add_field(name="Usuário", value=target.mention, inline=False)
        embed.add_field(name="Moedas", value=f"{coins} 🪙", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BalanceCog(bot))