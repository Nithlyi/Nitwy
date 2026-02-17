import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, Button, View, Modal, TextInput
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Classes auxiliares movidas para fora da cog para persistência
class CorSelect(Select):
    def __init__(self, cog, cores_dict, placeholder="Escolha uma cor...", custom_id=None):
        self.cog = cog
        options = [discord.SelectOption(label=nome, value=nome) for nome in cores_dict.keys()]
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        cor_nome = self.values[0]
        cores = self.cog.get_cores_ativas()
        cor_hex = cores[cor_nome]
        
        # Verifica e remove roles de cores antigas da palheta ativa
        user = interaction.user
        cores_ativas = self.cog.get_cores_ativas()
        roles_removidos = 0
        for r in user.roles:
            if r.name in cores_ativas.keys():
                await user.remove_roles(r)
                roles_removidos += 1
        
        # Tenta encontrar ou criar o role da nova cor
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=cor_nome)
        if not role:
            role = await guild.create_role(name=cor_nome, color=discord.Color(cor_hex))
        
        # Atribui a nova cor
        await user.add_roles(role)
        
        # Mensagem de confirmação com info sobre remoções
        if roles_removidos > 0:
            await interaction.response.send_message(f"Cor '{cor_nome}' atribuída a você! ({roles_removidos} cor(es) antiga(s) removida(s))", ephemeral=True)
        else:
            await interaction.response.send_message(f"Cor '{cor_nome}' atribuída a você!", ephemeral=True)

class PainelCores(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        tipo = cog.tipo_cores
        if tipo == 'all':
            # Para 'all', divide em 3 selects para evitar limite de 25
            self.add_item(CorSelect(cog, cog.cores_normais, "Escolha uma cor normal...", custom_id="color:normais"))
            self.add_item(CorSelect(cog, cog.cores_pastel, "Escolha uma cor pastel...", custom_id="color:pastel"))
            self.add_item(CorSelect(cog, cog.cores_gothic, "Escolha uma cor gothic...", custom_id="color:gothic"))
        else:
            # Para tipos específicos, um select único
            cores = cog.get_cores_ativas()
            self.add_item(CorSelect(cog, cores, custom_id="color:single"))

class Color(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        self.db_name = "discord_bot"  # Nome do banco
        self.collection_name = "color_config"
        self.client = None
        self.collection = None
        self.connect_mongo()
        self.load_config()  # Carrega configurações do MongoDB
        # Adiciona views persistentes para sobreviver a reinicializações
        self.bot.add_view(PainelCores(self))

    def connect_mongo(self):
        try:
            self.client = MongoClient(self.mongo_uri)
            self.collection = self.client[self.db_name][self.collection_name]
            # Testa conexão
            self.client.admin.command('ping')
            print("Conectado ao MongoDB com sucesso.")
        except ConnectionFailure:
            print("Erro ao conectar ao MongoDB. Usando valores padrão.")
            self.client = None
            self.collection = None

    def load_config(self):
        if self.collection is not None:
            doc = self.collection.find_one({"_id": "config"})
            if doc:
                self.tipo_cores = doc.get("tipo_cores", 'all')
                self.embed_title = doc.get("embed_title", "Painel de Cores")
                self.embed_description = doc.get("embed_description", "Escolha uma cor abaixo:")
                self.embed_color = doc.get("embed_color", 0x00ff00)
                self.embed_footer = doc.get("embed_footer", "")
                self.embed_thumbnail = doc.get("embed_thumbnail", None)
                self.embed_image = doc.get("embed_image", None)
            else:
                self.set_defaults()
        else:
            self.set_defaults()

    def set_defaults(self):
        self.tipo_cores = 'all'
        self.embed_title = "Painel de Cores"
        self.embed_description = "Escolha uma cor abaixo:"
        self.embed_color = 0x00ff00
        self.embed_footer = ""
        self.embed_thumbnail = None
        self.embed_image = None

    def save_config(self):
        if self.collection is not None:
            data = {
                "_id": "config",
                "tipo_cores": self.tipo_cores,
                "embed_title": self.embed_title,
                "embed_description": self.embed_description,
                "embed_color": self.embed_color,
                "embed_footer": self.embed_footer,
                "embed_thumbnail": self.embed_thumbnail,
                "embed_image": self.embed_image
            }
            self.collection.replace_one({"_id": "config"}, data, upsert=True)

    # Dicionários de cores: nome -> cor hex
    cores_normais = {
        "Vermelho": 0xFF0000,
        "Azul": 0x0000FF,
        "Verde": 0x00FF00,
        "Amarelo": 0xFFFF00,
        "Roxo": 0x800080,
        "Laranja": 0xFFA500,
        "Rosa": 0xFFC0CB,
        "Ciano": 0x00FFFF,
        "Magenta": 0xFF00FF,
        "Preto": 0x000000
    }

    cores_pastel = {
        "Rosa Pastel": 0xFFB6C1,
        "Azul Pastel": 0x87CEEB,
        "Verde Pastel": 0x98FB98,
        "Amarelo Pastel": 0xFFFACD,
        "Roxo Pastel": 0xDDA0DD,
        "Laranja Pastel": 0xFFDAB9,
        "Ciano Pastel": 0xE0FFFF,
        "Magenta Pastel": 0xFF69B4,
        "Cinza Pastel": 0xD3D3D3,
        "Branco": 0xFFFFFF,
        "Lavanda Pastel": 0xE6E6FA,
        "Menta Pastel": 0xF5FFFA,
        "Pêssego Pastel": 0xFFDAB9,
        "Lilás Pastel": 0xC8A2C8,
        "Aqua Pastel": 0xB0E0E6,
        "Champanhe Pastel": 0xF7E7CE,
        "Coral Pastel": 0xFAD5A5,
        "Melão Pastel": 0xFDBCB4,
        "Azul Céu Pastel": 0x87CEFA,
        "Verde Lima Pastel": 0xCCFFCC
    }

    cores_gothic = {
        "Preto Gothic": 0x000000,
        "Roxo Escuro": 0x4B0082,
        "Vermelho Sangue": 0x8B0000,
        "Cinza Escuro": 0x2F4F4F,
        "Azul Noite": 0x191970,
        "Verde Floresta": 0x006400,
        "Dourado Escuro": 0xB8860B,
        "Prata": 0xC0C0C0,
        "Marrom Antigo": 0x8B4513,
        "Violeta": 0x9400D3,
        "Preto Ébano": 0x1A1A1A,
        "Roxo Sombrio": 0x2E003E,
        "Vermelho Escarlate": 0x660000,
        "Cinza Sepulcral": 0x1C1C1C,
        "Azul Abismo": 0x000080,
        "Verde Sombra": 0x004400,
        "Dourado Antigo": 0x8B7355,
        "Prata Lunar": 0xA9A9A9,
        "Marrom Terreno": 0x5C4033,
        "Violeta Noturno": 0x4B0082,
        "Preto Profundo": 0x0A0A0A,
        "Roxo Enigmático": 0x301934,
        "Vermelho Carmesim": 0x8B0000,
        "Cinza Espectral": 0x696969,
        "Azul Profundo": 0x00008B
    }

    # Função para obter as cores ativas com base no tipo
    def get_cores_ativas(self):
        if self.tipo_cores == 'normais':
            return self.cores_normais
        elif self.tipo_cores == 'pastel':
            return self.cores_pastel
        elif self.tipo_cores == 'gothic':
            return self.cores_gothic
        else:  # 'all'
            return {**self.cores_normais, **self.cores_pastel, **self.cores_gothic}

    # Modais para edição
    class EditModal(Modal):
        def __init__(self, cog, field, title, label, placeholder, interaction, current_value=""):
            super().__init__(title=title)
            self.cog = cog
            self.field = field
            self.interaction = interaction
            self.input = TextInput(label=label, placeholder=placeholder, style=discord.TextStyle.paragraph, required=True, default=current_value)
            self.add_item(self.input)

        async def on_submit(self, interaction: discord.Interaction):
            value = self.input.value
            if self.field == 'color':
                try:
                    setattr(self.cog, f"embed_{self.field}", int(value, 16))
                except ValueError:
                    await interaction.response.send_message("Cor inválida. Use formato hex (ex: 000000).", ephemeral=True)
                    return
            else:
                setattr(self.cog, f"embed_{self.field}", value)
            
            self.cog.save_config()  # Salva configurações no MongoDB após alteração
            
            # Tenta atualizar o embed preview na resposta original ephemeral
            try:
                embed = self.cog.create_preview_embed()
                await self.interaction.edit_original_response(embed=embed, view=self.cog.ConfigView(self.cog, self.interaction))
                await interaction.response.send_message("Configuração atualizada!", ephemeral=True)
            except (discord.errors.InteractionResponded, discord.errors.NotFound, AttributeError):
                await interaction.response.send_message("A interação expirou (possivelmente após reinicialização do bot). Reabra o painel com /config_cores.", ephemeral=True)

    # View para configuração com botões
    class ConfigView(View):
        def __init__(self, cog, interaction):
            super().__init__(timeout=None)
            self.cog = cog
            self.interaction = interaction

        @discord.ui.button(label="Editar Título", style=discord.ButtonStyle.primary)
        async def edit_title(self, interaction: discord.Interaction, button: Button):
            modal = self.cog.EditModal(self.cog, "title", "Editar Título", "Novo Título", "Digite o título...", self.interaction, current_value=self.cog.embed_title)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Editar Descrição", style=discord.ButtonStyle.primary)
        async def edit_description(self, interaction: discord.Interaction, button: Button):
            modal = self.cog.EditModal(self.cog, "description", "Editar Descrição", "Nova Descrição", "Digite a descrição...", self.interaction, current_value=self.cog.embed_description)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Editar Cor", style=discord.ButtonStyle.primary)
        async def edit_color(self, interaction: discord.Interaction, button: Button):
            current_color = f"{self.cog.embed_color:06X}"
            modal = self.cog.EditModal(self.cog, "color", "Editar Cor", "Nova Cor (hex)", "Ex: 000000", self.interaction, current_value=current_color)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Editar Footer", style=discord.ButtonStyle.primary)
        async def edit_footer(self, interaction: discord.Interaction, button: Button):
            modal = self.cog.EditModal(self.cog, "footer", "Editar Footer", "Novo Footer", "Digite o footer...", self.interaction, current_value=self.cog.embed_footer)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Editar Thumbnail", style=discord.ButtonStyle.primary)
        async def edit_thumbnail(self, interaction: discord.Interaction, button: Button):
            current_thumb = self.cog.embed_thumbnail or ""
            modal = self.cog.EditModal(self.cog, "thumbnail", "Editar Thumbnail", "Nova URL", "Digite a URL da imagem...", self.interaction, current_value=current_thumb)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Editar Imagem", style=discord.ButtonStyle.primary)
        async def edit_image(self, interaction: discord.Interaction, button: Button):
            current_image = self.cog.embed_image or ""
            modal = self.cog.EditModal(self.cog, "image", "Editar Imagem", "Nova URL", "Digite a URL da imagem...", self.interaction, current_value=current_image)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Mudar Tipo de Cores", style=discord.ButtonStyle.secondary)
        async def change_type(self, interaction: discord.Interaction, button: Button):
            modal = self.cog.EditModal(self.cog, "tipo_cores", "Mudar Tipo de Cores", "Novo Tipo", "normais, pastel, gothic ou all", self.interaction, current_value=self.cog.tipo_cores)
            await interaction.response.send_modal(modal)

    def create_preview_embed(self):
        embed = discord.Embed(title=self.embed_title, description=self.embed_description, color=self.embed_color)
        if self.embed_footer:
            embed.set_footer(text=self.embed_footer)
        if self.embed_thumbnail:
            embed.set_thumbnail(url=self.embed_thumbnail)
        if self.embed_image:
            embed.set_image(url=self.embed_image)
        return embed

    # Slash command para configurar as cores (apenas admins, ephemeral com preview)
    @app_commands.command(name="config_cores", description="Abre o painel de configuração das cores com preview (ephemeral)")
    async def config_cores(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Você precisa ser administrador para usar este comando.", ephemeral=True)
            return
        
        embed = self.create_preview_embed()
        view = self.ConfigView(self, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Slash command para abrir o painel de cores (persistente, não ephemeral)
    @app_commands.command(name="painel_cores", description="Abre o painel de seleção de cores no canal atual")
    async def painel_cores(self, interaction: discord.Interaction):
        cores = self.get_cores_ativas()
        if not cores:
            await interaction.response.send_message("Nenhuma cor disponível. Configure com /config_cores.", ephemeral=True)
            return
        
        embed = self.create_preview_embed()
        view = PainelCores(self)
        await interaction.channel.send(embed=embed, view=view)  # Envia no canal, persistente
        await interaction.response.send_message("Painel de cores enviado no canal!", ephemeral=True)  # Confirmação privada

async def setup(bot):
    await bot.add_cog(Color(bot))