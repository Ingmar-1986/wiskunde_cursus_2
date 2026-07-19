for f in *.html
do
  sed -i '/standalone.css/a <link rel="stylesheet" href="base.css">' "$f"
  sed -i '/base.css/a <link rel="stylesheet" href="global.css">' "$f"
done
