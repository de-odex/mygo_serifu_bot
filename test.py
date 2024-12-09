import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
    except Exception as e:
        print(e)

# 定义 Slash Command
@bot.tree.command(name="greet", description="向某人问好")
@app_commands.describe(name="选择一个名字来问候")
async def greet(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f"你好，{name}！")

# 为该命令添加参数选项
@bot.tree.command(name="choose", description="选择一个选项")
async def choose(interaction: discord.Interaction, option: str):
    await interaction.response.send_message(f"你选择了：{option}")

# 在命令中添加选项（使用选择菜单）
@bot.tree.command(name="my_option_command", description="有选择项的命令")
async def my_option_command(interaction: discord.Interaction, option: str):
    choices = ["选项1", "选项2", "选项3"]  # 选择项列表
    await interaction.response.send_message(f"你选择了：{option}")


# 启动 bot
bot.run('OTY0NDI0OTE2MzI3ODgyNzgy.GjxlFc.om4Gk3GmAJqpEBA6lCeWHymMvW_QDZlmc1rJGU')