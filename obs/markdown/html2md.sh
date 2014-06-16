#!/usr/bin/env sh
# -*- coding: utf8 -*-
#  Copyright (c) 2013 Jesse Griffin
#  http://creativecommons.org/licenses/MIT/
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

# Exports translation notes to Markdown

PROGNAME="${0##*/}"
PANDOC=/usr/bin/pandoc
SRCBASE="/var/www/vhosts/door43.org/ts-exports"
DSTBASE="/var/www/vhosts/door43.org/md-exports"

echo "Converting to Markdown..."
for f in `find "$SRCBASE" -type f -name '*.html'`; do
    dstf="$DSTBASE${f##$SRCBASE}"
    dstdir="${dstf%/*}"
    if [ ! -d "$dstdir" ]; then
        mkdir -p "$dstdir"
    fi
    cat $f | $PANDOC -f html -s -t markdown | \
      sed -e '/obs-.*jpg/d' \
          -e '/en:obs:notes/d' \
          -e 's/(.*)//g' \
          -e 's/\[//g' \
          -e 's/\]//g' | \
      fmt | \
      sed -e 's/ ===/\n===/' \
          -e 's/ ---/\n---/' \
      > ${dstf%.html}.md
done

echo "Unifying..."
MDOBS="$DSTBASE/notes/obs-en-with-notes.md"
rm -f "$MDOBS"
for f in `find "$DSTBASE/notes/frames" -type f -name '*.md' | sort`; do
    cat $f >> "$MDOBS"
done

$PANDOC -f markdown -S -t docx -o ${MDOBS%.md}.docx $MDOBS
#$PANDOC -f markdown -S -t odt -o ${MDOBS%.md}.odt $MDOBS
#$PANDOC -f markdown -S -t pdf -o ${MDOBS%.md}.pdf $MDOBS

#sed  -e 's/?w=640&h=360&tok=[a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9]//' -e 's:_media:var/www/vhosts/door43.org/httpdocs/data/gitrepo/media:' 
