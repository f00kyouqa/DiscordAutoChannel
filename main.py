import discord
from discord.ext import commands
import aiohttp
import json
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta

# 環境変数の読み込み
load_dotenv()

# 設定
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Intents の設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

class OllamaManager:
    """Ollama API とのインタフェース"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
    
    async def generate(self, prompt: str) -> str:
        """Ollama に質問を送信して回答を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "").strip()
                    else:
                        print(f"Ollama API error: {response.status}")
                        return None
        except asyncio.TimeoutError:
            print("Ollama API timeout")
            return None
        except Exception as e:
            print(f"Ollama API error: {e}")
            return None
    
    async def suggest_channels(self, guild_name: str, existing_channels: list, conversation_context: str) -> list:
        """
        会話の文脈から新しく作成すべきチャンネルを提案
        
        Args:
            guild_name: サーバー名
            existing_channels: 既存のチャンネル名リスト
            conversation_context: 会話の文脈
        
        Returns:
            提案チャンネルのリスト (dict: {name, description, reason})
        """
        prompt = f"""
You are a Discord server management assistant. Based on the conversation context and existing channels, 
suggest new channels that should be created for this Discord server.

Guild: {guild_name}
Existing channels: {', '.join(existing_channels)}

Conversation context: {conversation_context}

Please suggest 2-5 new channels that would be useful. For each channel, provide:
1. Channel name (lowercase, use hyphens for spaces)
2. Short description
3. Reason why it's needed

Format your response as JSON array with objects like:
[
  {{"name": "channel-name", "description": "...", "reason": "..."}},
  ...
]

Only return valid JSON, no other text.
"""
        response = await self.generate(prompt)
        if not response:
            return []
        
        try:
            # JSON 部分を抽出
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                suggestions = json.loads(json_str)
                return suggestions
        except json.JSONDecodeError:
            print(f"Failed to parse Ollama response: {response}")
        
        return []
    
    async def analyze_channels_for_cleanup(self, channels_info: str) -> dict:
        """
        チャンネルの活動状況を分析し、整理の対象を提案
        
        Args:
            channels_info: チャンネル情報 (名前、最後のメッセージ日時など)
        
        Returns:
            整理対象チャンネル情報
        """
        prompt = f"""
You are a Discord server management assistant. Analyze the following channels and suggest which ones 
could be archived or deleted due to inactivity or redundancy.

Channels information:
{channels_info}

For each channel that should be cleaned up, provide:
1. Channel name
2. Reason for cleanup
3. Recommended action (archive, delete, or reorganize)

Format your response as JSON array:
[
  {{"name": "channel-name", "reason": "...", "action": "archive|delete|reorganize"}},
  ...
]

Only return valid JSON, no other text.
"""
        response = await self.generate(prompt)
        if not response:
            return {}
        
        try:
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                suggestions = json.loads(json_str)
                return suggestions
        except json.JSONDecodeError:
            print(f"Failed to parse Ollama response: {response}")
        
        return {}

# グローバル Ollama マネージャー
ollama = OllamaManager(OLLAMA_API_URL, OLLAMA_MODEL)

@bot.event
async def on_ready():
    """Bot が起動時に実行"""
    print(f"{bot.user} がログインしました")
    print(f"接続中のサーバー数: {len(bot.guilds)}")

@bot.command(name="suggest_channels")
@commands.has_permissions(administrator=True)
async def suggest_channels_command(ctx, *, context: str = None):
    """
    チャンネル作成を提案するコマンド
    使用例: !suggest_channels We need better organization for our projects
    """
    if not context:
        await ctx.send("❌ 提案の根拠となるテキストを入力してください。\n例: `!suggest_channels We need channels for project management`")
        return
    
    # 入力を制限（Ollama への負荷軽減）
    if len(context) > 500:
        context = context[:500]
    
    async with ctx.typing():
        guild = ctx.guild
        existing_channels = [ch.name for ch in guild.channels if isinstance(ch, discord.TextChannel)]
        
        suggestions = await ollama.suggest_channels(
            guild.name,
            existing_channels,
            context
        )
        
        if not suggestions:
            await ctx.send("⚠️ チャンネルの提案を生成できませんでした。")
            return
        
        # 提案をメッセージとして表示
        embed = discord.Embed(
            title="🚀 チャンネル作成提案",
            description=f"提案の根拠: {context}",
            color=discord.Color.blue()
        )
        
        for i, suggestion in enumerate(suggestions, 1):
            embed.add_field(
                name=f"{i}. #{suggestion.get('name', 'unknown')}",
                value=f"**説明:** {suggestion.get('description', 'N/A')}\n**理由:** {suggestion.get('reason', 'N/A')}",
                inline=False
            )
        
        view = ChannelCreationView(ctx.author, suggestions, guild, ollama)
        await ctx.send(embed=embed, view=view)

@bot.command(name="cleanup_analysis")
@commands.has_permissions(administrator=True)
async def cleanup_analysis_command(ctx):
    """
    チャンネル整理の分析を実行
    """
    async with ctx.typing():
        guild = ctx.guild
        
        # チャンネル情報を収集
        channels_info = []
        for channel in guild.text_channels:
            try:
                # 最後のメッセージを取得
                async for message in channel.history(limit=1):
                    last_message_date = message.created_at
                    break
                else:
                    last_message_date = channel.created_at
                
                days_inactive = (datetime.utcnow() - last_message_date).days
                channels_info.append({
                    'name': channel.name,
                    'members': len(channel.members),
                    'inactive_days': days_inactive,
                    'created_at': channel.created_at.isoformat()
                })
            except discord.Forbidden:
                continue
        
        # JSON 形式に変換
        channels_json = json.dumps(channels_info, indent=2, default=str)
        
        # Ollama で分析
        cleanup_suggestions = await ollama.analyze_channels_for_cleanup(channels_json)
        
        if not cleanup_suggestions:
            await ctx.send("✅ 整理の対象となるチャンネルはありません。")
            return
        
        # 結果を表示
        embed = discord.Embed(
            title="🧹 チャンネル整理提案",
            color=discord.Color.orange()
        )
        
        for suggestion in cleanup_suggestions:
            action_emoji = {
                'archive': '📦',
                'delete': '🗑️',
                'reorganize': '🔄'
            }.get(suggestion.get('action', ''), '❓')
            
            embed.add_field(
                name=f"{action_emoji} #{suggestion.get('name')}",
                value=f"**理由:** {suggestion.get('reason')}\n**対応:** {suggestion.get('action')}",
                inline=False
            )
        
        await ctx.send(embed=embed)

@bot.command(name="create_channel")
@commands.has_permissions(manage_channels=True)
async def create_channel_command(ctx, channel_name: str, *, description: str = ""):
    """
    チャンネルを作成するコマンド
    使用例: !create_channel projects Project management channel
    """
    try:
        # チャンネル名の検証
        if not channel_name or len(channel_name) > 32:
            await ctx.send("❌ チャンネル名は1～32文字である必要があります。")
            return
        
        # チャンネル作成
        new_channel = await ctx.guild.create_text_channel(
            channel_name,
            topic=description if description else None
        )
        
        embed = discord.Embed(
            title="✅ チャンネル作成完了",
            description=f"チャンネル {new_channel.mention} を作成しました。",
            color=discord.Color.green()
        )
        if description:
            embed.add_field(name="説明", value=description)
        
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ チャンネル作成の権限がありません。")
    except discord.HTTPException as e:
        await ctx.send(f"❌ エラーが発生しました: {e}")

@bot.command(name="auto_organize")
@commands.has_permissions(manage_channels=True)
async def auto_organize_command(ctx):
    """
    チャンネルを自動整理（カテゴリ分類）
    """
    async with ctx.typing():
        guild = ctx.guild
        
        # カテゴリの作成/整理ロジック
        default_categories = {
            'general': ['📢 general', '💬 announcements', '📝 rules'],
            'community': ['👋 introductions', '🤝 off-topic', '🎮 games'],
            'projects': ['📋 projects', '🛠️ dev', '🐛 bugs', '✨ features'],
            'media': ['📸 images', '📹 videos', '🎵 music']
        }
        
        existing_categories = {cat.name: cat for cat in guild.categories}
        
        for category_name in default_categories.keys():
            if category_name not in existing_categories:
                try:
                    await guild.create_category(category_name)
                except discord.Forbidden:
                    continue
        
        await ctx.send("✅ サーバーの自動整理を実行しました。")

class ChannelCreationView(discord.ui.View):
    """チャンネル作成提案の UI"""
    
    def __init__(self, author: discord.User, suggestions: list, guild: discord.Guild, ollama_manager):
        super().__init__(timeout=300)
        self.author = author
        self.suggestions = suggestions
        self.guild = guild
        self.ollama = ollama_manager
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ユーザー検証"""
        if interaction.user != self.author:
            await interaction.response.send_message("❌ このボタンは実行者のみが使用できます。", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="すべて作成", style=discord.ButtonStyle.green)
    async def create_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """すべてのチャンネルを作成"""
        await interaction.response.defer()
        
        created_channels = []
        for suggestion in self.suggestions:
            try:
                channel = await self.guild.create_text_channel(
                    suggestion.get('name', 'new-channel'),
                    topic=suggestion.get('description', '')
                )
                created_channels.append(channel.mention)
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Error creating channel: {e}")
        
        await interaction.followup.send(
            f"✅ {len(created_channels)}個のチャンネルを作成しました:\n" + ", ".join(created_channels)
        )
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """キャンセル"""
        await interaction.response.defer()
        self.stop()

def main():
    """Bot 起動"""
    if not DISCORD_TOKEN:
        print("❌ エラー: DISCORD_TOKEN が設定されていません。")
        print(".env ファイルに DISCORD_TOKEN を設定してください。")
        return
    
    print("🤖 Discord Auto Channel Bot を起動しています...")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
