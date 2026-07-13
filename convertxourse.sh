#!/bin/bash

for f in testmodule/*.html
do
    echo "Verwerk $f"

    # standalone.css vervangen door test.css
    sed -i "s#<link href='https://ximera.osu.edu/public/stylesheets/standalone.css' media='screen' rel='stylesheet' />#<link href='https://ximera.osu.edu/public/stylesheets/standalone.css' media='screen' rel='stylesheet' /><link href='../test.css' media='screen' rel='stylesheet' />#g" "$f"

    # Parts omzetten naar KU Leuven-achtige secties
    sed -i "
s#<h1 class='card part' id='part1'>#<div class=\"activity-card card-sectionheading card part\"><div class=\"card-block\"><h4 class=\"card-title\">#g
s#<h1 class='card part' id='part2'>#<div class=\"activity-card card-sectionheading card part\"><div class=\"card-block\"><h4 class=\"card-title\">#g
s#<h1 class='card part' id='part3'>#<div class=\"activity-card card-sectionheading card part\"><div class=\"card-block\"><h4 class=\"card-title\">#g
s#</h1>#</h4></div></div>#g
" "$f"

    # Storende p-tags verwijderen
    sed -i 's#<p>##g' "$f"
    sed -i 's#</p>##g' "$f"

done