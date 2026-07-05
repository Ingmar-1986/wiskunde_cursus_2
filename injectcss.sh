
for f in *.html
do
  sed -i '/standalone.css/a <link rel="stylesheet" href="global.css">' "$f"
done
