import discord
from discord import app_commands, ui
from discord.ext import commands
import datetime
import logging

logger = logging.getLogger(__name__)

class WelcomeView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def send_welcome(self, member: discord.Member):
        logger.info(f"[DEBUG] Iniciando send_welcome para {member}...")
        config = self.bot.db.welcome_configs.find_one({"guild_id": member.guild.id})
        if not config:
            logger.info("[DEBUG] Nenhuma configuração encontrada no DB.")
            return
        if not config.get("enabled", True):
            logger.info("[DEBUG] Sistema de welcome desativado.")
            return
        channel_id = config.get("channel_id")
        if not channel_id:
            logger.info("[DEBUG] Canal não definido na configuração.")
            return
        channel = member.guild.get_channel(channel_id)
        if not channel:
            logger.info("[DEBUG] Canal não encontrado (ID inválido ou bot sem acesso).")
            return
        logger.info(f"[DEBUG] Canal encontrado: {channel} (ID: {channel.id}). Tentando enviar embed...")

        embed_config = config.get("embed", {
            "title": "Bem-vindo(a) ao {server}!",
            "description": "Olá {user.mention}! Esperamos que você se divirta muito aqui!\nMembros atuais: {member_count}",
            "color": 0x00ff88,
            "thumbnail": "{user.avatar}",
            "image": None,
            "footer": "ID: {user.id} • Entrou em {timestamp}",
            "fields": []
        })

        def replace_vars(text: str) -> str:
            if not text:
                return ""
            try:
                return text.format(
                    user=member,
                    user_mention=member.mention,
                    user_name=member.name,
                    server=member.guild.name,
                    member_count=member.guild.member_count,
                    timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                    user_created=discord.utils.format_dt(member.created_at, "F"),
                    user_joined=discord.utils.format_dt(member.joined_at, "F") if member.joined_at else "N/A"
                )
            except KeyError as e:
                logger.warning(f"Erro de formatação em '{text}': {e}")
                return text  # Retorna o texto original se houver erro

        title = replace_vars(embed_config.get("title", "Bem-vindo(a)!"))
        description = replace_vars(embed_config.get("description", ""))

        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_config.get("color", 0x00ff88)
        )

        if embed_config.get("thumbnail"):
            thumb = replace_vars(embed_config["thumbnail"])
            if "{user.avatar}" in thumb:
                embed.set_thumbnail(url=member.display_avatar.url)  # Correção: usa display_avatar para compatibilidade
            else:
                embed.set_thumbnail(url=thumb)

        if embed_config.get("image"):
            img = replace_vars(embed_config["image"])
            embed.set_image(url=img)

        if embed_config.get("footer"):
            footer = replace_vars(embed_config["footer"])
            embed.set_footer(text=footer)

        for field in embed_config.get("fields", []):
            name = replace_vars(field.get("name", "Campo"))
            value = replace_vars(field.get("value", "Valor"))
            inline = field.get("inline", False)
            embed.add_field(name=name, value=value, inline=inline)

        try:
            await channel.send(embed=embed)
            logger.info("[DEBUG] Mensagem de welcome enviada com sucesso!")
        except Exception as e:
            logger.error(f"[DEBUG] Erro ao enviar mensagem: {e}")


class WelcomeConfigView(ui.View):
    def __init__(self, bot, interaction):
        super().__init__(timeout=600)
        self.bot = bot
        self.interaction = interaction
        self.guild_id = interaction.guild_id
        self.config = self.bot.db.welcome_configs.find_one({"guild_id": self.guild_id}) or {
            "enabled": True,
            "channel_id": None,
            "embed": {
                "title": "Bem-vindo(a) ao {server}!",
                "description": "Olá {user.mention}! Esperamos que você se divirta muito aqui!\nMembros atuais: {member_count}",
                "color": 0x00ff88,
                "thumbnail": "{user.avatar}",
                "image": None,
                "footer": "ID: {user.id} • Entrou em {timestamp}",
                "fields": []
            }
        }
        self.preview_message = None

    async def update_preview(self):
        embed = discord.Embed(
            title="Configuração de Welcome (Preview ao vivo)",
            description="Edite os campos e veja a mensagem de boas-vindas em tempo real.",
            color=discord.Color.blue()
        )

        user = self.interaction.user
        guild = self.interaction.guild

        preview_embed = discord.Embed(
            title=self.config["embed"].get("title", "Bem-vindo(a)!").format(
                user=user,
                server=guild.name,
                member_count=guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(user, 'joined_at') and getattr(user, 'joined_at') else "N/A"
            ),
            description=self.config["embed"].get("description", "").format(
                user=user,
                server=guild.name,
                member_count=guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(user, 'joined_at') and getattr(user, 'joined_at') else "N/A"
            ),
            color=self.config["embed"].get("color", 0x00ff88)
        )

        if self.config["embed"].get("thumbnail"):
            thumb = self.config["embed"]["thumbnail"].format(user=user)
            if "{user.avatar}" in thumb:
                preview_embed.set_thumbnail(url=getattr(user, 'display_avatar', None).url if hasattr(user, 'display_avatar') and user.display_avatar else None)
            else:
                preview_embed.set_thumbnail(url=thumb)

        if self.config["embed"].get("image"):
            img = self.config["embed"]["image"].format(user=user)
            preview_embed.set_image(url=img)

        if self.config["embed"].get("footer"):
            footer = self.config["embed"]["footer"].format(
                user=user,
                server=guild.name,
                member_count=guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(user, 'joined_at') and getattr(user, 'joined_at') else "N/A"
            )
            preview_embed.set_footer(text=footer)

        for field in self.config["embed"].get("fields", []):
            name = field.get("name", "Campo").format(
                user=user,
                server=guild.name,
                member_count=guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(user, 'joined_at') and getattr(user, 'joined_at') else "N/A"
            )
            value = field.get("value", "Valor").format(
                user=user,
                server=guild.name,
                member_count=guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(user, 'joined_at') and getattr(user, 'joined_at') else "N/A"
            )
            inline = field.get("inline", False)
            preview_embed.add_field(name=name, value=value, inline=inline)

        embed.add_field(name="Canal de Envio", value=f"<#{self.config.get('channel_id', 'Não definido')}>", inline=True)
        embed.add_field(name="Ativado?", value="Sim" if self.config.get("enabled", True) else "Não", inline=True)
        embed.add_field(name="Preview da mensagem de boas-vindas", value="↓ Veja abaixo ↓", inline=False)

        if self.preview_message:
            await self.preview_message.edit(embed=embed, view=self)
            await self.preview_message.edit(embed=preview_embed)
        else:
            self.preview_message = await self.interaction.followup.send(embed=embed, view=self, ephemeral=True)
            await self.preview_message.edit(embed=preview_embed)

    # Botões de edição
    @ui.button(label="Editar Título", style=discord.ButtonStyle.primary, row=0)
    async def edit_title(self, interaction: discord.Interaction, _):
        modal = SimpleEditModal(self, "title", "Título da mensagem de welcome")
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Descrição", style=discord.ButtonStyle.primary, row=0)
    async def edit_desc(self, interaction: discord.Interaction, _):
        modal = SimpleEditModal(self, "description", "Descrição da mensagem", paragraph=True)
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Cor (hex)", style=discord.ButtonStyle.primary, row=1)
    async def edit_color(self, interaction: discord.Interaction, _):
        modal = SimpleEditModal(self, "color", "Cor do embed (#RRGGBB)")
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Thumbnail URL", style=discord.ButtonStyle.primary, row=1)
    async def edit_thumbnail(self, interaction: discord.Interaction, _):
        modal = SimpleEditModal(self, "thumbnail", "URL da thumbnail (ou {user.avatar})")
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Imagem Principal (URL)", style=discord.ButtonStyle.primary, row=2)
    async def edit_image(self, interaction: discord.Interaction, _):
        modal = SimpleEditModal(self, "image", "URL da imagem grande")
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Footer", style=discord.ButtonStyle.secondary, row=2)
    async def edit_footer(self, interaction: discord.Interaction, _):
        modal = SimpleEditModal(self, "footer", "Texto do rodapé")
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Campo 1", style=discord.ButtonStyle.secondary, row=3)
    async def edit_field1(self, interaction: discord.Interaction, _):
        modal = FieldEditModal(self, 0)
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Campo 2", style=discord.ButtonStyle.secondary, row=3)
    async def edit_field2(self, interaction: discord.Interaction, _):
        modal = FieldEditModal(self, 1)
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Campo 3", style=discord.ButtonStyle.secondary, row=4)
    async def edit_field3(self, interaction: discord.Interaction, _):
        modal = FieldEditModal(self, 2)
        await interaction.response.send_modal(modal)

    @ui.button(label="Editar Campo 4", style=discord.ButtonStyle.secondary, row=4)
    async def edit_field4(self, interaction: discord.Interaction, _):
        modal = FieldEditModal(self, 3)
        await interaction.response.send_modal(modal)

    @ui.button(label="Definir Canal (ID)", style=discord.ButtonStyle.secondary, row=4)
    async def edit_channel(self, interaction: discord.Interaction, _):
        modal = SimpleEditModal(self, "channel_id", "ID do canal de boas-vindas")
        await interaction.response.send_modal(modal)

    @ui.button(label="Ativar/Desativar", style=discord.ButtonStyle.secondary, row=4)
    async def toggle_enabled(self, interaction: discord.Interaction, _):
        self.config["enabled"] = not self.config.get("enabled", True)
        self.bot.db.welcome_configs.update_one(
            {"guild_id": self.guild_id},
            {"$set": {"enabled": self.config["enabled"]}},
            upsert=True
        )
        await self.update_preview()
        await interaction.response.send_message(f"Sistema de welcome agora está **{'ativado' if self.config['enabled'] else 'desativado'}**.", ephemeral=True)

    @ui.button(label="Resetar Tudo", style=discord.ButtonStyle.danger, row=4)
    async def reset(self, interaction: discord.Interaction, _):
        self.bot.db.welcome_configs.delete_one({"guild_id": self.guild_id})
        self.config = {
            "enabled": True,
            "channel_id": None,
            "embed": {
                "title": "Bem-vindo(a) ao {server}!",
                "description": "Olá {user.mention}! Esperamos que você se divirta muito aqui!\nMembros atuais: {member_count}",
                "color": 0x00ff88,
                "thumbnail": "{user.avatar}",
                "image": None,
                "footer": "ID: {user.id} • Entrou em {timestamp}",
                "fields": []
            }
        }
        await self.update_preview()
        await interaction.response.send_message("Configurações de welcome resetadas para padrão!", ephemeral=True)


class SimpleEditModal(ui.Modal):
    def __init__(self, view, field, title, paragraph=False):
        super().__init__(title=f"Editar {title}")
        self.view = view
        self.field = field
        default = ""
        if field in ["title", "description", "thumbnail", "image", "footer"]:
            default = str(view.config.get("embed", {}).get(field, ""))
        elif field == "color":
            default = hex(view.config.get("embed", {}).get(field, 0x00ff88))[2:].zfill(6)
        else:
            default = str(view.config.get(field, ""))

        self.input = ui.TextInput(
            label=title,
            style=discord.TextStyle.paragraph if paragraph else discord.TextStyle.short,
            default=default,
            required=False
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.input.value.strip()

        if self.field in ["title", "description", "thumbnail", "image", "footer"]:
            embed_data = self.view.config.setdefault("embed", {})
            embed_data[self.field] = value if value else None
            self.view.bot.db.welcome_configs.update_one(
                {"guild_id": self.view.guild_id},
                {"$set": {"embed": embed_data}},
                upsert=True
            )
        elif self.field == "color":
            if value:
                try:
                    value = int(value.lstrip('#'), 16)
                except ValueError:
                    await interaction.response.send_message("Cor inválida. Use #RRGGBB ou deixe vazio.", ephemeral=True)
                    return
            else:
                value = 0x00ff88
            embed_data = self.view.config.setdefault("embed", {})
            embed_data[self.field] = value
            self.view.bot.db.welcome_configs.update_one(
                {"guild_id": self.view.guild_id},
                {"$set": {"embed": embed_data}},
                upsert=True
            )
        else:
            try:
                value = int(value) if value else None
            except ValueError:
                value = None
            self.view.config[self.field] = value
            self.view.bot.db.welcome_configs.update_one(
                {"guild_id": self.view.guild_id},
                {"$set": {self.field: value}},
                upsert=True
            )

        await self.view.update_preview()
        await interaction.response.send_message(f"**{self.field.capitalize()}** atualizado!", ephemeral=True)


class FieldEditModal(ui.Modal, title="Editar Campo Extra"):
    name = ui.TextInput(label="Nome do campo", style=discord.TextStyle.short, required=True)
    value = ui.TextInput(label="Valor do campo (use variáveis)", style=discord.TextStyle.paragraph, required=True)
    inline = ui.TextInput(label="Inline? (sim/não)", style=discord.TextStyle.short, default="sim", required=False)

    def __init__(self, view, field_index):
        super().__init__()
        self.view = view
        self.field_index = field_index
        fields = self.view.config["embed"].setdefault("fields", [{} for _ in range(4)])  # Garante 4 campos vazios
        while len(fields) <= field_index:
            fields.append({})
        field = fields[field_index]
        self.name.default = field.get("name", "")
        self.value.default = field.get("value", "")
        self.inline.default = "sim" if field.get("inline", False) else "não"

    async def on_submit(self, interaction: discord.Interaction):
        fields = self.view.config["embed"].setdefault("fields", [{} for _ in range(4)])
        field = fields[self.field_index]
        field["name"] = self.name.value
        field["value"] = self.value.value
        field["inline"] = self.inline.value.lower() in ["sim", "s", "yes", "y", "true"]

        self.view.bot.db.welcome_configs.update_one(
            {"guild_id": self.view.guild_id},
            {"$set": {"embed.fields": fields}},
            upsert=True
        )

        await self.view.update_preview()
        await interaction.response.send_message(f"Campo {self.field_index + 1} atualizado!", ephemeral=True)

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        logger.info(f"[DEBUG] on_member_join disparado para {member} (ID: {member.id}) em {member.guild.name} (Guild ID: {member.guild.id})")
        await WelcomeView(self.bot).send_welcome(member)

    @app_commands.command(name="welcomeconfig", description="[Admin] Configura a mensagem de boas-vindas com preview ao vivo")
    @app_commands.default_permissions(administrator=True)
    async def welcomeconfig(self, interaction: discord.Interaction):
        view = WelcomeConfigView(self.bot, interaction)
        await interaction.response.defer(ephemeral=True)
        await view.update_preview()

    @app_commands.command(name="welcomesendtest", description="[Admin] Envia um teste da mensagem de boas-vindas atual")
    @app_commands.default_permissions(administrator=True)
    async def welcomesendtest(self, interaction: discord.Interaction):
        config = self.bot.db.welcome_configs.find_one({"guild_id": interaction.guild_id})
        if not config:
            return await interaction.response.send_message("Configure primeiro com /welcomeconfig", ephemeral=True)

        channel = interaction.channel
        embed_config = config.get("embed", {
            "title": "Bem-vindo(a) ao {server}!",
            "description": "Olá {user.mention}! Esperamos que você se divirta muito aqui!\nMembros atuais: {member_count}",
            "color": 0x00ff88,
            "thumbnail": "{user.avatar}",
            "image": None,
            "footer": "ID: {user.id} • Entrou em {timestamp}",
            "fields": []
        })

        title = embed_config.get("title", "").format(
            user=interaction.user,
            server=interaction.guild.name,
            member_count=interaction.guild.member_count,
            timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
            user_created=discord.utils.format_dt(getattr(interaction.user, 'created_at', discord.utils.utcnow()), "F"),
            user_joined=discord.utils.format_dt(getattr(interaction.user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(interaction.user, 'joined_at') else "N/A"
        )
        description = embed_config.get("description", "").format(
            user=interaction.user,
            server=interaction.guild.name,
            member_count=interaction.guild.member_count,
            timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
            user_created=discord.utils.format_dt(getattr(interaction.user, 'created_at', discord.utils.utcnow()), "F"),
            user_joined=discord.utils.format_dt(getattr(interaction.user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(interaction.user, 'joined_at') else "N/A"
        )

        embed = discord.Embed(title=title, description=description, color=embed_config.get("color", 0x00ff88))

        if embed_config.get("thumbnail"):
            thumb = embed_config["thumbnail"].format(user=interaction.user)
            if "{user.avatar}" in thumb:
                embed.set_thumbnail(url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
            else:
                embed.set_thumbnail(url=thumb)

        if embed_config.get("image"):
            img = embed_config["image"].format(user=interaction.user)
            embed.set_image(url=img)

        if embed_config.get("footer"):
            footer = embed_config["footer"].format(
                user=interaction.user,
                server=interaction.guild.name,
                member_count=interaction.guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(interaction.user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(interaction.user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(interaction.user, 'joined_at') else "N/A"
            )
            embed.set_footer(text=footer)

        for field in embed_config.get("fields", []):
            name = field.get("name", "Campo").format(
                user=interaction.user,
                server=interaction.guild.name,
                member_count=interaction.guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(interaction.user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(interaction.user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(interaction.user, 'joined_at') else "N/A"
            )
            value = field.get("value", "Valor").format(
                user=interaction.user,
                server=interaction.guild.name,
                member_count=interaction.guild.member_count,
                timestamp=discord.utils.format_dt(discord.utils.utcnow(), "F"),
                user_created=discord.utils.format_dt(getattr(interaction.user, 'created_at', discord.utils.utcnow()), "F"),
                user_joined=discord.utils.format_dt(getattr(interaction.user, 'joined_at', discord.utils.utcnow()), "F") if hasattr(interaction.user, 'joined_at') else "N/A"
            )
            inline = field.get("inline", False)
            embed.add_field(name=name, value=value, inline=inline)

        await channel.send(embed=embed)
        await interaction.response.send_message("Teste de boas-vindas enviado no canal atual!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Welcome(bot))