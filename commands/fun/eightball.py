# commands/fun/eightball.py
import discord
from discord import app_commands
from discord.ext import commands
import random

class EightBallCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="eightball", description="Pergunte à bola mágica 8!")
    @app_commands.describe(pergunta="Sua pergunta para a bola")
    async def eightball(self, interaction: discord.Interaction, pergunta: str):
        respostas = [
            "Sim, com certeza!", "Definitivamente não.", "Provavelmente sim.",
            "Pergunte mais tarde.", "Melhor não te contar agora.", "Sinais apontam para sim.",
            "Minhas fontes dizem não.", "Concentre-se e pergunte novamente.", "Não conte com isso.",
            "Parece bom!", "Duvidoso.", "Absolutamente!", "Não é uma boa ideia.",
            "Vai acontecer.", "Improvável."
        ]
        resposta = random.choice(respostas)
        embed = discord.Embed(
            title="🎱 Bola Mágica 8",
            description=f"**Pergunta:** {pergunta}\n**Resposta:** {resposta}",
            color=discord.Color.from_str("#1A1A1A")
        )
        embed.set_footer(text="Pergunte com sabedoria!")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EightBallCog(bot))