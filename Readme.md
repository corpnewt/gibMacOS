The gibMacOs is a Python2/3 script that can download macOS components direct from Apple and create installers from it.

To run this script simple issue the following command in your terminal:
./gibMacOS.command

This will give you a prompt to select the macOS version you wish to download. After downloading the correct version we can create an installer with:
./BuildmacOSInstallApp.command

Add the download folder as outputed by the first step. An installer will be added to your folder.

You can now create bootable media for your version. For reference check out the official Apple documentation:
https://support.apple.com/en-us/HT201372



Updates:
This script can now also build Internet Recovery USB installers from Windows using [dd](http://www.chrysocome.net/dd) and [7zip](https://www.7-zip.org/download.html).



A special thanks goes out to:

* FoxletFox for [FetchMacOS](http://www.insanelymac.com/forum/topic/326366-fetchmacos-a-tool-to-download-macos-on-non-mac-platforms/) and outlining the URL setup
* munki for his [macadmin-scripts](https://github.com/munki/macadmin-scripts)
* timsutton for [brigadier](https://github.com/timsutton/brigadier)
* wolfmannight for [manOSDownloader_rc](https://www.insanelymac.com/forum/topic/338810-create-legit-copy-of-macos-from-apple-catalog/) off which BuildmacOSInstallApp.command is based
