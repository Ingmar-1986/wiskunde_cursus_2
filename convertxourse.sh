#!/bin/bash

for f in testmodule/*.html
do
    echo "Verwerk $f"

    # PARTS
    sed -i "
s#<h1 class='card part' id='part1'>#<div class=\"activity-card card-sectionheading card part\"><div class=\"card-block\"><h4 class=\"card-title\">#g
s#<h1 class='card part' id='part2'>#<div class=\"activity-card card-sectionheading card part\"><div class=\"card-block\"><h4 class=\"card-title\">#g
s#<h1 class='card part' id='part3'>#<div class=\"activity-card card-sectionheading card part\"><div class=\"card-block\"><h4 class=\"card-title\">#g
s#</h1>#</h4></div></div>#g
" "$f"

    # ACTIVITEITEN
    sed -i "
s#<a class='activity card '#<div class=\"activity-card card chapter\" #g
s#</a>#</div>#g
" "$f"

done