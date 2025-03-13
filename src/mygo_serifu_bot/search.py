import shutil
from pathlib import Path

from loguru import logger
from watchfiles import Change, DefaultFilter, awatch  # type: ignore
from whoosh.analysis import NgramWordAnalyzer  # type: ignore
from whoosh.fields import NUMERIC, TEXT, Schema  # type: ignore
from whoosh.index import Index, create_in, exists_in, open_dir  # type: ignore
from whoosh.qparser import MultifieldParser  # type: ignore
from whoosh.qparser import FieldAliasPlugin, QueryParser  # type: ignore
from whoosh.searching import Results, Searcher  # type: ignore
from whoosh.writing import IndexWriter  # type: ignore

from .constants import assets_path, project_path
from .media import Episode, gen_metadata

# TODO: remove type: ignores. holy crap whoosh needs type annotations

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


def index_add(writer: IndexWriter, show_name: str, episode: Episode):
    logger.info(f"adding to cache: {show_name} {episode.filename}")
    for line in episode.lines:
        # logger.trace(f"writing to index: {line.text}")
        writer.add_document(  # type: ignore
            **{  # type: ignore
                "show": show_name,
                "episode": episode.index,
                "filename": episode.filename,
                "name": line.name,
                "text": line.text,
                "start": line.start,
                "end": line.end,
            }
        )


def index_del(writer: IndexWriter, show_name: str, filename: str):
    logger.info(f"deleting from cache: {show_name} {filename}")
    query = QueryParser("text", ix.schema).parse(  # type: ignore
        f'show:"{show_name}" filename:{filename}'
    )
    writer.delete_by_query(query)  # type: ignore


def gen_index_full():
    logger.info("Generating index")
    data = gen_metadata()
    index_path.mkdir(parents=True, exist_ok=True)
    ix = create_in(index_path, schema)
    with ix.writer(limitmb=512) as writer:  # type: ignore
        for show_name, show in data.items():
            for episode in show:
                logger.debug(episode.filename)
                index_add(writer, show_name, episode)
    return ix


def gen_index_partial(ix: Index):
    """generate index if file not found"""
    logger.info("Generating index")
    # TODO: hardcoded
    with ix.writer(limitmb=512) as writer, ix.searcher() as searcher:  # type: ignore
        for show_name in ["mygo", "ave mujica"]:
            show_path = assets_path / show_name

            for episode_path in show_path.glob("*.mkv"):
                logger.debug(episode_path)
                # check if in index
                results = search(
                    searcher, f"show:'{show_name}' filename:'{episode_path.name}'"
                )
                if results.is_empty():
                    index_add(writer, show_name, Episode.from_path(episode_path))  # type: ignore
    return ix


@logger.catch()
def search(searcher: Searcher, query: str) -> Results:
    logger.debug(f"searching {query!r}")

    parser = MultifieldParser(["show", "name", "text"], ix.schema)  # type: ignore
    parser.add_plugin(  # type: ignore
        FieldAliasPlugin(
            {
                "show": ["series", "s"],
                "episode": ["ep", "e"],
                "name": ["actor", "n"],
            }
        )
    )

    logger.trace(query)
    query = parser.parse(query)  # type: ignore
    logger.trace(query)
    result = searcher.search(query)  # type: ignore
    logger.trace(list(result))  # type: ignore
    return result  # type: ignore


# ===== file watching =====


class MkvFilter(DefaultFilter):
    allowed_extensions = ".mkv"

    def __call__(self, change: Change, path: str) -> bool:
        return super().__call__(change, path) and path.endswith(self.allowed_extensions)


async def watch():
    logger.info(f"Watching files in {assets_path}")
    async for changes in awatch(assets_path, watch_filter=MkvFilter()):
        for change, path in changes:
            path = Path(path)
            show = path.parent.name
            logger.debug(f"change seen: {change} {path}")
            with ix.writer() as writer:  # type: ignore
                match change:
                    case Change.added:
                        ep = Episode.from_path(path)
                        index_add(writer, show, ep)  # type: ignore
                    case Change.modified:
                        index_del(writer, show, path.name)  # type: ignore
                        ep = Episode.from_path(path)
                        index_add(writer, show, ep)  # type: ignore
                    case Change.deleted:
                        index_del(writer, show, path.name)  # type: ignore


ix = None
if exists_in(index_path):
    logger.info(f"Search index found in {index_path}")
    ix = open_dir(index_path)
    if ix.schema == schema:  # type: ignore
        logger.info("Schema matches, checking integrity")
        ix = gen_index_partial(ix)
    else:
        logger.info("Schema mismatch, regenerating index")
        shutil.rmtree(index_path)
        ix = gen_index_full()
else:
    logger.info(f"Search index not found in {index_path}, creating")
    ix = gen_index_full()
