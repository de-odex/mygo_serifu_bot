import re
from dataclasses import dataclass, field
from pathlib import Path

import ffmpeg
from loguru import logger
from pysubs2 import SSAFile

from .constants import assets_path

self_path = Path(__file__)


@dataclass
class Episode:
    @dataclass
    class Line:
        start: int
        end: int
        name: str
        text: str

    filename: str
    lines: list[Line] = field(default_factory=list)

    @property
    def index(self):
        return int(re.match(r"Episode S\d+E(\d+)", self.filename).group(1))

    @classmethod
    def from_path(cls, path: Path) -> "Episode":
        episode = cls(filename=path.name)

        # extract subtitles
        sub_probe = ffmpeg.probe(
            path,
            select_streams="s",
            show_entries="stream=index:stream_tags=language",
        )

        # TODO: maybe add detection for signs only subs
        subtitle_streams = [
            stream
            for stream in sub_probe.get("streams", [])
            if stream.get("tags", {}).get("language") == "eng"
        ]
        if not subtitle_streams:
            raise ValueError("No English subtitles found")

        # I AM LAZY I AM SO SORRY ABOUT THIS UGLY BLOCK
        sub_files: list[bytes] = []
        for stream in subtitle_streams:
            stream_index = stream["index"]
            out, _ = (
                ffmpeg.input(path)
                .output(filename="pipe:1", map=f"0:{stream_index}", f="ass")
                .global_args(n=True, loglevel="error")
                .run(capture_stdout=True)
            )
            sub_files.append(out)

        # parse subtitles
        for sub_file in sub_files:
            sub = SSAFile.from_string(sub_file.decode("utf-8"))
            for line in sub:
                # filter out empty lines
                if line.text == "":
                    continue
                # filter out non-dialogue
                if line.name.startswith("text"):
                    continue

                episode.lines.append(
                    Episode.Line(
                        start=line.start,
                        end=line.end,
                        name=line.name,
                        text=line.plaintext.replace("\n ", " ")
                        .replace(" \n", " ")
                        .replace("\n", " "),
                    )
                )
        return episode


def gen_metadata() -> dict[str, list[Episode]]:
    """Generate the video and subtitle metadata if not found."""
    logger.info("Generating video metadata")
    shows: dict[str, list[Episode]] = {
        "mygo": [],
        "ave mujica": [],
    }

    for show_name, show in shows.items():
        show_path = assets_path / show_name

        for episode_path in show_path.glob("*.mkv"):
            logger.debug(episode_path)
            try:
                show.append(Episode.from_path(episode_path))
            except ValueError:
                logger.exception("Handled exception")
                continue
        logger.trace(f"{show_name} {len(show)=}")
    return shows
