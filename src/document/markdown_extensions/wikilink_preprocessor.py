# import logging  # For logdecorator
import markdown
import re

# from logdecorator import log_on_end
from markdown import Extension
from markdown.preprocessors import Preprocessor
from typing import Any, Dict, List

# from document import config

# logger = config.get_logger(__name__)


class WikiLinkPreprocessor(Preprocessor):
    """Convert wiki links to Markdown links."""

    def __init__(self, config: Dict, md: markdown.Markdown) -> None:
        """Initialize."""
        # Example use of config. See __init__ for WikiLinkExtension
        # below for initialization.
        # self.encoding = config.get("encoding")
        # super(WikiLinkPreprocessor, self).__init__()
        super().__init__()

    # @log_on_end(logging.DEBUG, "lines after preprocessor: {result}", logger=logger)
    def convert_wikilinks(self, lines: List[str]) -> List[str]:
        """Convert wiki style links into Markdown links."""
        source = "\n".join(lines)
        pattern = r"\[\[(.*?)\]\]"
        # if m := re.search(pattern, source):
        #     # Inspect source and m here in debug repl
        #     breakpoint()
        source = re.sub(pattern, r"[](\1)", source)
        return source.split("\n")

    def run(self, lines: List[str]) -> List[str]:
        """Entrypoint."""
        return self.convert_wikilinks(lines)


class WikiLinkExtension(Extension):
    """Wikilink to Markdown link conversion extension."""

    def __init__(self, *args: List, **kwargs: Dict) -> None:
        """Initialize."""
        self.config = {
            # Example config entry from the snippets extension that
            # ships with Python-Markdown library.
            # "encoding": ["utf-8", 'Encoding of snippets - Default: "utf-8"'],
        }
        # super(WikiLinkExtension, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """Register the extension."""
        self.md = md
        md.registerExtension(self)
        config = self.getConfigs()
        wikilink = WikiLinkPreprocessor(config, md)
        md.preprocessors.register(wikilink, "wikilink", 32)


def makeExtension(*args: Any, **kwargs: Any) -> WikiLinkExtension:
    """Return extension."""
    return WikiLinkExtension(*args, **kwargs)
