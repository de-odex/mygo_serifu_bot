from pathlib import Path

from loguru import logger
from watchfiles import Change, DefaultFilter, awatch
from whoosh.analysis import NgramWordAnalyzer
from whoosh.fields import NUMERIC, TEXT, Schema
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import FieldAliasPlugin, MultifieldParser, QueryParser
from whoosh.searching import Searcher

from .constants import assets_path, project_path
from .media import Episode, gen_metadata

schema = Schema(
    show=TEXT(stored=True),
    episode=NUMERIC(stored=True),
    filename=TEXT(stored=True),
    name=TEXT(stored=True),
    text=TEXT(
        stored=True,
        analyzer=NgramWordAnalyzer(minsize=2, maxsize=5),
        phrase=False,
    ),
    start=NUMERIC(stored=True),
    end=NUMERIC(stored=True),
)

index_path = project_path / "index"


def cache_add(writer, show_name, episode: Episode):
    logger.debug(f"adding to cache: {show_name} {episode.filename}")
    for line in episode.lines:
        # logger.trace(f"writing to index: {line.text}")
        writer.add_document(
            **{
                "show": show_name,
                "episode": episode.index,
                "filename": episode.filename,
                "name": line.name,
                "text": line.text,
                "start": line.start,
                "end": line.end,
            }
        )


def cache_del(writer, show_name, filename):
    logger.debug(f"deleting from cache: {show_name} {filename}")
    query = QueryParser("text", ix.schema).parse(
        f'show:"{show_name}" filename:{filename}'
    )
    writer.delete_by_query(query)


def gen_cache():
    logger.info("Generating index")
    data = gen_metadata()
    index_path.mkdir(parents=True, exist_ok=True)
    ix = create_in(index_path, schema)
    with ix.writer() as writer:
        for show_name, show in data.items():
            for episode in show:
                logger.debug(episode.filename)
                cache_add(writer, show_name, episode)
    return ix


ix = None
if exists_in(index_path):
    logger.info(f"Search index found in {index_path}")
    ix = open_dir(index_path)
else:
    logger.info(f"Search index not found in {index_path}, creating")
    ix = gen_cache()


parser = MultifieldParser(["show", "name", "text"], ix.schema)
parser.add_plugin(
    FieldAliasPlugin(
        {
            "show": ["series", "s"],
            "episode": ["ep", "e"],
            "name": ["actor", "n"],
        }
    )
)


# return empty list if line doesn't exist
@logger.catch(default=[])
def search(searcher: Searcher, query: str):
    logger.debug(f"searching {query!r}")
    logger.trace(query)
    query = parser.parse(query)
    logger.trace(query)
    result = searcher.search(query)
    logger.trace(list(result))
    return result


class MkvFilter(DefaultFilter):
    allowed_extensions = ".mkv"

    def __call__(self, change: Change, path: str) -> bool:
        return super().__call__(change, path) and path.endswith(self.allowed_extensions)


async def watch():
    logger.info(f"Watching files in {assets_path}")
    async for changes in awatch(assets_path, watch_filter=MkvFilter()):
        for change, path in changes:
            if change not in [Change.modified, Change.deleted]:
                continue
            path = Path(path)
            show = path.parent.name
            logger.debug(f"change seen: {change} {path}")
            with ix.writer() as writer:
                if change == Change.modified:
                    ep = Episode.from_path(path)
                    cache_add(writer, show, ep)
                elif change == Change.deleted:
                    cache_del(writer, show, path.name)
