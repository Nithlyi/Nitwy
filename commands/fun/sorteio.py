import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import asyncio

class SorteioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sorteio", description="Criar um sorteio simples")
    @app_commands.describe(premio="O prêmio", duracao_min="Duração em minutos")
    async def sorteio(self, interaction: discord.Interaction, premio: str, duracao_min: int):
        embed = discord.Embed(title="🎉 SORTEIO!", description=f"**Prêmio:** {premio}\nReaja com 🎟️ para participar!\nTermina em {duracao_min} minutos.", color=discord.Color.gold())
        embed.set_footer(text=f"Iniciado por {interaction.user.name} | ID: {interaction.id}")
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎟️")

        await interaction.response.send_message("Sorteio criado! Boa sorte a todos.", ephemeral=True)

        await asyncio.sleep(duracao_min * 60)

        msg = await interaction.channel.fetch_message(msg.id)
        users = []
        async for user in msg.reactions[0].users():
            if not user.bot:
                users.append(user)

        if len(users) == 0:
            await interaction.channel.send("Ninguém participou do sorteio... 😢")
            return

        winner = random.choice(users)
        await interaction.channel.send(f"Parabéns {winner.mention}! Você ganhou: **{premio}**! 🎉")

async def setup(bot):
    await bot.add_cog(SorteioCog(bot))