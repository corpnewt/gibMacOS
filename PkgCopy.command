# Python has an issue with this syntax
mv macOS\ Downloads/*/*/* .
# Also download clover while we are at it
rm download_url.list
curl -sL https://api.github.com/repos/dids/clover-builder/releases/latest | jq -r '.assets[].browser_download_url' >> download_url.list
