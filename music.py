import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 유튜브 DL 옵션
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# 봇이 명령어를 받으면 실행하는 부분
@bot.event
async def on_ready():
    print("시작되었습니다")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("노래봇"))
    await bot.tree.sync()  # 슬래시 커맨드 등록

@bot.tree.command(name="재생", description='url을 입력하세요')
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.send_message("재생 중...")
    if not interaction.user.voice:
        await interaction.response.send_message("먼저 음성 채널에 입장해야 합니다.")
        return
    
    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not voice_client:
        voice_client = await channel.connect()

    async with interaction.channel.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
    
    await interaction.followup.send(f'재생 중: [{player.title}]({url})')

@bot.tree.command(name="종료", description='음악을 멈추고 봇을 퇴장시킵니다.')
async def stop(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message("음악을 멈추고 봇이 퇴장했습니다.")
    else:
        await interaction.response.send_message("봇이 현재 음성 채널에 연결되어 있지 않습니다.")


# 토큰으로 봇 실행
access_token = os.environ("BOT_TOKEN")
bot.run(access_token)
