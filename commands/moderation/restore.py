import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
from io import BytesIO

class RestoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="restore", description="Restaura o servidor a partir de backup JSON (DESTRUTIVO!)")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        if interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Apenas o dono do servidor pode usar este comando.", ephemeral=True)
            return

        if not arquivo.filename.lower().endswith('.json'):
            await interaction.response.send_message("Anexe um arquivo .json válido do backup.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            conteudo_bytes = await arquivo.read()
            backup_data = json.loads(conteudo_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            await interaction.followup.send("JSON inválido ou corrompido.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"Erro ao ler o arquivo: {str(e)}", ephemeral=True)
            return

        required = {"guild_id", "roles", "categories"}
        if not required.issubset(backup_data):
            await interaction.followup.send("JSON incompleto (faltam roles ou categories).", ephemeral=True)
            return

        view = RestoreConfirmView(interaction.user, self.bot, backup_data, interaction.guild)
        await interaction.followup.send(
            f"**⚠️ DESTRUIÇÃO TOTAL DA ESTRUTURA ATUAL ⚠️**\n"
            f"Backup: **{backup_data.get('guild_name', 'Desconhecido')}** (ID: {backup_data['guild_id']})\n"
            "Todos os canais, categorias e cargos (exceto @everyone) serão **deletados** e recriados.\n"
            "Overwrites (permissões específicas) serão restaurados para cargos.\n"
            "Confirme apenas se tiver certeza absoluta!",
            view=view,
            ephemeral=True
        )


class RestoreConfirmView(discord.ui.View):
    def __init__(self, owner: discord.Member, bot: commands.Bot, backup: dict, guild: discord.Guild):
        super().__init__(timeout=300)
        self.owner = owner
        self.bot = bot
        self.backup = backup
        self.guild = guild

    @discord.ui.button(label="Confirmar (IRREVERSÍVEL)", style=discord.ButtonStyle.danger)
    async def confirm_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.owner:
            return await interaction.response.send_message("Apenas o dono pode confirmar.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        msg = await interaction.followup.send("Iniciando restauração... (pode demorar alguns segundos)", ephemeral=True)

        try:
            # 1. Deletar canais existentes
            for ch in list(self.guild.channels):
                try:
                    await ch.delete(reason="Restauração de backup")
                    await asyncio.sleep(0.35)
                except:
                    pass

            # 2. Deletar cargos (exceto @everyone e managed)
            for role in list(self.guild.roles):
                if role.is_default() or role.managed:
                    continue
                try:
                    await role.delete(reason="Restauração de backup")
                    await asyncio.sleep(0.35)
                except:
                    pass

            await msg.edit(content="Estrutura antiga removida. Recriando cargos...")

            # 3. Mapa: ID antigo → novo role
            old_id_to_new = {}
            roles_sorted = sorted(self.backup["roles"], key=lambda r: r["position"], reverse=True)

            for r in roles_sorted:
                if r["name"] == "@everyone":
                    everyone = self.guild.default_role
                    await everyone.edit(
                        permissions=discord.Permissions(r["permissions"]),
                        color=discord.Color(r["color"]),
                        hoist=r["hoist"],
                        mentionable=r["mentionable"]
                    )
                    old_id_to_new[r["id"]] = everyone
                    continue

                new_role = await self.guild.create_role(
                    name=r["name"],
                    color=discord.Color(r["color"]),
                    permissions=discord.Permissions(r["permissions"]),
                    hoist=r["hoist"],
                    mentionable=r["mentionable"],
                    reason="Restauração de backup"
                )
                old_id_to_new[r["id"]] = new_role
                await asyncio.sleep(0.35)

            await msg.edit(content="Cargos recriados. Recriando categorias e canais...")

            # 4. Função auxiliar para aplicar overwrites
            async def create_channel_with_overwrites(ch_data, category=None):
                overwrites_to_apply = {}
                for ow in ch_data.get("overwrites", []):
                    if ow["target_type"] != "role":
                        continue  # Ignora member overwrites

                    old_role_id = ow["target_id"]
                    new_role = old_id_to_new.get(old_role_id)
                    if not new_role:
                        continue

                    allow = discord.Permissions(ow["allow"])
                    deny = discord.Permissions(ow["deny"])
                    overwrites_to_apply[new_role] = discord.PermissionOverwrite.from_pair(allow=allow, deny=deny)

                kwargs = {
                    "name": ch_data["name"],
                    "position": ch_data["position"],
                    "overwrites": overwrites_to_apply,
                    "reason": "Restauração de backup"
                }
                if category:
                    kwargs["category"] = category
                if "topic" in ch_data and ch_data["topic"]:
                    kwargs["topic"] = ch_data["topic"]
                if "nsfw" in ch_data:
                    kwargs["nsfw"] = ch_data["nsfw"]
                if "bitrate" in ch_data and ch_data["bitrate"]:
                    kwargs["bitrate"] = ch_data["bitrate"]
                if "user_limit" in ch_data and ch_data["user_limit"] is not None:
                    kwargs["user_limit"] = ch_data["user_limit"]

                ch_type = ch_data["type"]
                if ch_type == "text":
                    return await self.guild.create_text_channel(**kwargs)
                elif ch_type == "voice":
                    return await self.guild.create_voice_channel(**kwargs)
                elif ch_type == "stage_voice":
                    return await self.guild.create_stage_channel(**kwargs)
                return None

            # 5. Categorias + canais dentro delas
            for cat_data in self.backup.get("categories", []):
                cat_overwrites = {}
                for ow in cat_data.get("overwrites", []):
                    if ow["target_type"] != "role":
                        continue
                    old_id = ow["target_id"]
                    new_role = old_id_to_new.get(old_id)
                    if new_role:
                        allow = discord.Permissions(ow["allow"])
                        deny = discord.Permissions(ow["deny"])
                        cat_overwrites[new_role] = discord.PermissionOverwrite.from_pair(allow=allow, deny=deny)

                category = await self.guild.create_category(
                    name=cat_data["name"],
                    position=cat_data["position"],
                    overwrites=cat_overwrites,
                    reason="Restauração de backup"
                )
                await asyncio.sleep(0.4)

                for ch_data in cat_data.get("channels", []):
                    await create_channel_with_overwrites(ch_data, category)
                    await asyncio.sleep(0.4)

            # 6. Canais sem categoria
            for ch_data in self.backup.get("text_channels", []):
                await create_channel_with_overwrites(ch_data)
                await asyncio.sleep(0.4)

            for ch_data in self.backup.get("voice_channels", []):
                await create_channel_with_overwrites(ch_data)
                await asyncio.sleep(0.4)

            await msg.edit(
                content="**Restauração concluída!**\n"
                        "Cargos, categorias, canais e permissões específicas (overwrites de roles) foram restaurados.\n"
                        "Overwrites por membros **não** foram restaurados.\n"
                        "Verifique a estrutura do servidor."
            )

        except discord.Forbidden as e:
            await msg.edit(content=f"Erro: Permissões insuficientes no bot ({str(e)})")
        except Exception as e:
            await msg.edit(content=f"Erro durante restauração: {str(e)}")
        finally:
            self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.owner:
            return
        await interaction.response.send_message("Restauração cancelada.", ephemeral=True)
        self.stop()


async def setup(bot):
    await bot.add_cog(RestoreCog(bot))