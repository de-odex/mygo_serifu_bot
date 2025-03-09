import asyncio
import datetime
import io
import json
import os
from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import discord
import ffmpeg
import pysubs2
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from loguru import logger

from .constants import assets_path, project_path

self_path = Path(__file__)

show_names = [
    "mygo",
    "ave mujica",
]


def generate_metadata():
    """Generate the video and subtitle metadata if not found."""
    # TODO: megafunction, break up
    # TODO: logging

    metadata = {}
    for show_name in show_names:
        show_path = assets_path / show_name
        show_metadata = metadata[show_name] = {}

        for episode_path in show_path.glob("*.mkv"):
            # extract subtitles

            video_probe = ffmpeg.probe(
                episode_path,
                select_streams="V",
                show_entries="stream=index:stream=avg_frame_rate",
            )
            sub_probe = ffmpeg.probe(
                episode_path,
                select_streams="s",
                show_entries="stream=index:stream_tags=language",
            )

            video_streams = video_probe.get("streams", [])
            if not video_streams:
                logger.error("No video found")
                continue
            # TODO: maybe add detection for signs only subs
            subtitle_streams = [
                stream
                for stream in sub_probe.get("streams", [])
                if stream.get("tags", {}).get("language") == "eng"
            ]
            if not subtitle_streams:
                logger.error("No English subtitles found")
                continue
            episode_metadata = show_metadata[episode_path.name] = {}
            streams_metadata = episode_metadata["streams"] = {}

            for stream in video_streams:
                stream_index = stream["index"]
                streams_metadata[stream_index] = {
                    "type": "video",
                    "avg_frame_rate": stream["avg_frame_rate"],
                }

            # I AM LAZY I AM SO SORRY ABOUT THIS UGLY BLOCK
            for stream in subtitle_streams:
                stream_index = stream["index"]
                output_file = (
                    episode_path.parent / f"{episode_path.stem}_{stream_index}.ass"
                )
                out, err = (
                    ffmpeg.input(episode_path)
                    .output(str(output_file), map=f"0:{stream_index}")
                    .global_args("-y", "-loglevel", "error")
                    .run(capture_stdout=True, capture_stderr=True)
                )
                if out:
                    logger.info(out.decode("utf-8"))
                if err:
                    logger.error(err.decode("utf-8"))
                streams_metadata[stream_index] = {
                    "type": "subtitle",
                    "filename": str(output_file.relative_to(project_path)),
                }
                logger.info(
                    f"Extracted English subtitle {stream_index} to {output_file}"
                )

            # parse subtitles
            for stream_index, stream_metadata in streams_metadata.items():
                if stream_metadata["type"] != "subtitle":
                    continue
                sub = pysubs2.load(stream_metadata["filename"])
                line_metadata = stream_metadata["lines"] = []
                for line in sub:
                    # filter out empty lines
                    if line.text == "":
                        continue
                    # filter out non-dialogue
                    if line.name.startswith("text"):
                        continue

                    line_metadata.append(
                        {
                            "start": line.start,
                            "end": line.end,
                            "name": line.name,
                            "text": line.plaintext.replace("\n", ""),
                        }
                    )

    with open(assets_path / "metadata.json", "w") as f:
        json.dump(metadata, f)


if __name__ == "__main__":
    generate_metadata()
