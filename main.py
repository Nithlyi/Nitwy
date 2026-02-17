import discord
from discord.ext import commands
import os
import logging
import threading
import time
from typing import Dict
from dotenv import load_dotenv
import pymongo
from fastapi import FastAPI
import uvicorn

# Importa o handler de cogs (seu arquivo handler.py)
from handler import load_cogs

# ────────────────────────────────────────────────
# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Carrega .env
load_dotenv()

# Variáveis obrigatórias
TOKEN = os.getenv('DISCORD_TOKEN')
APPLICATION_ID = os.getenv('APPLICATION_ID')
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DATABASE_NAME', 'discordbot')

# Validação inicial
if not TOKEN:
    logger.critical("DISCORD_TOKEN não encontrado no .env")
    exit(1)
if not APPLICATION_ID:
    logger.critical("APPLICATION_ID não encontrado no .env (pegue no Developer Portal)")
    exit(1)
if not MONGO_URI:
    logger.warning("MONGO_URI não encontrado — rodando sem banco de dados")

# Conexão MongoDB (opcional)
db = None
if MONGO_URI:
    try:
        mongo_client = pymongo.MongoClient(MONGO_URI)
        mongo_client.admin.command('ping')
        db = mongo_client[DB_NAME]
        logger.info("MongoDB conectado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao conectar no MongoDB: {e}")
        db = None

# Intents necessárias
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# Classe de cooldown global por usuário (6 segundos)
class UserCooldown:
    def __init__(self, cooldown_seconds: float = 6.0):
        self.cooldown = cooldown_seconds
        self.last_used: Dict[int, float] = {}  # user_id → timestamp

    def is_on_cooldown(self, user_id: int) -> bool:
        now = time.time()
        last = self.last_used.get(user_id, 0)
        return now - last < self.cooldown

    def update(self, user_id: int):
        self.last_used[user_id] = time.time()

    def remaining(self, user_id: int) -> float:
        now = time.time()
        last = self.last_used.get(user_id, 0)
        return max(0, self.cooldown - (now - last))

cooldown_manager = UserCooldown(cooldown_seconds=6.0)

# ────────────────────────────────────────────────
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=int(APPLICATION_ID),  # converte string → int
            help_command=None
        )
        self.db = db

    async def setup_hook(self):
        # Carrega cogs via handler
        await load_cogs(self)

        # Sincronização dos slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Comandos slash sincronizados: {len(synced)} comandos")
        except Exception as e:
            logger.error(f"Erro ao sincronizar comandos: {e}")

    async def on_ready(self):
        logger.info(f"Bot online → {self.user} (ID: {self.user.id})")
        logger.info(f"Conectado a {len(self.guilds)} servidor(es)")

    # Check global de cooldown para TODOS os comandos slash
    async def on_app_command_invoke(self, interaction: discord.Interaction) -> bool:
        if cooldown_manager.is_on_cooldown(interaction.user.id):
            remaining = cooldown_manager.remaining(interaction.user.id)
            embed = discord.Embed(
                description=f"⏳ Aguarde **{remaining:.1f} segundos** antes de usar outro comando.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False  # impede o comando de rodar

        cooldown_manager.update(interaction.user.id)
        return True

    # Tratamento global de erros nos slash commands
    async def on_app_command_error(self, interaction: discord.Interaction, error):
        from discord import app_commands

        # Ignora cooldown aqui (já tratado no invoke)
        if isinstance(error, app_commands.CommandOnCooldown):
            return

        if isinstance(error, app_commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions).replace("_", " ").title()
            msg = f"Você não tem as permissões necessárias: **{perms}**"

        elif isinstance(error, app_commands.MissingRole):
            roles = ", ".join([f"<@&{rid}>" for rid in error.missing_roles])
            msg = f"Você precisa de um dos seguintes cargos: {roles}"

        elif isinstance(error, app_commands.CheckFailure):
            msg = "Você não tem permissão para usar este comando."

        else:
            # Erro inesperado → loga detalhadamente
            command_name = interaction.command.name if interaction.command else "desconhecido"
            logger.error(f"Erro no comando /{command_name}:", exc_info=error)
            msg = "Ocorreu um erro ao executar o comando. Tente novamente mais tarde."

        # Envia resposta (sempre ephemeral)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except discord.HTTPException:
            pass  # já respondido / canal deletado / etc


# Instancia o bot
bot = MyBot()

# Registra o check global de interação (cooldown)
bot.tree.interaction_check = bot.on_app_command_invoke

# Registra o handler global de erros dos slash commands
bot.tree.on_error = bot.on_app_command_error

# ────────────────────────────────────────────────
# Webserver para Render + UptimeRobot
app = FastAPI(title="Bot Keep-Alive")

@app.get("/")
async def root():
    logger.info("[DEBUG] Ping recebido na rota /")
    return {
        "status": "okay",
        "message": "funcionou"
    }

async def start_bot():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            logger.info(f"[DEBUG] Tentativa {attempt + 1} de iniciar bot...")
            await bot.start(TOKEN)
            logger.info("[DEBUG] Bot iniciado com sucesso!")
            break
        except discord.HTTPException as e:
            if e.status == 429:
                wait_time = (2 ** attempt) * 60  # Backoff: 1min, 2min, 4min, 8min, 16min
                logger.warning(f"[DEBUG] Rate limit detectado. Aguardando {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[DEBUG] Erro HTTP ao iniciar bot: {e}")
                break
        except Exception as e:
            logger.critical(f"[DEBUG] Erro ao iniciar bot: {e}")
            break
    else:
        logger.critical("[DEBUG] Falhou em todas as tentativas de iniciar o bot.")

def run_webserver():
    try:
        port = int(os.getenv("PORT", 10000))
        logger.info(f"[DEBUG] Iniciando webserver na porta {port}...")
        
        # Inicia o bot em um thread separado
        import threading
        bot_thread = threading.Thread(target=lambda: asyncio.run(start_bot()), daemon=True)
        bot_thread.start()
        logger.info("[DEBUG] Thread do bot iniciada.")
        
        # Roda o webserver
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"[DEBUG] Erro ao iniciar webserver: {e}")

# ────────────────────────────────────────────────
# Início principal
if __name__ == "__main__":
    logger.info("[DEBUG] Iniciando aplicação principal...")
    run_webserver()  # Roda o webserver e inicia o bot em thread