import asyncio
import datetime
import inspect
import io
import logging
import os
import shlex
from datetime import datetime
from pathlib import Path

import discord
import ffmpeg
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from loguru import logger

from .constants import assets_path, project_path

self_path = Path(__file__)


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


logger.add(
    (project_path / "logs" / self_path.stem).with_suffix(".log"),
    rotation="00:00",
    retention="7 days",
    compression="lzma",
)
discord.utils.setup_logging(
    handler=InterceptHandler(),
    root=False,
)


if Path("proto.env").is_file():
    logger.warning("loading proto.env as environment file...")
    load_dotenv("proto.env")
else:
    load_dotenv()


from . import search
from .search import watch

error_gif_link = "https://raw.githubusercontent.com/eason102/mygo_serifu_bot/refs/heads/main/src/error.gif"


intents = discord.Intents.default()
bot = commands.AutoShardedBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    server_count = len(bot.guilds)
    logger.info(f"Online: {bot.user} | in {server_count} servers")


def _humanise(ms: int) -> str:
    seconds = ms // 1000
    minutes = seconds // 60
    seconds %= 60

    return f"{minutes}m{seconds}s"


async def autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    with search.ix.searcher() as searcher:  # type: ignore
        results = search.search(searcher, current)
        data: list[app_commands.Choice[str]] = []

        for index, entry in enumerate(results):
            name = "("
            if entry["show"] == "mygo":
                name += "MyGO "
            elif entry["show"] == "ave mujica":
                name += "Ave Mujica "
            name += f"Ep{entry['episode']} {_humanise(entry['start'])}) "  # type: ignore
            if entry["name"]:
                name += f"{entry['name']}: "
            name += f"{entry['text']}"

            value = f"s:'{entry['show']}' e:'{entry['episode']}' start:{entry['start']}"

            name = (name[:95] + "(...)") if len(name) > 100 else name
            data.append(discord.app_commands.Choice(name=name, value=value))

            if index >= 25:
                break

        return data

    return autocomplete


def ffmpeg_image(
    show: str,
    episode: str,
    start_offset_ms: int,
):
    filename = str((assets_path / show / episode).relative_to(Path.cwd()))
    pipeline = (
        ffmpeg.input(filename=filename, ss=f"{start_offset_ms}ms")
        .subtitles(filename=filename, stream_index=0)
        .output(
            filename="pipe:",
            ss=f"{start_offset_ms}ms",
            vframes=1,
            f="image2",
            vcodec="png",
        )
        .global_args(copyts=True, loglevel="error")
    )
    logger.debug(shlex.join(pipeline.compile()))
    buffer, error = pipeline.run(capture_stdout=True)
    return buffer, error


def ffmpeg_gif(
    show: str,
    episode: str,
    start_ms: int,
    duration: int,
):
    start_str = f"{start_ms}ms"
    duration_str = f"{duration}ms"

    filename = str((assets_path / show / episode).relative_to(Path.cwd()))
    in_pipe = (
        ffmpeg.input(filename=filename, ss=start_str, t=duration_str)
        .scale(w=-1, h=432)
        .subtitles(filename=filename, stream_index=0)
        # .trim(start=0, end=f"{duration}ms")
        .split()
    )

    palettegen = (
        in_pipe.video(0)
        # .trim(start=0, end=f"{duration}ms")
        .palettegen(stats_mode="diff")
    )

    pipeline = (
        in_pipe.video(1)
        .paletteuse(
            palettegen,
            dither="bayer",
            diff_mode="rectangle",
        )
        .output(
            filename="pipe:1",
            ss=start_str,
            t=duration_str,
            f="gif",
            vcodec="gif",
        )
        .global_args(copyts=True, loglevel="error")
    )
    logger.debug(shlex.join(pipeline.compile()))
    buffer, error = pipeline.run(capture_stdout=True)
    return buffer, error


async def _error(
    interaction: discord.Interaction,
    exc: app_commands.AppCommandError,
):
    command = interaction.command
    logger.exception(f"An error occurred in {command.name}")
    description: str = "An unexpected error has occurred."
    if isinstance(exc, app_commands.CommandInvokeError):
        match exc.original:
            case ValueError() as exc_orig:
                description = str(exc_orig)
            case ffmpeg.FFMpegExecuteError():
                description = "Something happened to FFmpeg..."
            case _:
                # Don't report exception message
                pass

    embed = discord.Embed(
        title="❌Error",
        description=description,
        color=discord.Color.red(),
    )
    embed.set_image(url=error_gif_link)

    if "msg" in interaction.extras:
        msg = interaction.extras["msg"]
        await msg.edit(embed=embed)
        # logger.info(
        #     # f"Server ID: {interaction.guild_id} Line: {result['text']} Error: {error}"
        #     f"Server ID: {interaction.guild_id}"
        # )
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


bot.tree.on_error = _error


# ===== image commands =====

image_describe = dict(
    text="The line to search for",
    second="Offset (in seconds) - default 0.75s",
)


@bot.tree.command(
    name="avemygo",
    description="Search for MyGO and Ave Mujica lines",
)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.autocomplete(text=autocomplete)
@app_commands.describe(**image_describe)
async def avemygo(
    interaction: discord.Interaction,
    text: str,
    second: float = 0.75,
):
    logger.info(f"Server ID: {interaction.guild_id} Request: {text}")

    result = None
    with search.ix.searcher() as searcher:  # type: ignore
        result = search.search(searcher, text)
        if len(result) == 0:
            raise ValueError("No lines were found, please try again.")

        result = result[0].fields()  # type: ignore

    await interaction.response.defer()

    start_time = datetime.now()

    start_ms = result["start"]  # type: ignore
    start_offset_ms = max(0, start_ms + int(second * 1000))  # type: ignore
    buffer, _ = await asyncio.to_thread(
        ffmpeg_image,
        result["show"],  # type: ignore
        result["filename"],  # type: ignore
        start_offset_ms,
    )

    await interaction.followup.send(
        file=discord.File(
            fp=io.BytesIO(buffer),
            filename=f"{result['show']}-Ep{result['episode']}-{start_offset_ms}.png",
        )
    )
    end_time = datetime.now()

    run_time = end_time - start_time
    total_seconds = run_time.total_seconds()
    logger.info(
        f"Server ID: {interaction.guild_id} Line: {result['text']} Time taken: {total_seconds:.3f} seconds"
    )


# ===== gif commands =====

gif_describe = dict(
    text="The line to search for",
    duration_limit="Max GIF duration (in seconds) - default 5s, max 10s.",
    spoiler="Spoiler the GIF",
)


@bot.tree.command(
    name="avemygogif",
    description="Search for MyGO and Ave Mujica lines and create GIFs",
)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.autocomplete(text=autocomplete)
@app_commands.describe(**gif_describe)
async def avemygogif(
    interaction: discord.Interaction,
    text: str,
    duration_limit: float = 5.0,
    spoiler: bool = False,
):
    logger.info(f"Server ID: {interaction.guild_id} Request: {text}")

    # TODO: hardcoded
    max_dur_limit = 10.0
    if duration_limit > max_dur_limit:
        raise ValueError(f"The maximum duration for GIF creation is {max_dur_limit}s.")

    result = None
    with search.ix.searcher() as searcher:  # type: ignore
        result = search.search(searcher, text)
        if len(result) == 0:
            raise ValueError("No lines were found, please try again.")

        result = result[0].fields()  # type: ignore

    await interaction.response.defer()
    embed = discord.Embed(
        title="GIF is being produced...",
        description="Depending on the complexity of the picture, it may take some time.",
        color=discord.Color.green(),
    )
    # wait=True needed for type checker to use correct return type
    msg = interaction.extras["msg"] = await interaction.followup.send(
        wait=True, embed=embed, ephemeral=True
    )

    start_time = datetime.now()

    duration_limit = int(duration_limit * 1000)
    start_ms = result["start"]  # type: ignore
    end_ms = result["end"]  # type: ignore
    duration = min(end_ms - start_ms, duration_limit)  # type: ignore
    buffer2, _ = await asyncio.to_thread(
        ffmpeg_gif,
        result["show"],  # type: ignore
        result["filename"],  # type: ignore
        start_ms,  # type: ignore
        duration,
    )

    await msg.edit(
        embed=None,
        attachments=[
            discord.File(
                fp=io.BytesIO(buffer2),
                filename=f"{result['show']}-Ep{result['episode']}-{result['start']}-{duration_limit}.gif",
                spoiler=spoiler,
            )
        ],
    )
    end_time = datetime.now()

    run_time = end_time - start_time
    total_seconds = run_time.total_seconds()
    logger.info(
        f"Server ID: {interaction.guild_id} Line: {result['text']} Duration: {duration}ms GIF processing time: {total_seconds:.3f}s"
    )


# ===== async running =====


async def bot_run():
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        raise OSError("missing required environment variable DISCORD_TOKEN")

    async with bot:
        await bot.start(DISCORD_TOKEN, reconnect=True)


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(bot_run())
        tg.create_task(watch())

        logger.info("Started bot")
    logger.info("Finished bot")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
