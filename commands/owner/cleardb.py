import discord
from discord import app_commands, Interaction
from discord.ext import commands
import asyncio

# Check global (fora da classe) - recebe apenas interaction
async def is_bot_owner(interaction: discord.Interaction) -> bool:
    return await interaction.client.is_owner(interaction.user)


class ClearDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cleardb", description="Limpa a configuração do servidor no banco de dados (apenas dono)")
    @app_commands.check(is_bot_owner)  # ← usa o check global
    async def clear_db(self, interaction: Interaction):
        guild_id = interaction.guild_id

        # Confirmação extra
        await interaction.response.send_message(
            "Você tem certeza que deseja **limpar todas as configurações deste servidor** no banco de dados?\n"
            "Digite `SIM` nos próximos 10 segundos para confirmar.",
            ephemeral=True
        )

        def check(m):
            return m.author.id == interaction.user.id and m.content.upper() == "SIM" and m.channel == interaction.channel

        try:
            await self.bot.wait_for('message', check=check, timeout=10.0)

            # Deleta apenas o documento desse servidor
            result = self.bot.db.guild_configs.delete_one({"guild_id": guild_id})

            if result.deleted_count > 0:
                await interaction.followup.send(
                    f"Configuração do servidor **{interaction.guild.name}** apagada com sucesso do banco.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Nenhuma configuração encontrada para este servidor.",
                    ephemeral=True
                )

        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado. Limpeza cancelada.", ephemeral=True)

    @clear_db.error
    async def clear_db_error(self, interaction: Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Apenas o dono do bot pode usar este comando.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Erro: {error}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ClearDB(bot))