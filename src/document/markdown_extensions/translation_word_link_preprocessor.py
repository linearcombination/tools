import logging  # For logdecorator
import markdown
import os
import pathlib
import re

from logdecorator import log_on_start  # , log_on_end
from markdown import Extension
from markdown.preprocessors import Preprocessor
from typing import cast, Dict, List, Optional

from document import config
from document.utils import file_utils

logger = config.get_logger(__name__)

# See https://github.com/Python-Markdown/markdown/wiki/Tutorial-2---Altering-Markdown-Rendering
# for template to follow.

# Handle [foo](../kt/foo.md) style links.
TRANSLATION_WORD_LINK_RE = (
    r"\[(?P<link_text>.*?)\]\(\.+\/(?:kt|names|other)\/(?P<word>.*?)\.md\)"
)

# This next pattern catches scripture references like: ../col/01/03.md
# pattern = r"\[(.*?)\]\(.*?\/(.*?)\.md\)"

# Handle [[rc://*/tw/dict/kt/foo.md]] style links.
TRANSLATION_WORD_LINK_ALT_RE = (
    r"\[\[rc:\/\/\*\/tw\/dict\/bible\/(?:kt|names|other)\/(?P<word>.*?)\]\]"
)

# FIXME To be implemented. We need to find out what URL to use for obs
# resources.
# [21:9](rc://gu/tn/help/obs/21/09)
TRANSLATION_NOTE_OBS_LINK_RE = r"\[(?P<link_text>.*?)\]\(rc:\/\/.*?\/tn\/help\/obs\/(?P<chapter_num>.*?)\/(?P<verse_ref>.*?)\)"

# Handle [Blah 46: 33-34](rc://gu/tn/help/gen/46/33) style links
TRANSLATION_NOTE_LINK_RE = r"\[(?P<link_text>.*?)\]\(rc:\/\/.*?\/tn\/help\/(?P<book_id>.*?)\/(?P<chapter_num>.*?)\/(?P<verse_ref>.*?)\)"


class TranslationWordLinkPreprocessor(Preprocessor):
    """Convert wiki links to Markdown links."""

    @log_on_start(
        logging.DEBUG,
        "lang_code: {lang_code}, tw_resource_dir: {tw_resource_dir}",
        logger=logger,
    )
    def __init__(
        self,
        md: markdown.Markdown,
        lang_code: str,
        tw_resource_dir: Optional[str],
    ) -> None:
        """Initialize."""
        # Avoid circular reference by importing here instead of the
        # top of the file.
        from document.domain.resource import TWResource

        self.md = md
        self.lang_code = lang_code
        self.tw_resource_dir = tw_resource_dir
        # FIXME A conditional on self.tw_resoruce_dir will obviate the
        # cast for mypy. If you go this route then you can initialize
        # self.translation_word_filepaths and
        # self.translation_words_dict to empty data structures first
        # and then only update them if their dependencies are not
        # None.
        self.translation_word_filepaths = (
            TWResource.get_translation_word_filepaths(cast(str, self.tw_resource_dir))
            if tw_resource_dir
            else None
        )
        # logger.debug(
        #     "self.translation_word_filepaths: {}".format(
        #         self.translation_word_filepaths
        #     )
        # )
        self.translation_words_dict = (
            {
                pathlib.Path(os.path.basename(word_filepath)).stem: word_filepath
                for word_filepath in self.translation_word_filepaths
            }
            if self.translation_word_filepaths
            else {}
        )
        # logger.debug(
        #     "self.translation_words_dict: {}".format(self.translation_words_dict)
        # )
        super().__init__()

    def run(self, lines: List[str]) -> List[str]:
        """
        Entry point.
        """
        source = "\n".join(lines)
        source = self.transform_translation_word_link(source)
        # Some language book combos use a different link format. Handle those.
        source = self.transform_translation_word_alt_link(source)
        # FIXME Finish Implementing
        source = self.transform_translation_note_link(source)
        return source.split("\n")

    def transform_translation_word_link(self, source: str) -> str:
        """
        Transform the translation word relative file link into a
        source anchor link pointing to a destination anchor link for
        the translation word definition. If the language is
        non-English then also localize the translation word link text
        (we wouldn't want English link text in a non-English language
        - but this is actually often what exists in the link pointing
        to the translation word definition).
        """
        # Avoid circular reference by importing here instead of the
        # top of the file.
        from document.domain.resource import TWResource

        for match in re.finditer(TRANSLATION_WORD_LINK_RE, source):
            filename_sans_suffix = match.group(2)
            if filename_sans_suffix in self.translation_words_dict:
                if self.lang_code != "en":
                    # Need to localize non-English languages.
                    file_content = file_utils.read_file(
                        self.translation_words_dict[filename_sans_suffix]
                    )
                    # Get the localized name for the translation word
                    localized_translation_word = (
                        TWResource.get_localized_translation_word(file_content)
                    )
                    # Build the anchor links
                    source = source.replace(
                        match.group(0),  # The whole match
                        r"[{}](#{}-{})".format(
                            match.group("link_text"),
                            self.lang_code,
                            localized_translation_word,
                        ),
                    )
                else:
                    # Build the anchor links.
                    source = source.replace(
                        match.group(0),
                        r"[{}](#{}-{})".format(
                            match.group("link_text"),
                            self.lang_code,
                            match.group("word"),
                        ),
                    )
            else:
                logger.info(
                    "match.group('word'): {} is not in translation words dict".format(
                        match.group("word")
                    )
                )

        return source

    def transform_translation_word_alt_link(self, source: str) -> str:
        """
        Transform the translation word rc link into source anchor link
        pointing to a destination anchor link for the translation word
        definition. If the language is non-English then also localize
        the translation word link text (we wouldn't want English link
        text in a non-English language - but this is actually often what
        exists in the link pointing to the translation word
        definition).
        """
        # Avoid circular reference by importing here instead of the
        # top of the file.
        from document.domain.resource import TWResource

        for match in re.finditer(TRANSLATION_WORD_LINK_ALT_RE, source):
            logger.info("there are matches using TRANSLATION_WORD_LINK_ALT_RE")
            filename_sans_suffix = match.group(1)
            logger.debug("filename_sans_suffix: {}".format(filename_sans_suffix))
            if filename_sans_suffix in self.translation_words_dict:
                logger.info("filename_sans_suffix is in self.translation_words_dict")
                if self.lang_code != "en":
                    logger.debug(
                        "About to read file: {}".format(
                            self.translation_words_dict[filename_sans_suffix]
                        )
                    )
                    # Need to localize non-English languages.
                    file_content = file_utils.read_file(
                        self.translation_words_dict[filename_sans_suffix]
                    )
                    # Get the localized name for the translation word
                    localized_translation_word = (
                        TWResource.get_localized_translation_word(file_content)
                    )
                    # Build the anchor links
                    source = source.replace(
                        match.group(0),  # The whole match
                        r"[{}](#{}-{})".format(
                            localized_translation_word,
                            self.lang_code,
                            match.group("word"),
                        ),
                    )
                else:
                    # Build the anchor links.
                    source = source.replace(
                        match.group(0),
                        r"[{}](#{}-{})".format(
                            match.group("word"), self.lang_code, match.group("word")
                        ),
                    )
            else:
                logger.info(
                    "match: {} is not in translation words dict".format(match.group(0))
                )

        return source

    def transform_translation_note_link(self, source: str) -> str:
        """
        Transform the translation note rc link into a link pointing to
        the anchor link for the translation note for chapter verse
        reference.
        """
        for match in re.finditer(TRANSLATION_NOTE_LINK_RE, source):
            logger.info("there are matches using TRANSLATION_NOTE_LINK_RE")
            book_id = match.group("book_id")
            if book_id == "obs":
                # Create link to obs resource
                # FIXME Implement.
                # source = source.replace(
                #     match.group(0),
                #     r"[{}](#{}-{}-tn-ch-{}-v-{})".format(
                #         match.group("link_text"),
                #         self.lang_code,
                #         # FIXME Make sure book_id is not 'obs' or update
                #         # the RE so that it doesn't match 'obs' in the
                #         # book_id position.
                #         match.group("book_id"),
                #         match.group("chapter_num").zfill(3),
                #         match.group("verse_ref").zfill(3),
                #     ),
                # )
                pass
            else:
                # Build the link to the translation note resource.
                # FIXME These type of links can point to any book,
                # chapter, verse combo for the given language. Of
                # course, this means that the translation note link
                # may point to a translation note that is not included
                # in the current DocumentRequest. In a perfect world,
                # we would thus build an internal link to any
                # translation note that is included in this
                # DocumentRequest and build an external link to any
                # translation note that is not included in this
                # DocumentRequest. The problem is that to build
                # internal links we'd need to pass in the
                # DocumentRequest instance to this extension in order
                # to determine if a resource link would be to an
                # internal (to this DocumentRequest) or external
                # resource.
                # if internal link then:
                source = source.replace(
                    match.group(0),
                    r"[{}](#{}-{}-tn-ch-{}-v-{})".format(
                        match.group("link_text"),
                        self.lang_code,
                        # FIXME Make sure book_id is not 'obs' or update
                        # the RE so that it doesn't match 'obs' in the
                        # book_id position.
                        match.group("book_id"),
                        match.group("chapter_num").zfill(3),
                        match.group("verse_ref").zfill(3),
                    ),
                )
                # else:
                # build an external link to the translation note

        return source


class TranslationWordLinkExtension(Extension):
    """A Markdown link conversion extension."""

    def __init__(self, **kwargs: Dict) -> None:
        """Initialize."""
        self.config = {
            "lang_code": [
                "en",
                "The language code for the resource whose asset files are currently being processed.",
            ],
            "tw_resource_dir": [
                "",
                "The base directory for the translation word Markdown filepaths.",
            ],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        # logger.debug(
        #     "self.getConfig('translation_word_filepaths'): {}".format(
        #         self.getConfig("translation_word_filepaths")
        #     )
        # )
        md.preprocessors.register(
            TranslationWordLinkPreprocessor(
                md,
                lang_code=list(self.getConfig("lang_code"))[0],
                tw_resource_dir=list(self.getConfig("tw_resource_dir"))[0],
            ),
            "translationwordlink",
            32,
        )
