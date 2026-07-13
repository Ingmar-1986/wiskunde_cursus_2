#!/bin/bash

for f in testmodule/*.html
do
    echo "Verwerk $f"

    # standalone.css vervangen door test.css
    sed -i "s#<link href='https://ximera.osu.edu/public/stylesheets/standalone.css' media='screen' rel='stylesheet' />#<link href='https://ximera.osu.edu/public/stylesheets/standalone.css' media='screen' rel='stylesheet' /><link href='../test.css' media='screen' rel='stylesheet' /><link href='../Header_Footer.css' media='screen' rel='stylesheet' />#g" "$f"

sed -i 's#<body>#<body>\n<!--HEADER-->#' "$f"

sed -i '/<!--HEADER-->/r Header.html' "$f"

sed -i '/<!--HEADER-->/d' "$f"

sed -i 's#<body>#<body>\n<!--INTRO-->#' "$f"

sed -i '/<!--INTRO-->/r ModuleIntro.html' "$f"

sed -i '/<!--INTRO-->/d' "$f"

sed -i '/<\/body>/i\
PLACEHOLDER_FOOTER
' "$f"

sed -i '/PLACEHOLDER_FOOTER/r Footer.html' "$f"
sed -i '/PLACEHOLDER_FOOTER/d' "$f"
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