import discord
from discord import app_commands
from discord.ext import commands
import datetime

class DailyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="daily", description="Coletar sua recompensa diária")
    async def daily(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        now = datetime.datetime.utcnow()

        user_data = self.bot.db.economy.find_one({"guild_id": guild_id, "user_id": user_id}) or {"coins": 0, "last_daily": None}
        
        if user_data.get("last_daily"):
            last = datetime.datetime.fromisoformat(user_data["last_daily"])
            if (now - last).days < 1:
                remaining = (last + datetime.timedelta(days=1) - now)
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes = remainder // 60
                await interaction.response.send_message(f"Você já coletou hoje! Volte em {hours}h {minutes}min.", ephemeral=True)
                return

        reward = 100  # ajuste o valor
        user_data["coins"] = user_data.get("coins", 0) + reward
        user_data["last_daily"] = now.isoformat()

        self.bot.db.economy.replace_one(
            {"guild_id": guild_id, "user_id": user_id},
            user_data,
            upsert=True
        )

        await interaction.response.send_message(f"Você coletou **{reward} moedas**! Saldo atual: {user_data['coins']} 🪙")

async def setup(bot):
    await bot.add_cog(DailyCog(bot))