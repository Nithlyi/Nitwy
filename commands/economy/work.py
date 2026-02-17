import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime

class WorkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="work", description="Trabalhe e ganhe moedas")
    async def work(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        now = datetime.datetime.utcnow()

        data = self.bot.db.economy.find_one({"guild_id": guild_id, "user_id": user_id}) or {"coins": 0, "last_work": None}

        if data.get("last_work"):
            last = datetime.datetime.fromisoformat(data["last_work"])
            if (now - last).total_seconds() < 3600:  # 1 hora cooldown
                remaining = 3600 - (now - last).total_seconds()
                await interaction.response.send_message(f"Volte em {int(remaining//60)} minutos.", ephemeral=True)
                return

        reward = random.randint(50, 150)
        data["coins"] = data.get("coins", 0) + reward
        data["last_work"] = now.isoformat()

        self.bot.db.economy.replace_one(
            {"guild_id": guild_id, "user_id": user_id},
            data,
            upsert=True
        )

        await interaction.response.send_message(f"Você trabalhou e ganhou **{reward} moedas**! 💼")

async def setup(bot):
    await bot.add_cog(WorkCog(bot))