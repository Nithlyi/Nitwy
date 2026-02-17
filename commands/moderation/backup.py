import discord
from discord import app_commands
from discord.ext import commands
import json
import datetime
from io import BytesIO

class BackupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="backup", description="Cria um backup do servidor e envia para o dono via DM.")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_command(self, interaction: discord.Interaction):
        if interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Apenas o dono do servidor pode usar este comando.", ephemeral=True)
            return

        view = ConfirmationView(interaction.user, self.bot)
        await interaction.response.send_message(
            "Você tem certeza que deseja criar um backup do servidor? Isso coletará dados como canais, cargos e permissões.",
            view=view,
            ephemeral=True
        )


class ConfirmationView(discord.ui.View):
    def __init__(self, owner: discord.User, bot: commands.Bot):
        super().__init__(timeout=60)
        self.owner = owner
        self.bot = bot

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.owner:
            await interaction.response.send_message("Apenas o dono pode confirmar.", ephemeral=True)
            return

        await interaction.response.defer()

        guild = interaction.guild
        backup_data = {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "created_at": str(datetime.datetime.now()),
            "roles": [
                {
                    "id": role.id,
                    "name": role.name,
                    "color": role.color.value,
                    "permissions": role.permissions.value,
                    "position": role.position,
                    "hoist": role.hoist,
                    "mentionable": role.mentionable
                }
                for role in guild.roles if not role.managed
            ],
            "categories": [
                {
                    "name": category.name,
                    "position": category.position,
                    "overwrites": [
                        {
                            "target_id": target.id,
                            "target_type": "role" if isinstance(target, discord.Role) else "member",
                            "allow": overwrite.allow.value,
                            "deny": overwrite.deny.value
                        }
                        for target, overwrite in category.overwrites.items()
                    ],
                    "channels": [
                        {
                            "name": channel.name,
                            "type": str(channel.type),
                            "position": channel.position,
                            "topic": getattr(channel, 'topic', None),
                            "nsfw": getattr(channel, 'nsfw', False),
                            "bitrate": getattr(channel, 'bitrate', None),
                            "user_limit": getattr(channel, 'user_limit', None),
                            "overwrites": [
                                {
                                    "target_id": target.id,
                                    "target_type": "role" if isinstance(target, discord.Role) else "member",
                                    "allow": overwrite.allow.value,
                                    "deny": overwrite.deny.value
                                }
                                for target, overwrite in channel.overwrites.items()
                            ]
                        }
                        for channel in category.channels
                    ]
                }
                for category in guild.categories
            ],
            "text_channels": [
                {
                    "name": channel.name,
                    "position": channel.position,
                    "topic": channel.topic,
                    "nsfw": channel.nsfw,
                    "overwrites": [
                        {
                            "target_id": target.id,
                            "target_type": "role" if isinstance(target, discord.Role) else "member",
                            "allow": overwrite.allow.value,
                            "deny": overwrite.deny.value
                        }
                        for target, overwrite in channel.overwrites.items()
                    ]
                }
                for channel in guild.text_channels if channel.category is None
            ],
            "voice_channels": [
                {
                    "name": channel.name,
                    "position": channel.position,
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit,
                    "overwrites": [
                        {
                            "target_id": target.id,
                            "target_type": "role" if isinstance(target, discord.Role) else "member",
                            "allow": overwrite.allow.value,
                            "deny": overwrite.deny.value
                        }
                        for target, overwrite in channel.overwrites.items()
                    ]
                }
                for channel in guild.voice_channels if channel.category is None
            ],
        }

        backup_json = json.dumps(backup_data, indent=4, ensure_ascii=False)

        file = discord.File(
            BytesIO(backup_json.encode('utf-8')),
            filename=f"backup_{guild.id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        try:
            dm_channel = await self.owner.create_dm()
            await dm_channel.send("Aqui está o backup do seu servidor:", file=file)
            await interaction.followup.send("Backup criado e enviado para sua DM com sucesso!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("Não consegui enviar DM. Verifique se DMs estão abertas.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Erro ao enviar DM: {str(e)}", ephemeral=True)

        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.owner:
            await interaction.response.send_message("Apenas o dono pode cancelar.", ephemeral=True)
            return

        await interaction.response.send_message("Backup cancelado.", ephemeral=True)
        self.stop()


async def setup(bot):
    await bot.add_cog(BackupCog(bot))