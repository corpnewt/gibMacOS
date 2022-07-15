Py2/py3 script that can download macOS components direct from Apple

Can also now build Internet Recovery USB installers from Windows using [dd](http://www.chrysocome.net/dd) and [7zip](https://www.7-zip.org/download.html).

**NOTE:** As of macOS 11 (Big Sur), Apple has changed the way they distribute macOS, and internet recovery USBs can no longer be built via MakeInstall on Windows.  macOS versions through Catalina will still work though.

**NOTE 2:** As of macOS 11 (Big Sur), Apple distributes the OS via an InstallAssistant.pkg file.  `BuildmacOSInstallApp.command` is not needed to create the install application when in macOS in this case - and you can simply run `InstallAssistant.pkg`, which will place the install app in your /Applications folder on macOS.

Thanks to:

* FoxletFox for [FetchMacOS](http://www.insanelymac.com/forum/topic/326366-fetchmacos-a-tool-to-download-macos-on-non-mac-platforms/) and outlining the URL setup
* munki for his [macadmin-scripts](https://github.com/munki/macadmin-scripts)
* timsutton for [brigadier](https://github.com/timsutton/brigadier)
* wolfmannight for [manOSDownloader_rc](https://www.insanelymac.com/forum/topic/338810-create-legit-copy-of-macos-from-apple-catalog/) off which BuildmacOSInstallApp.command is based
