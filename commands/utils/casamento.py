import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import asyncio

class ProposeView(View):
    def __init__(self, proposer, target, cog, message):
        super().__init__(timeout=300)  # 5 minutos
        self.proposer = proposer
        self.target = target
        self.cog = cog
        self.message = message

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.green, emoji="💍")
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.target:
            await interaction.response.send_message("Apenas o destinatário pode responder.", ephemeral=True)
            return
        
        # Adiciona casamento
        self.cog.add_marriage(self.proposer.id, self.target.id)
        
        # Embed de anúncio
        embed = discord.Embed(
            title="Novo Casamento! 💍",
            description=f"{self.proposer.mention} agora é casado com {self.target.mention}!",
            color=0xFF69B4
        )
        await interaction.channel.send(embed=embed)
        
        # Edita a mensagem original
        expired_embed = discord.Embed(
            title="Proposta Aceita! 💍",
            description=f"{self.target.mention} aceitou a proposta de {self.proposer.mention}!",
            color=0x00FF00
        )
        await self.message.edit(embed=expired_embed, view=None)
        
        await interaction.response.send_message("Casamento realizado!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.red, emoji="💔")
    async def decline(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.target:
            await interaction.response.send_message("Apenas o destinatário pode responder.", ephemeral=True)
            return
        
        # Edita a mensagem original
        declined_embed = discord.Embed(
            title="Proposta Recusada 💔",
            description=f"{self.target.mention} recusou a proposta de {self.proposer.mention}.",
            color=0xFF0000
        )
        await self.message.edit(embed=declined_embed, view=None)
        
        await interaction.response.send_message("Proposta recusada.", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        # Edita a mensagem para expirado
        expired_embed = discord.Embed(
            title="Proposta Expirada ⏰",
            description="A proposta de casamento expirou sem resposta.",
            color=0xFFFF00
        )
        try:
            await self.message.edit(embed=expired_embed, view=None)
        except:
            pass

class Casamento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        self.db_name = "discord_bot"  # Nome do banco
        self.collection_name = "marriages"
        self.client = None
        self.collection = None
        self.connect_mongo()

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

    def get_marriage(self, user_id):
        if self.collection is not None:
            return self.collection.find_one({"$or": [{"user1": user_id}, {"user2": user_id}]})
        return None

    def add_marriage(self, user1, user2):
        if self.collection is not None:
            self.collection.insert_one({"user1": user1, "user2": user2})

    def remove_marriage(self, user_id):
        if self.collection is not None:
            self.collection.delete_one({"$or": [{"user1": user_id}, {"user2": user_id}]})

    def get_all_marriages(self):
        if self.collection is not None:
            return list(self.collection.find())
        return []

    @app_commands.command(name="casar", description="Casa-se com um usuário")
    @app_commands.describe(user="Usuário para se casar")
    async def casar(self, interaction: discord.Interaction, user: discord.Member):
        if user.id == interaction.user.id:
            await interaction.response.send_message("Você não pode se casar consigo mesmo.", ephemeral=True)
            return
        
        if self.get_marriage(interaction.user.id):
            await interaction.response.send_message("Você já está casado.", ephemeral=True)
            return
        
        if self.get_marriage(user.id):
            embed = discord.Embed(
                title="Casamento Impossível 💔",
                description=f"{user.mention} já é casado!",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Envia proposta no canal
        embed = discord.Embed(
            title="Proposta de Casamento 💍",
            description=f"{interaction.user.mention} quer se casar com {user.mention}! O que você diz?",
            color=0xFF69B4
        )
        view = ProposeView(interaction.user, user, self, None)  # Message será definido após enviar
        message = await interaction.channel.send(embed=embed, view=view)
        view.message = message  # Define a message para edição
        
        await interaction.response.send_message("Proposta enviada no canal!", ephemeral=True)

    @app_commands.command(name="divorciar", description="Divorcia-se do parceiro atual")
    async def divorciar(self, interaction: discord.Interaction):
        marriage = self.get_marriage(interaction.user.id)
        if not marriage:
            await interaction.response.send_message("Você não está casado.", ephemeral=True)
            return
        
        partner_id = marriage["user2"] if marriage["user1"] == interaction.user.id else marriage["user1"]
        partner = interaction.guild.get_member(partner_id)
        
        # Remove casamento
        self.remove_marriage(interaction.user.id)
        
        # Embed de anúncio
        embed = discord.Embed(
            title="Divórcio! 💔",
            description=f"{interaction.user.mention} se divorciou de {partner.mention if partner else 'seu parceiro'}!",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="casamentos", description="Lista todos os casamentos atuais")
    async def casamentos(self, interaction: discord.Interaction):
        marriages = self.get_all_marriages()
        if not marriages:
            embed = discord.Embed(
                title="Casamentos Atuais",
                description="Nenhum casamento registrado.",
                color=0x00FF00
            )
        else:
            description = "\n".join(
                f"{interaction.guild.get_member(m['user1']).mention if interaction.guild.get_member(m['user1']) else f'<@{m["user1"]}>'} 💕 {interaction.guild.get_member(m['user2']).mention if interaction.guild.get_member(m['user2']) else f'<@{m["user2"]}>'}"
                for m in marriages
            )
            embed = discord.Embed(
                title="Casamentos Atuais",
                description=description,
                color=0x010202
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Casamento(bot))