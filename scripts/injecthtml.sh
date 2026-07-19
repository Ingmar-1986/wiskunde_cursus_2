#!/bin/bash

for f in *.html
do
    title=$(grep -oP '(?<=<title>).*?(?=</title>)' "$f")

    sed "s/__TITLE__/$title/" navbar.html > navbar_tmp.html

    grep -q "<nav class=\"navbar" "$f" && continue

    sed -i '/<body>/r navbar_tmp.html' "$f"
done     