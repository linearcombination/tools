"""
This module provides the assembly strategies and sub-strategies that
are used to assemble HTML documents prior to their conversion to PDF
form.

Assembly strategies utilize the Strategy pattern:
https://github.com/faif/python-patterns/blob/master/patterns/behavioral/strategy.py
"""


# Handle circular import issue with document_generator module.
from __future__ import annotations  # https://www.python.org/dev/peps/pep-0563/

import itertools
import logging  # For logdecorator
import re

from logdecorator import log_on_start
from typing import Callable, cast, Dict, List, Optional, Tuple

from document import config
from document.domain import bible_books, document_generator, model
from document.domain.resource import (
    Resource,
    USFMResource,
    TNResource,
    TWResource,
    TQResource,
    TAResource,
)


logger = config.get_logger(__name__)

########################################################################
## Asseembly strategy and sub-strategy factories
##
## Currently, there are two levels of assembly strategies: one higher,
## chosen by _assembly_strategy_factory, and one lower, chosen by
## _assembly_sub_strategy_factory. These two levels of assembly
## strategies work together in the following way: the higher level
## constrains the assembly algorithm by some criteria, e.g., by
## language, and then the lower level further organizes the assembly
## within those constraints, .e.g., by superimposing an order to when
## resource's are interleaved. It is possible to have both multiple
## higher level, so-called 'assembly strategies' and lower level,
## so-called 'sub strategies', assembly strategies.


def assembly_strategy_factory(
    assembly_strategy_kind: model.AssemblyStrategyEnum,
) -> Callable[[document_generator.DocumentGenerator], str]:
    """
    Strategy pattern. Given an assembly_strategy_kind, returns the
    appropriate strategy function to run.
    """
    strategies = {
        model.AssemblyStrategyEnum.LANGUAGE_BOOK_ORDER: _assemble_content_by_lang_then_book,
        model.AssemblyStrategyEnum.BOOK_LANGUAGE_ORDER: _assemble_content_by_book_then_lang,
    }
    return strategies[assembly_strategy_kind]


def assembly_sub_strategy_factory(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> Callable[
    [
        Optional[USFMResource],
        Optional[TNResource],
        Optional[TQResource],
        Optional[TWResource],
        Optional[TAResource],
        Optional[USFMResource],
        model.AssemblySubstrategyEnum,
    ],
    model.HtmlContent,
]:
    """
    Strategy pattern. Given the existence, i.e., exists or None, of each
    type of the possible resource instances and an
    assembly sub-strategy kind, returns the appropriate sub-strategy
    function to run.

    This functions as a lookup table that will select the right
    assembly function to run. The impetus for it is to avoid messy
    conditional logic in an otherwise monolithic assembly algorithm
    that would be checking the existence of each resource.
    This makes adding new strategies straightforward, if a bit
    redundant. The redundancy is the cost of comprehension.
    """
    strategies: Dict[
        Tuple[
            # Params: usfm_resource_exists, tn_resource_exists,
            # tq_resource_exists, tw_resource_exists, ta_resource_exists,
            # usfm_resource2_exists, assembly_strategy_kind
            bool,
            bool,
            bool,
            bool,
            bool,
            bool,
            model.AssemblySubstrategyEnum,
        ],
        Callable[
            [
                Optional[USFMResource],
                Optional[TNResource],
                Optional[TQResource],
                Optional[TWResource],
                Optional[TAResource],
                Optional[USFMResource],
                model.AssemblySubstrategyEnum,
            ],
            model.HtmlContent,
        ],
    ] = {
        (
            True,
            True,
            True,
            True,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_tq_tw_usfm2_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            True,
            True,
            False,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_tq_usfm2_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            False,
            True,
            False,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            False,
            False,
            True,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            True,
            False,
            False,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            True,
            False,
            True,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            False,
            True,
            True,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            False,
            False,
            False,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_tq_usfm2_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            False,
            False,
            False,
            False,
            False,
            True,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_tq_usfm2_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        # (
        #     True,
        #     True,
        #     True,
        #     True,
        #     True,
        #     False,
        #     model.AssemblySubstrategyEnum.VERSE,
        # ): _assemble_usfm_tn_tq_tw_ta_content_by_verse,
        # ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            True,
            True,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_tq_tw_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            True,
            False,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_tw_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            False,
            True,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_tq_tw_content_by_verse,
        # ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            False,
            False,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_tw_content_by_verse,
        (
            True,
            True,
            True,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_tq_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            True,
            False,
            True,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_tq_content_by_verse,
        (
            True,
            True,
            False,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_tn_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            False,
            True,
            True,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_tn_tq_tw_content_by_verse,
        ): _assemble_tn_as_iterator_content_by_verse,
        (
            False,
            True,
            False,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_tn_tw_content_by_verse,
        ): _assemble_tn_as_iterator_content_by_verse,
        (
            False,
            True,
            True,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_tn_tq_content_by_verse,
        ): _assemble_tn_as_iterator_content_by_verse,
        (
            False,
            False,
            True,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tq_tw_content_by_verse,
        (
            False,
            False,
            False,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tw_content_by_verse,
        (
            False,
            False,
            True,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tq_content_by_verse,
        (
            True,
            False,
            False,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_usfm_content_by_verse,
        ): _assemble_usfm_as_iterator_content_by_verse,
        (
            False,
            True,
            False,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
            # ): _assemble_tn_content_by_verse,
        ): _assemble_tn_as_iterator_content_by_verse,
    }
    return strategies[
        (
            # Turn existence (exists or not) into a boolean for each
            # instance, the tuple of these together are an immutable,
            # and thus hashable, dictionary key into our function lookup table.
            usfm_resource is not None,
            tn_resource is not None,
            tq_resource is not None,
            tw_resource is not None,
            ta_resource is not None,
            usfm_resource2 is not None,
            assembly_substrategy_kind,
        )
    ]


def assembly_sub_strategy_factory_for_book_then_lang(
    usfm_resources: List[USFMResource],
    tn_resources: List[TNResource],
    tq_resources: List[TQResource],
    tw_resources: List[TWResource],
    ta_resources: List[TAResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> Callable[
    [
        List[USFMResource],
        List[TNResource],
        List[TQResource],
        List[TWResource],
        List[TAResource],
        model.AssemblySubstrategyEnum,
    ],
    model.HtmlContent,
]:
    """
    Strategy pattern. Given the existence, i.e., exists or emtpy, of each
    type of the possible resource instances and an
    assembly sub-strategy kind, returns the appropriate sub-strategy
    function to run.

    This functions as a lookup table that will select the right
    assembly function to run. The impetus for it is to avoid messy
    conditional logic in an otherwise monolithic assembly algorithm
    that would be checking the existence of each resource.
    This makes adding new strategies straightforward, if a bit
    redundant. The redundancy is the cost of comprehension.
    """
    strategies: Dict[
        Tuple[
            # Params: usfm_resources is non-empty, tn_resources is non-empty, tq_resources is non-empty, tw_resources is non-empty, ta_resources is non-empty, assembly_strategy_kind
            bool,
            bool,
            bool,
            bool,
            bool,
            model.AssemblySubstrategyEnum,
        ],
        Callable[
            [
                List[USFMResource],
                List[TNResource],
                List[TQResource],
                List[TWResource],
                List[TAResource],
                model.AssemblySubstrategyEnum,
            ],
            model.HtmlContent,
        ],
    ] = {
        (
            True,
            True,
            True,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            True,
            True,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            True,
            True,
            False,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            True,
            True,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            True,
            False,
            True,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            True,
            False,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            True,
            False,
            False,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            True,
            False,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang,
        (
            False,
            True,
            True,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tn_as_iterator_content_by_verse_for_book_then_lang,
        (
            False,
            True,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tn_as_iterator_content_by_verse_for_book_then_lang,
        (
            False,
            True,
            False,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tn_as_iterator_content_by_verse_for_book_then_lang,
        (
            False,
            True,
            False,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tn_as_iterator_content_by_verse_for_book_then_lang,
        (
            False,
            False,
            True,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tq_as_iterator_content_by_verse_for_book_then_lang,
        (
            False,
            False,
            True,
            False,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tq_as_iterator_content_by_verse_for_book_then_lang,
        (
            False,
            False,
            False,
            True,
            False,
            model.AssemblySubstrategyEnum.VERSE,
        ): _assemble_tw_as_iterator_content_by_verse_for_book_then_lang,
    }
    return strategies[
        (
            # Turn existence (exists or not) into a boolean for each
            # instance, the tuple of these together are an immutable,
            # and thus hashable, dictionary key into our function lookup table.
            True if usfm_resources else False,
            True if tn_resources else False,
            True if tq_resources else False,
            True if tw_resources else False,
            True if ta_resources else False,
            assembly_substrategy_kind,
        )
    ]


#######################################
## Assembly strategy implementations


@log_on_start(
    logging.INFO,
    "Assembling document by interleaving at first by language and then by book.",
    logger=logger,
)
def _assemble_content_by_lang_then_book(
    docgen: document_generator.DocumentGenerator,
) -> str:
    """
    Assemble by language then by book in lexicographical order before
    delegating more atomic ordering/interleaving to an assembly
    sub-strategy.
    """
    # NOTE Each strategy can interleave resource material the way it
    # wants. A user could choose a strategy they want at the front
    # end. Presumably, we could offer the user such strategies from a
    # dropdown that would be intelligent enough to only present
    # choices that make sense for the number of languages and
    # resources they have selected, e.g., we wouldn't bother them with
    # the choice of interleaving strategy if for instance all they
    # wanted was TN for Swahili and nothing else.

    resources_sorted_by_language = sorted(
        docgen.found_resources,
        key=lambda resource: resource.lang_name,
    )
    html = []
    language: str
    # group_by_lang: itertools._grouper
    for language, group_by_lang in itertools.groupby(
        resources_sorted_by_language,
        lambda resource: resource.lang_name,
    ):
        html.append(config.get_html_format_string("language").format(language))

        # For groupby's sake, we need to first sort
        # group_by_lang before doing a groupby operation on it so that
        # resources will be clumped together by resource code, i.e.,
        # by language, otherwise a new group will be created every time a new
        # resource_code is sequentially encountered.
        resources_sorted_by_book = sorted(
            group_by_lang, key=lambda resource: resource.resource_code
        )
        for book, group_by_book in itertools.groupby(
            resources_sorted_by_book, lambda resource: resource.resource_code
        ):
            html.append(
                config.get_html_format_string("book").format(
                    # FIXME Use localized book name
                    bible_books.BOOK_NAMES[book]
                )
            )

            # Save grouper generator values in list since it will get exhausted
            # when used and exhausted generators cannot be reused.
            resources = list(group_by_book)
            usfm_resource: Optional[USFMResource] = _get_first_usfm_resource(resources)
            tn_resource: Optional[TNResource] = _get_tn_resource(resources)
            tq_resource: Optional[TQResource] = _get_tq_resource(resources)
            tw_resource: Optional[TWResource] = _get_tw_resource(resources)
            ta_resource: Optional[TAResource] = _get_ta_resource(resources)
            usfm_resource2: Optional[USFMResource] = _get_second_usfm_resource(
                resources
            )

            # We've got the resources, now we can use the sub-strategy factory
            # method to choose the right function to use from here on out.
            docgen.assembly_sub_strategy = assembly_sub_strategy_factory(
                usfm_resource,
                tn_resource,
                tq_resource,
                tw_resource,
                ta_resource,
                usfm_resource2,
                config.get_default_assembly_substrategy(),
            )

            logger.debug(
                "docgen._assembly_sub_strategy: {}".format(
                    str(docgen.assembly_sub_strategy)
                )
            )

            # Now that we have the sub-strategy, let's run it and
            # generate the HTML output.
            sub_html: model.HtmlContent = docgen.assembly_sub_strategy(
                usfm_resource,
                tn_resource,
                tq_resource,
                tw_resource,
                ta_resource,
                usfm_resource2,
                config.get_default_assembly_substrategy(),
            )
            html.append(sub_html)

    return "\n".join(html)


@log_on_start(
    logging.INFO,
    "Assembling document by interleaving at first by book and then by language.",
    logger=logger,
)
def _assemble_content_by_book_then_lang(
    docgen: document_generator.DocumentGenerator,
) -> str:
    """
    Assemble by book then by language in lexicographical order before
    delegating more atomic ordering/interleaving to an assembly
    sub-strategy.
    """

    # NOTE Each strategy can interleave resource material the way it
    # wants. A user could choose a strategy they want at the front
    # end. Presumably, we could offer the user such strategies from a
    # dropdown that would be intelligent enough to only present
    # choices that make sense for the number of languages and
    # resources they have selected, e.g., we wouldn't bother them with
    # the choice of interleaving strategy if for instance all they
    # wanted was TN for Swahili and nothing else.

    resources_sorted_by_book = sorted(
        # docgen.found_resources, key=lambda resource: resource.lang_name,
        docgen.found_resources,
        key=lambda resource: resource.resource_code,
    )
    html = []
    book: str
    # group_by_book: itertools._grouper
    for book, group_by_book in itertools.groupby(
        resources_sorted_by_book,
        lambda resource: resource.resource_code,
    ):
        html.append(
            config.get_html_format_string("book_as_grouper").format(
                bible_books.BOOK_NAMES[book]
            )
        )

        # Save grouper generator values in list since it will get exhausted
        # when used and exhausted generators cannot be reused.
        resources = list(group_by_book)
        # usfm_resource: Optional[USFMResource] = _get_first_usfm_resource(resources)
        usfm_resources: List[USFMResource] = _get_usfm_resources(resources)
        tn_resources: List[TNResource] = _get_tn_resources(resources)
        tq_resources: List[TQResource] = _get_tq_resources(resources)
        tw_resources: List[TWResource] = _get_tw_resources(resources)
        ta_resources: List[TAResource] = _get_ta_resources(resources)
        # usfm_resource2: Optional[USFMResource] = _get_second_usfm_resource(resources)

        # We've got the resources, now we can use the sub-strategy factory
        # method to choose the right function to use from here on out.
        docgen.assembly_sub_strategy_for_book_then_lang = (
            assembly_sub_strategy_factory_for_book_then_lang(
                usfm_resources,
                tn_resources,
                tq_resources,
                tw_resources,
                ta_resources,
                config.get_default_assembly_substrategy(),
            )
        )

        logger.debug(
            "docgen._assembly_sub_strategy_for_book_then_lang: {}".format(
                str(docgen.assembly_sub_strategy_for_book_then_lang)
            )
        )

        # Now that we have the sub-strategy, let's run it and
        # generate the HTML output.
        sub_html: model.HtmlContent = docgen.assembly_sub_strategy_for_book_then_lang(
            usfm_resources,
            tn_resources,
            tq_resources,
            tw_resources,
            ta_resources,
            config.get_default_assembly_substrategy(),
        )
        html.append(sub_html)

    return "\n".join(html)


#########################################################################
# Assembly sub-strategy implementations for language then book strategy
#
# Possible combinations with usfm (e.g., ulb, ulb-wa, cuv, nav, etc), tn,
# tq, tw, usfm2 (e.g., udb):
#
#
#  | usfm | tn | tq | tw | usfm2 | combination as string | complete | unit test | comment    |
#  |------+----+----+----+-------+-----------------------+----------+-----------+------------|
#  |    0 |  0 |  0 |  0 |     1 | usfm2                 | y        | y         | See note * |
#  |    0 |  0 |  0 |  1 |     0 | tw                    | y        | y         |            |
#  |    0 |  0 |  0 |  1 |     1 | tw,usfm2              | y        | y         | See note * |
#  |    0 |  0 |  1 |  0 |     0 | tq                    | y        | y         |            |
#  |    0 |  0 |  1 |  0 |     1 | tq,usfm2              | y        | y         | See note * |
#  |    0 |  0 |  1 |  1 |     0 | tq,tw                 | y        | y         |            |
#  |    0 |  0 |  1 |  1 |     1 | tq,tw,usfm2           | y        | y         | See note * |
#  |    0 |  1 |  0 |  0 |     0 | tn                    | y        | y         |            |
#  |    0 |  1 |  0 |  0 |     1 | tn,usfm2              | y        | y         | See note * |
#  |    0 |  1 |  0 |  1 |     0 | tn,tw                 | y        | y         |            |
#  |    0 |  1 |  0 |  1 |     1 | tn,tw,usfm2           | y        | y         | See note * |
#  |    0 |  1 |  1 |  0 |     0 | tn,tq                 | y        | y         |            |
#  |    0 |  1 |  1 |  0 |     1 | tn,tq,usfm2           | y        | y         | See note * |
#  |    0 |  1 |  1 |  1 |     0 | tn,tq,tw              | y        | y         |            |
#  |    0 |  1 |  1 |  1 |     1 | tn,tq,tw,usfm2        | y        | y         | See note * |
#  |    1 |  0 |  0 |  0 |     0 | usfm                  | y        | y         |            |
#  |    1 |  0 |  0 |  0 |     1 | usfm,usfm2            | y        | y         |            |
#  |    1 |  0 |  0 |  1 |     0 | usfm,tw               | y        | y         |            |
#  |    1 |  0 |  0 |  1 |     1 | usfm,tw,usfm2         | y        | y         |            |
#  |    1 |  0 |  1 |  0 |     0 | usfm,tq               | y        | y         |            |
#  |    1 |  0 |  1 |  0 |     1 | usfm,tq,usfm2         | y        | y         |            |
#  |    1 |  0 |  1 |  1 |     0 | usfm,tq,tw            | y        | y         |            |
#  |    1 |  0 |  1 |  1 |     1 | usfm,tq,tw,usfm2      | y        | y         |            |
#  |    1 |  1 |  0 |  0 |     0 | usfm,tn               | y        | y         |            |
#  |    1 |  1 |  0 |  0 |     1 | usfm,tn,usfm2         | y        | y         |            |
#  |    1 |  1 |  0 |  1 |     0 | usfm,tn,tw            | y        | y         |            |
#  |    1 |  1 |  0 |  1 |     1 | usfm,tn,tw,usfm2      | y        | y         |            |
#  |    1 |  1 |  1 |  0 |     0 | usfm,tn,tq            | y        | y         |            |
#  |    1 |  1 |  1 |  0 |     1 | usfm,tn,tq,usfm2      | y        | y         |            |
#  |    1 |  1 |  1 |  1 |     0 | usfm,tn,tq,tw         | y        | y         |            |
#  |    1 |  1 |  1 |  1 |     1 | usfm,tn,tq,tw,usfm2   | y        | y         |            |
#
# Note *:
#
# If there is only one USFM resource requested then the assembly
# strategy algo, via _get_first_usfm_resource, puts that USFM resource
# in usfm_resource position rather than usfm_resource2 position. If two
# USFM resources are requested then the second one in the
# DocumentRequest gets put in usfm_resource2 position. Only the first
# USFM resource in the DocumentRequest has any subsequent TN, TQ, TW,
# and TA resources referencing it. A second USFMResource, e.g., udb,
# stands alone without referencing resources. This seems to work out
# fine in practice, but may be changed later by forcing usfm_resource to
# be of a particular resource_type, e.g., ulb, cuv, nav, and
# usfm_resource2 to be of another, e.g., udb. This change could be
# accomplished by modifying _get_first_usfm_resource and
# _get_second_usfm_resource.


def _assemble_usfm_as_iterator_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein at least one
    USFM resource (e.g., ulb, nav, cuv, etc.) exists, and TN, TQ, TW,
    and a second USFM (e.g., probably always udb) may exist. If only
    one USFM exists then it will be used as the first
    USFM resource even if it is of udb resource type. Non-USFM
    resources, e.g., TN, TQ, TW, and TA will reference (and link where
    applicable) the first USFM resource and come after it in the
    interleaving strategy. The second USFM resource is displayed last
    in this interleaving strategy.
    """

    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []
    if tn_resource:
        book_intro = tn_resource.book_payload.intro_html
        book_intro = _adjust_book_intro_headings(book_intro)
        html.append(model.HtmlContent(book_intro))

    if usfm_resource:
        # Scripture type for usfm_resource, e.g., ulb, cuv, nav, etc.
        html.append(
            model.HtmlContent(
                config.get_html_format_string("resource_type_name").format(
                    usfm_resource.resource_type_name
                )
            )
        )
        # PEP526 disallows declaration of types in for loops, but allows this.
        chapter_num: model.ChapterNum
        chapter: model.USFMChapter
        for chapter_num, chapter in usfm_resource.chapters_content.items():
            # Add in the USFM chapter heading.
            chapter_heading = model.HtmlContent("")
            chapter_heading = chapter.chapter_content[0]
            html.append(chapter_heading)
            if tn_resource:
                # Add the translation notes chapter intro.
                chapter_intro = _get_chapter_intro(tn_resource, chapter_num)
                html.append(chapter_intro)

                tn_verses = tn_resource.get_verses_for_chapter(chapter_num)
            if tq_resource:
                tq_verses = tq_resource.get_verses_for_chapter(chapter_num)

            # PEP526 disallows declaration of types in for
            # loops, but allows this.
            verse_num: model.VerseRef
            verse: model.HtmlContent
            # Now let's interleave USFM verse with its translation note, translation
            # questions, and translation words if available.
            for verse_num, verse in chapter.chapter_verses.items():
                # Add header
                html.append(
                    model.HtmlContent(
                        config.get_html_format_string(
                            "resource_type_name_with_ref"
                        ).format(
                            usfm_resource.resource_type_name, chapter_num, verse_num
                        )
                    )
                )
                # Add scripture verse
                html.append(verse)
                # Add TN verse content, if any
                if tn_resource and tn_verses and verse_num in tn_verses:
                    tn_verse_content = tn_resource.format_tn_verse(
                        chapter_num,
                        verse_num,
                        tn_verses[verse_num],
                    )
                    html.extend(tn_verse_content)
                # Add TQ verse content, if any
                if tq_resource and tq_verses and verse_num in tq_verses:
                    tq_verse_content = _format_tq_verse(
                        tq_resource.resource_type_name,
                        chapter_num,
                        verse_num,
                        tq_verses[verse_num],
                    )
                    html.extend(tq_verse_content)

                if tw_resource:
                    # Add the translation words links section.
                    translation_word_links_html = (
                        tw_resource.get_translation_word_links(
                            chapter_num,
                            verse_num,
                            verse,
                        )
                    )
                    html.extend(translation_word_links_html)
            # Add scripture footnotes if available
            if chapter.chapter_footnotes:
                html.append(config.get_html_format_string("footnotes"))
                html.append(chapter.chapter_footnotes)
        if tw_resource:
            # Add the translation words definition section.
            linked_translation_words = tw_resource.get_translation_words_section()
            html.extend(linked_translation_words)

    if usfm_resource2:
        # Scripture type for usfm_resource2, e.g., udb
        html.append(
            model.HtmlContent(
                config.get_html_format_string("resource_type_name").format(
                    usfm_resource2.resource_type_name
                )
            )
        )
        # Add the usfm_resource2, e.g., udb, scripture verses.
        for chapter_num, chapter in usfm_resource2.chapters_content.items():
            # Add in the USFM chapter heading.
            chapter_heading = model.HtmlContent("")
            chapter_heading = chapter.chapter_content[0]
            html.append(chapter_heading)
            # Now let's interleave USFM verse with its translation note, translation
            # questions, and translation words if available.
            for verse_num, verse in chapter.chapter_verses.items():
                # Add header
                html.append(
                    model.HtmlContent(
                        config.get_html_format_string(
                            "resource_type_name_with_ref"
                        ).format(
                            usfm_resource2.resource_type_name, chapter_num, verse_num
                        )
                    )
                )
                # Add scripture verse
                html.append(verse)
    return model.HtmlContent("\n".join(html))


def _assemble_usfm_tq_tw_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein USFM, TQ,
    and TW exist.
    """
    usfm_resource = cast(
        USFMResource, usfm_resource
    )  # Make mypy happy. We know, due to how we got here, that usfm_resource object is not None.
    tq_resource = cast(
        TQResource, tq_resource
    )  # Make mypy happy. We know, due to how we got here, that tq_resource object is not None.
    tw_resource = cast(
        TWResource, tw_resource
    )  # Make mypy happy. We know, due to how we got here, that tq_resource object is not None.

    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    chapter: model.USFMChapter
    for chapter_num, chapter in usfm_resource.chapters_content.items():
        # Add in the USFM chapter heading.
        chapter_heading = model.HtmlContent("")
        chapter_heading = chapter.chapter_content[0]
        html.append(chapter_heading)

        tq_verses = tq_resource.get_verses_for_chapter(chapter_num)

        # PEP526 disallows declaration of types in for
        # loops, but allows this.
        verse_num: model.VerseRef
        verse: model.HtmlContent
        # Now let's interleave USFM verse with its translation note, translation
        # questions, and translation words if available.
        for verse_num, verse in chapter.chapter_verses.items():
            # Add header
            html.append(
                model.HtmlContent(
                    config.get_html_format_string("resource_type_name_with_ref").format(
                        usfm_resource.resource_type_name, chapter_num, verse_num
                    )
                )
            )
            # Add scripture verse
            html.append(verse)
            # Add TN verse content, if any
            if tq_verses and verse_num in tq_verses:
                tq_verse_content = _format_tq_verse(
                    tq_resource.resource_type_name,
                    chapter_num,
                    verse_num,
                    tq_verses[verse_num],
                )
                html.extend(tq_verse_content)
            # Add the translation words links section
            translation_word_links_html = tw_resource.get_translation_word_links(
                chapter_num,
                verse_num,
                verse,
            )
            html.extend(translation_word_links_html)
        # Add scripture footnotes if available
        if chapter.chapter_footnotes:
            html.append(config.get_html_format_string("footnotes"))
            html.append(chapter.chapter_footnotes)
    # Add the translation words definition section.
    linked_translation_words = tw_resource.get_translation_words_section()
    html.extend(linked_translation_words)
    return model.HtmlContent("\n".join(html))


def _assemble_usfm_tw_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein USFM and TW
    exist.
    """
    usfm_resource = cast(
        USFMResource, usfm_resource
    )  # Make mypy happy. We know, due to how we got here, that usfm_resource object is not None.
    tw_resource = cast(
        TWResource, tw_resource
    )  # Make mypy happy. We know, due to how we got here, that tq_resource object is not None.

    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    chapter: model.USFMChapter
    for chapter_num, chapter in usfm_resource.chapters_content.items():
        # Add in the USFM chapter heading.
        chapter_heading = model.HtmlContent("")
        chapter_heading = chapter.chapter_content[0]
        html.append(chapter_heading)

        # PEP526 disallows declaration of types in for
        # loops, but allows this.
        verse_num: model.VerseRef
        verse: model.HtmlContent
        # Now let's interleave USFM verse with its translation note, translation
        # questions, and translation words if available.
        for verse_num, verse in chapter.chapter_verses.items():
            # Add scripture verse header
            html.append(
                model.HtmlContent(
                    config.get_html_format_string("resource_type_name_with_ref").format(
                        usfm_resource.resource_type_name, chapter_num, verse_num
                    )
                )
            )
            # Add scripture verse
            html.append(verse)
            # Add the translation words links section
            translation_word_links_html = tw_resource.get_translation_word_links(
                chapter_num,
                verse_num,
                verse,
            )
            html.extend(translation_word_links_html)
        # Add scripture footnotes if available
        if chapter.chapter_footnotes:
            html.append(config.get_html_format_string("footnotes"))
            html.append(chapter.chapter_footnotes)
    # Add the translation words definition section.
    linked_translation_words = tw_resource.get_translation_words_section()
    html.extend(linked_translation_words)
    return model.HtmlContent("\n".join(html))


def _assemble_usfm_tq_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein only USFM and TQ exist.
    """
    usfm_resource = cast(
        USFMResource, usfm_resource
    )  # Make mypy happy. We know, due to how we got here, that usfm_resource object is not None.
    tq_resource = cast(
        TQResource, tq_resource
    )  # Make mypy happy. We know, due to how we got here, that usfm_resource object is not None.

    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    chapter: model.USFMChapter
    for chapter_num, chapter in usfm_resource.chapters_content.items():
        # Add in the USFM chapter heading.
        chapter_heading = model.HtmlContent("")
        chapter_heading = chapter.chapter_content[0]
        html.append(chapter_heading)

        tq_verses = tq_resource.get_verses_for_chapter(chapter_num)

        # PEP526 disallows declaration of types in for
        # loops, but allows this.
        verse_num: model.VerseRef
        verse: model.HtmlContent
        # Now let's interleave USFM verse with its
        # translation note if available.
        for verse_num, verse in chapter.chapter_verses.items():
            # Add scripture verse heading
            html.append(
                model.HtmlContent(
                    config.get_html_format_string("resource_type_name_with_ref").format(
                        usfm_resource.resource_type_name, chapter_num, verse_num
                    )
                )
            )
            # Add scripture verse
            html.append(verse)
            # Add TQ verse content, if any
            if tq_verses and verse_num in tq_verses:
                tq_verse_content = _format_tq_verse(
                    tq_resource.resource_type_name,
                    chapter_num,
                    verse_num,
                    tq_verses[verse_num],
                )
                html.extend(tq_verse_content)
        # Add scripture footnotes if available
        if chapter.chapter_footnotes:
            html.append(config.get_html_format_string("footnotes"))
            html.append(chapter.chapter_footnotes)
    return model.HtmlContent("\n".join(html))


def _assemble_tn_as_iterator_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein only TN, TQ,
    and TW exists.
    """
    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []
    if tn_resource:
        book_intro = tn_resource.book_payload.intro_html
        book_intro = _adjust_book_intro_headings(book_intro)
        html.append(book_intro)

        # PEP526 disallows declaration of types in for loops, but allows this.
        chapter_num: model.ChapterNum
        for chapter_num in tn_resource.book_payload.chapters:
            # How to get chapter heading for Translation notes when USFM is not
            # requested? For now we'll use non-localized chapter heading. Add in the
            # USFM chapter heading.
            chapter_heading = model.HtmlContent(
                config.get_html_format_string("tn_only_chapter_header").format(
                    tn_resource.lang_code,
                    bible_books.BOOK_NUMBERS[tn_resource.resource_code].zfill(3),
                    str(chapter_num).zfill(3),
                    chapter_num,
                )
            )
            html.append(chapter_heading)

            # Add the translation notes chapter intro.
            chapter_intro = _get_chapter_intro(tn_resource, chapter_num)
            html.append(chapter_intro)

            tn_verses = tn_resource.get_verses_for_chapter(chapter_num)
            if tq_resource:
                tq_verses = tq_resource.get_verses_for_chapter(chapter_num)

            # PEP526 disallows declaration of types in for loops, but allows this.
            verse_num: model.VerseRef
            verse: model.HtmlContent
            # Now let's get all the verse level content.
            # iterator = tn_verses or tq_verses
            # if iterator:
            if tn_verses:
                for verse_num, verse in tn_verses.items():
                    # Add TN verse content, if any
                    if tn_verses and verse_num in tn_verses:
                        tn_verse_content = tn_resource.format_tn_verse(
                            chapter_num,
                            verse_num,
                            tn_verses[verse_num],
                        )
                        html.extend(tn_verse_content)

                    # Add TQ verse content, if any
                    if tq_resource and tq_verses and verse_num in tq_verses:
                        tq_verse_content = _format_tq_verse(
                            tq_resource.resource_type_name,
                            chapter_num,
                            verse_num,
                            tq_verses[verse_num],
                        )
                        html.extend(tq_verse_content)
                    if tw_resource:
                        # Add the translation words links section.
                        translation_word_links_html = (
                            tw_resource.get_translation_word_links(
                                chapter_num,
                                verse_num,
                                verse,
                            )
                        )
                        html.extend(translation_word_links_html)
    if tw_resource:
        # Add the translation words definition section.
        linked_translation_words = tw_resource.get_translation_words_section(
            include_uses_section=False
        )
        html.extend(linked_translation_words)
    if usfm_resource2:
        # Add the usfm_resource2, e.g., udb, scripture verses.
        for chapter_num, chapter in usfm_resource2.chapters_content.items():
            # Add in the USFM chapter heading.
            chapter_heading = model.HtmlContent("")
            chapter_heading = chapter.chapter_content[0]
            html.append(chapter_heading)
            # Now let's interleave USFM verse with its translation note, translation
            # questions, and translation words if available.
            for verse_num, verse in chapter.chapter_verses.items():
                # Add header
                html.append(
                    model.HtmlContent(
                        config.get_html_format_string(
                            "resource_type_name_with_ref"
                        ).format(
                            usfm_resource2.resource_type_name, chapter_num, verse_num
                        )
                    )
                )
                # Add scripture verse
                html.append(verse)
    return model.HtmlContent("\n".join(html))


def _assemble_tq_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein only TQ exists.
    """
    tq_resource = cast(
        TQResource, tq_resource
    )  # Make mypy happy. We know, due to how we got here, that tq_resource object is not None.

    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    for chapter_num in tq_resource.book_payload.chapters:
        # How to get chapter heading for Translation questions when there is
        # not USFM requested? For now we'll use non-localized chapter heading.
        # Add in the USFM chapter heading.
        chapter_heading = model.HtmlContent(
            config.get_html_format_string("tn_only_chapter_header").format(
                tq_resource.lang_code,
                bible_books.BOOK_NUMBERS[tq_resource.resource_code].zfill(3),
                str(chapter_num).zfill(3),
                chapter_num,
            )
        )
        html.append(chapter_heading)

        # Get TQ chapter verses
        tq_verses = tq_resource.get_verses_for_chapter(chapter_num)

        # PEP526 disallows declaration of types in for loops, but allows this.
        verse_num: model.VerseRef
        verse: model.HtmlContent
        # Now let's get all the verse translation notes available.
        if tq_verses:
            for verse_num, verse in tq_verses.items():
                tq_verse_content = _format_tq_verse(
                    tq_resource.resource_type_name, chapter_num, verse_num, verse
                )
                html.extend(tq_verse_content)
    return model.HtmlContent("\n".join(html))


def _assemble_tq_tw_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein only TQ and
    TW exists.
    """
    tq_resource = cast(
        TQResource, tq_resource
    )  # Make mypy happy. We know, due to how we got here, that tq_resource object is not None.
    tw_resource = cast(
        TWResource, tw_resource
    )  # Make mypy happy. We know, due to how we got here, that tq_resource object is not None.

    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    for chapter_num in tq_resource.book_payload.chapters:
        # How to get chapter heading for Translation questions when there is
        # not USFM requested? For now we'll use non-localized chapter heading.
        # Add in the USFM chapter heading.
        chapter_heading = model.HtmlContent(
            config.get_html_format_string("tn_only_chapter_header").format(
                tq_resource.lang_code,
                bible_books.BOOK_NUMBERS[tq_resource.resource_code].zfill(3),
                str(chapter_num).zfill(3),
                chapter_num,
            )
        )
        html.append(chapter_heading)

        # Get TQ chapter verses
        tq_verses = tq_resource.get_verses_for_chapter(chapter_num)

        # PEP526 disallows declaration of types in for loops, but allows this.
        verse_num: model.VerseRef
        verse: model.HtmlContent
        # Now let's get all the verse translation notes available.
        if tq_verses:
            for verse_num, verse in tq_verses.items():
                tq_verse_content = _format_tq_verse(
                    tq_resource.resource_type_name, chapter_num, verse_num, verse
                )
                html.extend(tq_verse_content)

                # Add the translation words links section.
                translation_word_links_html = tw_resource.get_translation_word_links(
                    chapter_num,
                    verse_num,
                    verse,
                )
                html.extend(translation_word_links_html)
    # Add the translation words definition section.
    linked_translation_words = tw_resource.get_translation_words_section(
        include_uses_section=False
    )
    html.extend(linked_translation_words)
    return model.HtmlContent("\n".join(html))


def _assemble_tw_content_by_verse(
    usfm_resource: Optional[USFMResource],
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
    usfm_resource2: Optional[USFMResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein only TW exists.
    """
    tw_resource = cast(
        TWResource, tw_resource
    )  # Make mypy happy. We know, due to how we got here, that tq_resource object is not None.

    _initialize_resource_html(tn_resource, tq_resource, tw_resource, ta_resource)

    html: List[model.HtmlContent] = []

    # Add the translation words definition section.
    linked_translation_words = tw_resource.get_translation_words_section(
        include_uses_section=False
    )
    html.extend(linked_translation_words)
    return model.HtmlContent("\n".join(html))


#########################################################################
# Assembly sub-strategy implementations for book then language strategy


def _assemble_usfm_as_iterator_content_by_verse_for_book_then_lang(
    usfm_resources: List[USFMResource],
    tn_resources: List[TNResource],
    tq_resources: List[TQResource],
    tw_resources: List[TWResource],
    ta_resources: List[TAResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein at least one
    USFM resource (e.g., ulb, nav, cuv, etc.) exists, and TN, TQ, and
    TW may exist.
    """

    _initialize_resources_html(tn_resources, tq_resources, tw_resources, ta_resources)

    html: List[model.HtmlContent] = []

    # Sort resources by language
    usfm_resources.sort(key=lambda r: r.lang_code)
    tn_resources.sort(key=lambda r: r.lang_code)
    tq_resources.sort(key=lambda r: r.lang_code)
    tw_resources.sort(key=lambda r: r.lang_code)
    ta_resources.sort(key=lambda r: r.lang_code)

    # Rough sketch of algo that follows:
    # English book intro
    # French book intro
    # chapter heading, e.g., Chapter 1
    #     english chapter intro goes here
    #     french chaptre entre qui
    #         Unlocked Literal Bible (ULB) 1:1
    #         a verse goes here
    #         French ULB 1:1
    #         voila est es magnifique
    #         ULB Translation Helps 1:1
    #         translation notes for English goes here
    #         French Translation notes 1:1
    #         translation notes for French goes here
    #         etc for tq, tw links, footnotes, followed by tw definitions

    # Add book intros for each tn_resource
    for tn_resource in tn_resources:
        # Add the book intro
        book_intro = tn_resource.book_payload.intro_html
        book_intro = _adjust_book_intro_headings(book_intro)
        # book_intros.append(book_intro)
        html.append(model.HtmlContent(book_intro))

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    chapter: model.USFMChapter
    # Use the first usfm_resource as a chapter_num pump.
    for chapter_num, chapter in usfm_resources[0].chapters_content.items():
        # Add the first USFM resource's chapter heading. We ignore
        # chapter headings for other usfm_resources because it would
        # be strange to have more than one chapter heading per chapter
        # for this assembly sub-strategy.
        chapter_heading = model.HtmlContent("")
        chapter_heading = chapter.chapter_content[0]
        html.append(model.HtmlContent(chapter_heading))

        # Add chapter intro for each language
        for tn_resource in tn_resources:
            # Add the translation notes chapter intro.
            chapter_intro = _get_chapter_intro(tn_resource, chapter_num)
            html.append(model.HtmlContent(chapter_intro))

        # Use the first usfm_resource as a verse_num pump
        for verse_num, verse in (
            usfm_resources[0].chapters_content[chapter_num].chapter_verses.items()
        ):
            # Add the interleaved USFM verses
            for usfm_resource in usfm_resources:
                if (
                    chapter_num in usfm_resource.chapters_content
                    and verse_num
                    in usfm_resource.chapters_content[chapter_num].chapter_verses
                ):
                    # Add header
                    html.append(
                        model.HtmlContent(
                            config.get_html_format_string(
                                "resource_type_name_with_ref"
                            ).format(
                                usfm_resource.resource_type_name, chapter_num, verse_num
                            )
                        )
                    )
                    # Add scripture verse
                    html.append(
                        usfm_resource.chapters_content[chapter_num].chapter_verses[
                            verse_num
                        ]
                    )

            # Add the interleaved tn verses
            for tn_resource in tn_resources:
                tn_verses = tn_resource.get_verses_for_chapter(chapter_num)
                if tn_verses and verse_num in tn_verses:
                    tn_verse_content = tn_resource.format_tn_verse(
                        chapter_num,
                        verse_num,
                        tn_verses[verse_num],
                    )
                    html.extend(tn_verse_content)

            # Add the interleaved tq verses
            for tq_resource in tq_resources:
                tq_verses = tq_resource.get_verses_for_chapter(chapter_num)
                # Add TQ verse content, if any
                if tq_verses and verse_num in tq_verses:
                    tq_verse_content = _format_tq_verse(
                        tq_resource.resource_type_name,
                        chapter_num,
                        verse_num,
                        tq_verses[verse_num],
                    )
                    html.extend(tq_verse_content)

            # Add the interleaved translation word links
            for idx, tw_resource in enumerate(tw_resources):
                # FIXME We may want to use a try block to protect
                # against invalid index access.
                # Add the translation words links section.
                translation_word_links_html = tw_resource.get_translation_word_links(
                    chapter_num,
                    verse_num,
                    usfm_resources[idx]
                    .chapters_content[chapter_num]
                    .chapter_verses[verse_num],
                )
                html.extend(translation_word_links_html)

        # Add the footnotes
        for usfm_resource in usfm_resources:
            try:
                if chapter_footnotes := usfm_resource.chapters_content[
                    chapter_num
                ].chapter_footnotes:
                    html.append(config.get_html_format_string("footnotes"))
                    html.append(chapter_footnotes)
            except KeyError as exception:
                logger.debug(
                    "usfm_resource: {}, does not have chapter: {}".format(
                        usfm_resource, chapter_num
                    )
                )

    # Add the translation word definitions
    for tw_resource in tw_resources:
        # Add the translation words definition section.
        linked_translation_words = tw_resource.get_translation_words_section()
        html.extend(linked_translation_words)

    return model.HtmlContent("\n".join(html))


def _assemble_tn_as_iterator_content_by_verse_for_book_then_lang(
    usfm_resources: List[USFMResource],
    tn_resources: List[TNResource],
    tq_resources: List[TQResource],
    tw_resources: List[TWResource],
    ta_resources: List[TAResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein at least
    tn_resources exists, and TN, TQ, and TW may exist.
    """

    _initialize_resources_html(tn_resources, tq_resources, tw_resources, ta_resources)

    html: List[model.HtmlContent] = []

    # Sort resources by language
    usfm_resources.sort(key=lambda resource: resource.lang_code)
    tn_resources.sort(key=lambda resource: resource.lang_code)
    tq_resources.sort(key=lambda resource: resource.lang_code)
    tw_resources.sort(key=lambda resource: resource.lang_code)
    ta_resources.sort(key=lambda resource: resource.lang_code)

    # Rough sketch of algo that follows:
    # English book intro
    # French book intro
    # chapter heading, e.g., Chapter 1
    #     english chapter intro goes here
    #     french chapter intro goes here
    #         ULB Translation Helps 1:1
    #         translation notes for English goes here
    #         French Translation notes 1:1
    #         translation notes for French goes here
    #         etc for tq, tw links, followed by tw definitions

    # Add book intros for each tn_resource
    for tn_resource in tn_resources:
        # Add the book intro
        book_intro = tn_resource.book_payload.intro_html
        book_intro = _adjust_book_intro_headings(book_intro)
        # book_intros.append(book_intro)
        html.append(model.HtmlContent(book_intro))

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    chapter: model.TNChapterPayload
    # Use the first tn_resource as a chapter_num pump.
    for chapter_num, chapter in tn_resources[0].book_payload.chapters.items():
        chapter_heading = model.HtmlContent("Chapter {}".format(chapter_num))
        html.append(model.HtmlContent(chapter_heading))

        # Add chapter intro for each language
        for tn_resource in tn_resources:
            # Add the translation notes chapter intro.
            chapter_intro = _get_chapter_intro(tn_resource, chapter_num)
            html.append(model.HtmlContent(chapter_intro))

        # Use the first tn_resource as a verse_num pump
        for verse_num, verse in (
            tn_resources[0].book_payload.chapters[chapter_num].verses_html.items()
        ):
            # Add the interleaved tn verses
            for tn_resource in tn_resources:
                tn_verses = tn_resource.get_verses_for_chapter(chapter_num)
                if tn_verses and verse_num in tn_verses:
                    tn_verse_content = tn_resource.format_tn_verse(
                        chapter_num,
                        verse_num,
                        tn_verses[verse_num],
                    )
                    html.extend(tn_verse_content)

            # Add the interleaved tq verses
            for tq_resource in tq_resources:
                tq_verses = tq_resource.get_verses_for_chapter(chapter_num)
                # Add TQ verse content, if any
                if tq_verses and verse_num in tq_verses:
                    tq_verse_content = _format_tq_verse(
                        tq_resource.resource_type_name,
                        chapter_num,
                        verse_num,
                        tq_verses[verse_num],
                    )
                    html.extend(tq_verse_content)

            # Add the interleaved translation word links
            for idx, tw_resource in enumerate(tw_resources):
                # Add the translation words links section.
                if idx in usfm_resources:
                    translation_word_links_html = (
                        tw_resource.get_translation_word_links(
                            chapter_num,
                            verse_num,
                            usfm_resources[idx]
                            .chapters_content[chapter_num]
                            .chapter_verses[verse_num],
                        )
                    )
                    html.extend(translation_word_links_html)

    # Add the translation word definitions
    for tw_resource in tw_resources:
        # Add the translation words definition section.
        linked_translation_words = tw_resource.get_translation_words_section()
        html.extend(linked_translation_words)

    return model.HtmlContent("\n".join(html))


def _assemble_tq_as_iterator_content_by_verse_for_book_then_lang(
    usfm_resources: List[USFMResource],
    tn_resources: List[TNResource],
    tq_resources: List[TQResource],
    tw_resources: List[TWResource],
    ta_resources: List[TAResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a 'by verse' strategy wherein at least
    tq_resources exists, and TQ, and TW may exist.
    """

    _initialize_resources_html(tn_resources, tq_resources, tw_resources, ta_resources)

    html: List[model.HtmlContent] = []

    # Sort resources by language
    usfm_resources.sort(key=lambda r: r.lang_code)
    tn_resources.sort(key=lambda r: r.lang_code)
    tq_resources.sort(key=lambda r: r.lang_code)
    tw_resources.sort(key=lambda r: r.lang_code)
    ta_resources.sort(key=lambda r: r.lang_code)

    # Rough sketch of algo that follows:
    # English book intro
    # French book intro
    # chapter heading, e.g., Chapter 1
    #     english chapter intro goes here
    #     french chapter intro goes here
    #         etc for tq, tw links, followed by tw definitions

    # PEP526 disallows declaration of types in for loops, but allows this.
    chapter_num: model.ChapterNum
    chapter: model.TQChapterPayload
    # Use the first tn_resource as a chapter_num pump.
    for chapter_num, chapter in tq_resources[0].book_payload.chapters.items():
        chapter_heading = model.HtmlContent("Chapter {}".format(chapter_num))
        html.append(model.HtmlContent(chapter_heading))

        # Use the first tq_resource as a verse_num pump
        for verse_num, verse in (
            tq_resources[0].book_payload.chapters[chapter_num].verses_html.items()
        ):
            # Add the interleaved tq verses
            for tq_resource in tq_resources:
                tq_verses = tq_resource.get_verses_for_chapter(chapter_num)
                # Add TQ verse content, if any
                if tq_verses and verse_num in tq_verses:
                    tq_verse_content = _format_tq_verse(
                        tq_resource.resource_type_name,
                        chapter_num,
                        verse_num,
                        tq_verses[verse_num],
                    )
                    html.extend(tq_verse_content)

            # Add the interleaved translation word links
            for idx, tw_resource in enumerate(tw_resources):
                if idx in usfm_resources:
                    # Add the translation words links section.
                    translation_word_links_html = (
                        tw_resource.get_translation_word_links(
                            chapter_num,
                            verse_num,
                            usfm_resources[idx]
                            .chapters_content[chapter_num]
                            .chapter_verses[verse_num],
                        )
                    )
                    html.extend(translation_word_links_html)

    # Add the translation word definitions
    for tw_resource in tw_resources:
        # Add the translation words definition section.
        linked_translation_words = tw_resource.get_translation_words_section()
        html.extend(linked_translation_words)

    return model.HtmlContent("\n".join(html))


def _assemble_tw_as_iterator_content_by_verse_for_book_then_lang(
    usfm_resources: List[USFMResource],
    tn_resources: List[TNResource],
    tq_resources: List[TQResource],
    tw_resources: List[TWResource],
    ta_resources: List[TAResource],
    assembly_substrategy_kind: model.AssemblySubstrategyEnum,
) -> model.HtmlContent:
    """
    Construct the HTML for a only TW.
    """

    _initialize_resources_html(tn_resources, tq_resources, tw_resources, ta_resources)

    html: List[model.HtmlContent] = []

    # Sort resources by language
    usfm_resources.sort(key=lambda r: r.lang_code)
    tn_resources.sort(key=lambda r: r.lang_code)
    tq_resources.sort(key=lambda r: r.lang_code)
    tw_resources.sort(key=lambda r: r.lang_code)
    ta_resources.sort(key=lambda r: r.lang_code)

    # Add the translation word definitions
    for tw_resource in tw_resources:
        # Add the translation words definition section.
        linked_translation_words = tw_resource.get_translation_words_section(
            include_uses_section=False
        )
        html.extend(linked_translation_words)

    return model.HtmlContent("\n".join(html))


######################
## Utility functions


def _initialize_resource_html(
    tn_resource: Optional[TNResource],
    tq_resource: Optional[TQResource],
    tw_resource: Optional[TWResource],
    ta_resource: Optional[TAResource],
) -> None:
    """
    Call initialize_verses_html for each non-USFM resource that is not null.
    """
    tw_resource_dir = None
    if tw_resource:
        # Pass the tw_resource's resource_dir to other resources which
        # in turn will pass it on to the TranslationWordLinkExtension
        # which will handle transformating links for translation
        # words that occur within a translation word asset file itself.
        tw_resource_dir = tw_resource.resource_dir
        tw_resource.initialize_verses_html(tw_resource_dir)
    if tn_resource:
        tn_resource.initialize_verses_html(tw_resource_dir)
    if tq_resource:
        tq_resource.initialize_verses_html(tw_resource_dir)
    if ta_resource:
        ta_resource.initialize_verses_html(tw_resource_dir)


def _initialize_resources_html(
    tn_resources: List[TNResource],
    tq_resources: List[TQResource],
    tw_resources: List[TWResource],
    ta_resources: List[TAResource],
) -> None:
    """
    Call initialize_verses_html for each non-USFM resource.
    """
    tw_resource_dir = None
    for tw_resource in tw_resources:
        # Pass the tw_resource's resource_dir to other resources which
        # in turn will pass it on to the TranslationWordLinkExtension
        # which will handle transforming links for translation
        # words that occur within a translation word asset file itself.
        tw_resource_dir = tw_resource.resource_dir
        tw_resource.initialize_verses_html(tw_resource_dir)
    for tn_resource in tn_resources:
        tw_resource_dir_list = [
            tw_resource.resource_dir
            for tw_resource in tw_resources
            if tn_resource.lang_code == tw_resource.lang_code
            and tn_resource.resource_code == tw_resource.resource_code
        ]
        if tw_resource_dir_list:
            tn_resource.initialize_verses_html(tw_resource_dir_list[0])
        else:
            tn_resource.initialize_verses_html(None)
    for tq_resource in tq_resources:
        tw_resource_dir_list = [
            tw_resource.resource_dir
            for tw_resource in tw_resources
            if tq_resource.lang_code == tw_resource.lang_code
            and tq_resource.resource_code == tw_resource.resource_code
        ]
        if tw_resource_dir_list:
            tq_resource.initialize_verses_html(tw_resource_dir_list[0])
        else:
            tq_resource.initialize_verses_html(None)
    for ta_resource in tq_resources:
        tw_resource_dir_list = [
            tw_resource.resource_dir
            for tw_resource in tw_resources
            if ta_resource.lang_code == tw_resource.lang_code
            and ta_resource.resource_code == tw_resource.resource_code
        ]
        if tw_resource_dir_list:
            ta_resource.initialize_verses_html(tw_resource_dir_list[0])
        else:
            ta_resource.initialize_verses_html(None)


def _format_tq_verse(
    resource_type_name: str,
    chapter_num: model.ChapterNum,
    verse_num: model.VerseRef,
    verse: model.HtmlContent,
) -> List[model.HtmlContent]:
    """
    This is a slightly different form of TQResource.get_tq_verse that is used
    when no USFM or TN has been requested.
    """
    html: List[model.HtmlContent] = []
    html.append(
        model.HtmlContent(
            config.get_html_format_string("resource_type_name_with_ref").format(
                resource_type_name, chapter_num, verse_num
            )
        )
    )
    # Change H1 HTML elements to H4 HTML elements in each translation
    # question.
    html.append(model.HtmlContent(re.sub(r"h1", r"h4", verse)))
    return html


# FIXME TA not implemented yet
# def _format_ta_verse(
#     chapter_num: model.ChapterNum, verse_num: model.VerseRef, verse: model.HtmlContent
# ) -> List[model.HtmlContent]:
#     html: List[model.HtmlContent] = []
#     html.append(
#         model.HtmlContent(
#             config.get_html_format_string("translation_academy").format(
#                 chapter_num, verse_num
#             )
#         )
#     )
#     # Change H1 HTML elements to H4 HTML elements in each translation
#     # question.
#     html.append(model.HtmlContent(re.sub(r"h1", r"h4", verse)))
#     return html


def _get_first_usfm_resource(resources: List[Resource]) -> Optional[USFMResource]:
    """
    Return the first USFMResource instance, if any, contained in resources,
    else return None.
    """
    usfm_resources = [
        resource
        for resource in resources
        if isinstance(resource, USFMResource)
        # NOTE If you wanted to force only certain USFM resource types
        # in the usfm_resource position then you could do something
        # like:
        # resource for resource in resources if isinstance(resource,
        # USFMResource) and resource.resource_type in ["ulb", "cuv",
        # "nav", "ugnt", "uhb", "rsb", "f10", "blv", "ust"]
        # You'd have to choose which USFM resource types based on
        # which ones make sense for TN, TQ, TW, and TA to reference
        # them.
        # NOTE See note on _get_second_usfm_resource for what else
        # would need to be done to support this alternative.
    ]
    return usfm_resources[0] if usfm_resources else None


def _get_second_usfm_resource(resources: List[Resource]) -> Optional[USFMResource]:
    """
    Return the second USFMResource instance, if any, contained in resources,
    else return None.
    """
    usfm_resources = [
        resource for resource in resources if isinstance(resource, USFMResource)
    ]
    return usfm_resources[1] if len(usfm_resources) > 1 else None
    # NOTE This is just a sketch of what you could do if you wanted to
    # only allow certain USFM resource types to be in usfm_resource2
    # position in the interleaving strategy. Currently, the
    # interleaving strategy shows usfm_resource2 at the end of other
    # resources in each chapter, i.e., no TN, TQ, TW, or TA resource
    # referencing it.
    # usfm_resources = [
    #     resource for resource in resources if isinstance(resource,
    #     USFMResource) and resource.resource_type in ["udb"]
    # ]
    # return usfm_resources[0] if usfm_resources else None


def _get_usfm_resources(resources: List[Resource]) -> List[USFMResource]:
    """
    Return the USFMResource instances, if any, contained in resources.
    """
    usfm_resources = [
        resource for resource in resources if isinstance(resource, USFMResource)
    ]
    return usfm_resources


def _get_tn_resource(resources: List[Resource]) -> Optional[TNResource]:
    """
    Return the TNResource instance, if any, contained in resources,
    else return None.
    """
    tn_resources = [
        resource for resource in resources if isinstance(resource, TNResource)
    ]
    return tn_resources[0] if tn_resources else None


def _get_tn_resources(resources: List[Resource]) -> List[TNResource]:
    """
    Return the TNResource instances, if any, contained in resources.
    """
    tn_resources = [
        resource for resource in resources if isinstance(resource, TNResource)
    ]
    return tn_resources


def _get_tw_resource(resources: List[Resource]) -> Optional[TWResource]:
    """
    Return the TWResource instance, if any, contained in resources,
    else return None.
    """
    tw_resources = [
        resource for resource in resources if isinstance(resource, TWResource)
    ]
    return tw_resources[0] if tw_resources else None


def _get_tw_resources(resources: List[Resource]) -> List[TWResource]:
    """
    Return the TWResource instance, if any, contained in resources.
    """
    tw_resources = [
        resource for resource in resources if isinstance(resource, TWResource)
    ]
    return tw_resources


def _get_tq_resource(resources: List[Resource]) -> Optional[TQResource]:
    """
    Return the TQResource instance, if any, contained in resources,
    else return None.
    """
    tq_resources = [
        resource for resource in resources if isinstance(resource, TQResource)
    ]
    return tq_resources[0] if tq_resources else None


def _get_tq_resources(resources: List[Resource]) -> List[TQResource]:
    """
    Return the TQResource instance, if any, contained in resources.
    """
    tq_resources = [
        resource for resource in resources if isinstance(resource, TQResource)
    ]
    return tq_resources


def _get_ta_resource(resources: List[Resource]) -> Optional[TAResource]:
    """
    Return the TAResource instance, if any, contained in resources,
    else return None.
    """
    ta_resources = [
        resource for resource in resources if isinstance(resource, TAResource)
    ]
    return ta_resources[0] if ta_resources else None


def _get_ta_resources(resources: List[Resource]) -> List[TAResource]:
    """
    Return the TAResource instance, if any, contained in resources.
    """
    ta_resources = [
        resource for resource in resources if isinstance(resource, TAResource)
    ]
    return ta_resources


def _adjust_book_intro_headings(book_intro: str) -> model.HtmlContent:
    """Change levels on headings."""
    # Move the H2 out of the way, we'll deal with it last.
    book_intro = re.sub(r"h2", r"h6", book_intro)
    book_intro = re.sub(r"h1", r"h2", book_intro)
    book_intro = re.sub(r"h3", r"h4", book_intro)
    # Now adjust the temporary H6s.
    return model.HtmlContent(re.sub(r"h6", r"h3", book_intro))


def _adjust_chapter_intro_headings(chapter_intro: str) -> model.HtmlContent:
    """Change levels on headings."""
    # Move the H4 out of the way, we'll deal with it last.
    chapter_intro = re.sub(r"h4", r"h6", chapter_intro)
    chapter_intro = re.sub(r"h3", r"h4", chapter_intro)
    chapter_intro = re.sub(r"h1", r"h3", chapter_intro)
    chapter_intro = re.sub(r"h2", r"h4", chapter_intro)
    # Now adjust the temporary H6s.
    return model.HtmlContent(re.sub(r"h6", r"h5", chapter_intro))


def _get_chapter_intro(
    tn_resource: TNResource, chapter_num: model.ChapterNum
) -> model.HtmlContent:
    """Get the chapter intro."""
    if tn_resource and chapter_num in tn_resource.book_payload.chapters:
        chapter_intro = tn_resource.book_payload.chapters[chapter_num].intro_html
    else:
        chapter_intro = model.HtmlContent("")
    # NOTE I am not sure that the 'Links:' section of chapter
    # intro makes sense anymore with the way documents
    # are interleaved.
    # Remove the Links: section of the markdown.
    # chapter_intro = markdown_utils.remove_md_section(chapter_intro, "Links:")
    return _adjust_chapter_intro_headings(chapter_intro)
