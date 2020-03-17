#!/usr/bin/env python
from Scripts import *
import os, datetime, shutil, time, sys, argparse

class gibMacOS:
    def __init__(self):
        self.d = downloader.Downloader()
        self.u = utils.Utils("gibMacOS")
        self.r = run.Run()
        self.min_w = 80
        self.min_h = 24
        self.u.resize(self.min_w, self.min_h)

        self.catalog_suffix = {
            "public" : "beta",
            "publicrelease" : "",
            "customer" : "customerseed",
            "developer" : "seed"
        }
        self.current_macos = 15
        self.min_macos = 5
        self.print_urls = False
        self.mac_os_names_url = {
            "8" : "mountainlion",
            "7" : "lion",
            "6" : "snowleopard",
            "5" : "leopard"
        }
        self.version_names = {
            "tiger" : "10.4",
            "leopard" : "10.5",
            "snow leopard" : "10.6",
            "lion" : "10.7",
            "mountain lion" : "10.8",
            "mavericks" : "10.9",
            "yosemite" : "10.10",
            "el capitan" : "10.11",
            "sierra" : "10.12",
            "high sierra" : "10.13",
            "mojave" : "10.14",
            "catalina" : "10.15"
        }
        self.current_catalog = "publicrelease"
        self.catalog_data    = None
        self.scripts = "Scripts"
        self.plist   = "sucatalog.plist"
        self.saves   = "macOS Downloads"
        self.save_local = False
        self.force_local = False
        self.find_recovery = False
        self.recovery_suffixes = (
            "RecoveryHDUpdate.pkg",
            "RecoveryHDMetaDmg.pkg"
        )

    def resize(self, width=0, height=0):
        if os.name=="nt":
            # Winders resizing is dumb... bail
            return
        width = width if width > self.min_w else self.min_w
        height = height if height > self.min_h else self.min_h
        self.u.resize(width, height)

    def set_prods(self):
        self.resize()
        if not self.get_catalog_data(self.save_local):
            self.u.head("Catalog Data Error")
            print("")
            print("The currently selected catalog ({}) was not reachable".format(self.current_catalog))
            if self.save_local:
                print("and I was unable to locate a valid {} file in the\n{} directory.".format(self.plist, self.scripts))
            print("Please ensure you have a working internet connection.")
            print("")
            self.u.grab("Press [enter] to exit...")
        self.mac_prods = self.get_dict_for_prods(self.get_installers())

    def set_catalog(self, catalog):
        self.current_catalog = catalog.lower() if catalog.lower() in self.catalog_suffix else "publicrelease"

    def build_url(self, **kwargs):
        catalog = kwargs.get("catalog", self.current_catalog).lower()
        catalog = catalog if catalog.lower() in self.catalog_suffix else "publicrelease"
        version = int(kwargs.get("version", self.current_macos))
        url = "https://swscan.apple.com/content/catalogs/others/index-"
        url += "-".join([self.mac_os_names_url[str(x)] if str(x) in self.mac_os_names_url else "10."+str(x) for x in reversed(range(self.min_macos, version+1))])
        url += ".merged-1.sucatalog"
        ver_s = self.mac_os_names_url[str(version)] if str(version) in self.mac_os_names_url else "10."+str(version)
        if len(self.catalog_suffix[catalog]):
            url = url.replace(ver_s, ver_s+self.catalog_suffix[catalog]+"-"+ver_s)
        return url

    def get_catalog_data(self, local = False):
        # Gets the data based on our current_catalog
        url = self.build_url(catalog=self.current_catalog, version=self.current_macos)
        self.u.head("Downloading Catalog")
        print("")
        if local:
            print("Checking locally for {}".format(self.plist))
            cwd = os.getcwd()
            os.chdir(os.path.dirname(os.path.realpath(__file__)))
            if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts, self.plist)):
                print(" - Found - loading...")
                try:
                    with open(os.path.join(os.getcwd(), self.scripts, self.plist), "rb") as f:
                        self.catalog_data = plist.load(f)
                    os.chdir(cwd)
                    return True
                except:
                    print(" - Error loading - downloading instead...\n")
                    os.chdir(cwd)
            else:
                print(" - Not found - downloading instead...\n")
        print("Currently downloading {} catalog from\n\n{}\n".format(self.current_catalog, url))
        try:
            b = self.d.get_bytes(url)
            print("")
            self.catalog_data = plist.loads(b)
        except:
            print("Error downloading!")
            return False
        try:
            # Assume it's valid data - dump it to a local file
            if local or self.force_local:
                print(" - Saving to {}...".format(self.plist))
                cwd = os.getcwd()
                os.chdir(os.path.dirname(os.path.realpath(__file__)))
                with open(os.path.join(os.getcwd(), self.scripts, self.plist), "wb") as f:
                    plist.dump(self.catalog_data, f)
                os.chdir(cwd)
        except:
            print(" - Error saving!")
            return False
        return True

    def get_installers(self, plist_dict = None):
        if not plist_dict:
            plist_dict = self.catalog_data
        if not plist_dict:
            return []
        mac_prods = []
        for p in plist_dict.get("Products", {}):
            if not self.find_recovery:
                if plist_dict.get("Products",{}).get(p,{}).get("ExtendedMetaInfo",{}).get("InstallAssistantPackageIdentifiers",{}).get("OSInstall",{}) == "com.apple.mpkg.OSInstall":
                    mac_prods.append(p)
            else:
                # Find out if we have any of the recovery_suffixes
                if any(x for x in plist_dict.get("Products",{}).get(p,{}).get("Packages",[]) if x["URL"].endswith(self.recovery_suffixes)):
                    mac_prods.append(p)
        return mac_prods

    def get_build_version(self, dist_dict):
        build = version = "Unknown"
        try:
            dist_url = dist_dict.get("English","") if dist_dict.get("English",None) else dist_dict.get("en","")
            dist_file = self.d.get_bytes(dist_url, False).decode("utf-8")
        except:
            dist_file = ""
            pass
        build_search = "macOSProductBuildVersion" if "macOSProductBuildVersion" in dist_file else "BUILD"
        vers_search  = "macOSProductVersion" if "macOSProductVersion" in dist_file else "VERSION"
        try:
            build = dist_file.split("<key>{}</key>".format(build_search))[1].split("<string>")[1].split("</string>")[0]
        except:
            pass
        try:
            version = dist_file.split("<key>{}</key>".format(vers_search))[1].split("<string>")[1].split("</string>")[0]
        except:
            pass
        return (build,version)

    def get_dict_for_prods(self, prods, plist_dict = None):
        if plist_dict==self.catalog_data==None:
            plist_dict = {}
        else:
            plist_dict = self.catalog_data if plist_dict == None else plist_dict

        prod_list = []
        for prod in prods:
            # Grab the ServerMetadataURL for the passed product key if it exists
            prodd = {"product":prod}
            try:
                b = self.d.get_bytes(plist_dict.get("Products",{}).get(prod,{}).get("ServerMetadataURL",""), False)
                smd = plist.loads(b)
            except:
                smd = {}
            # Populate some info!
            prodd["date"] = plist_dict.get("Products",{}).get(prod,{}).get("PostDate","")
            prodd["installer"] = False
            if plist_dict.get("Products",{}).get(prod,{}).get("ExtendedMetaInfo",{}).get("InstallAssistantPackageIdentifiers",{}).get("OSInstall",{}) == "com.apple.mpkg.OSInstall":
                prodd["installer"] = True
            prodd["time"] = time.mktime(prodd["date"].timetuple()) + prodd["date"].microsecond / 1E6
            prodd["title"] = smd.get("localization",{}).get("English",{}).get("title","Unknown")
            prodd["version"] = smd.get("CFBundleShortVersionString","Unknown")
            if prodd["version"] == " ":
                prodd["version"] = ""
            # Try to get the description too
            try:
                desc = smd.get("localization",{}).get("English",{}).get("description","").decode("utf-8")
                desctext = desc.split('"p1">')[1].split("</a>")[0]
            except:
                desctext = None
            prodd["description"] = desctext
            # Iterate the available packages and save their urls and sizes
            if self.find_recovery:
                # Only get the recovery packages
                prodd["packages"] = [x for x in plist_dict.get("Products",{}).get(prod,{}).get("Packages",[]) if x["URL"].endswith(self.recovery_suffixes)]
            else:
                # Add them all!
                prodd["packages"] = plist_dict.get("Products",{}).get(prod,{}).get("Packages",[])
            # Attempt to get the build/version info from the dist
            b,v = self.get_build_version(plist_dict.get("Products",{}).get(prod,{}).get("Distributions",{}))
            prodd["build"] = b
            if not v.lower() == "unknown":
                prodd["version"] = v
            prod_list.append(prodd)
        # Sort by newest
        prod_list = sorted(prod_list, key=lambda x:x["time"], reverse=True)
        return prod_list

    def download_prod(self, prod, dmg = False):
        # Takes a dictonary of details and downloads it
        self.resize()
        name = "{} - {} {}".format(prod["product"], prod["version"], prod["title"]).replace(":","").strip()
        dl_list = []
        for x in prod["packages"]:
            if not x.get("URL",None):
                continue
            if dmg and not x.get("URL","").lower().endswith(".dmg"):
                continue
            # add it to the list
            dl_list.append(x["URL"])
        if not len(dl_list):
            self.u.head("Error")
            print("")
            print("There were no files to download")
            print("")
            self.u.grab("Press [enter] to return...")
            return
        c = 0
        done = []
        if self.print_urls:
            self.u.head("Download Links")
            print("")
            print("{}:\n".format(name))
            print("\n".join([" - {} \n   --> {}".format(os.path.basename(x), x) for x in dl_list]))
            print("")
            self.u.grab("Press [enter] to return...")
            return
        # Only check the dirs if we need to
        cwd = os.getcwd()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        if os.path.exists(os.path.join(os.getcwd(), self.saves, self.current_catalog, name)):
            while True:
                self.u.head("Already Exists")
                print("")
                print("It looks like you've already downloaded {}".format(name))
                print("")
                menu = self.u.grab("Redownload? (y/n):  ")
                if not len(menu):
                    continue
                if menu[0].lower() == "n":
                    return
                if menu[0].lower() == "y":
                    break
            # Remove the old copy, then re-download
            shutil.rmtree(os.path.join(os.getcwd(), self.saves, self.current_catalog, name))
        # Make it new
        os.makedirs(os.path.join(os.getcwd(), self.saves, self.current_catalog, name))
        for x in dl_list:
            c += 1
            self.u.head("Downloading File {} of {}".format(c, len(dl_list)))
            print("")
            if len(done):
                print("\n".join(["{} --> {}".format(y["name"], "Succeeded" if y["status"] else "Failed") for y in done]))
                print("")
            if dmg:
                print("NOTE: Only Downloading DMG Files")
                print("")
            print("Downloading {} for {}...".format(os.path.basename(x), name))
            print("")
            try:
                self.d.stream_to_file(x, os.path.join(os.getcwd(), self.saves, self.current_catalog, name, os.path.basename(x)))
                done.append({"name":os.path.basename(x), "status":True})
            except:
                done.append({"name":os.path.basename(x), "status":False})
        succeeded = [x for x in done if x["status"]]
        failed    = [x for x in done if not x["status"]]
        self.u.head("Downloaded {} of {}".format(len(succeeded), len(dl_list)))
        print("")
        print("Succeeded:")
        if len(succeeded):
            for x in succeeded:
                print("  {}".format(x["name"]))
        else:
            print("  None")
        print("")
        print("Failed:")
        if len(failed):
            for x in failed:
                print("  {}".format(x["name"]))
        else:
            print("  None")
        print("")
        print("Files saved to:")
        print("  {}".format(os.path.join(os.getcwd(), self.saves, self.current_catalog, name)))
        print("")
        self.u.grab("Press [enter] to return...")

    def show_catalog_url(self):
        self.resize()
        self.u.head()
        print("")
        print("Current Catalog:   {}".format(self.current_catalog))
        print("Max macOS Version: 10.{}".format(self.current_macos))
        print("")
        print("{}".format(self.build_url()))
        print("")
        menu = self.u.grab("Press [enter] to return...")
        return

    def pick_catalog(self):
        self.resize()
        self.u.head("Select SU Catalog")
        print("")
        count = 0
        for x in self.catalog_suffix:
            count += 1
            print("{}. {}".format(count, x))
        print("")
        print("M. Main Menu")
        print("Q. Quit")
        print("")
        menu = self.u.grab("Please select an option:  ")
        if not len(menu):
            self.pick_catalog()
            return
        if menu[0].lower() == "m":
            return
        elif menu[0].lower() == "q":
            self.u.custom_quit()
        # Should have something to test here
        try:
            i = int(menu)
            self.current_catalog = list(self.catalog_suffix)[i-1]
        except:
            # Incorrect - try again
            self.pick_catalog()
            return
        # If we made it here - then we got something
        # Reload with the proper catalog
        self.get_catalog_data()

    def pick_macos(self):
        self.resize()
        self.u.head("Select Max macOS Version")
        print("")
        print("Currently set to 10.{}".format(self.current_macos))
        print("")
        print("M. Main Menu")
        print("Q. Quit")
        print("")
        menu = self.u.grab("Please type the max macOS version for the catalog url (10.xx format):  ")
        if not len(menu):
            self.pick_macos()
            return
        if menu[0].lower() == "m":
            return
        elif menu[0].lower() == "q":
            self.u.custom_quit()
        # At this point - we should have something in 10.xx format
        parts = menu.split(".")
        if len(parts) > 2 or len(parts) < 2 or parts[0] != "10":
            self.pick_macos()
            return
        # Got the right format
        try:
            self.current_macos = int(parts[1])
        except:
            # Not an int
            self.pick_macos()
            return
        # At this point, we should be good
        self.get_catalog_data()

    def main(self, dmg = False):
        self.u.head()
        print("")
        print("Available Products:")
        print("")
        num = 0
        w = 0
        pad = 12
        if not len(self.mac_prods):
            print("No installers in catalog!")
            print("")
        for p in self.mac_prods:
            num += 1
            var1 = "{}. {} {}".format(num, p["title"], p["version"])
            if p["build"].lower() != "unknown":
                var1 += " ({})".format(p["build"])
            var2 = "   - {} - Added {}".format(p["product"], p["date"])
            if self.find_recovery and p["installer"]:
                # Show that it's a full installer
                var2 += " - FULL Install"
            w = len(var1) if len(var1) > w else w
            w = len(var2) if len(var2) > w else w
            print(var1)
            print(var2)
        print("")
        print("M. Change Max-OS Version (Currently 10.{})".format(self.current_macos))
        print("C. Change Catalog (Currently {})".format(self.current_catalog))
        print("I. Only Print URLs (Currently {})".format(self.print_urls))
        if sys.platform.lower() == "darwin":
            pad += 2
            print("S. Set Current Catalog to SoftwareUpdate Catalog")
            print("L. Clear SoftwareUpdate Catalog")
        print("R. Toggle Recovery-Only (Currently {})".format("On" if self.find_recovery else "Off"))
        print("U. Show Catalog URL")
        print("Q. Quit")
        self.resize(w, (num*2)+pad)
        if os.name=="nt":
            # Formatting differences..
            print("")
        menu = self.u.grab("Please select an option:  ")
        if not len(menu):
            return
        if menu[0].lower() == "q":
            self.resize()
            self.u.custom_quit()
        elif menu[0].lower() == "u":
            self.show_catalog_url()
            return
        elif menu[0].lower() == "m":
            self.pick_macos()
        elif menu[0].lower() == "c":
            self.pick_catalog()
        elif menu[0].lower() == "i":
            self.print_urls ^= True
            return
        elif menu[0].lower() == "l" and sys.platform.lower() == "darwin":
            # Clear the software update catalog
            self.u.head("Clearing SU CatalogURL")
            print("")
            print("sudo softwareupdate --clear-catalog")
            self.r.run({"args":["softwareupdate","--clear-catalog"],"sudo":True})
            print("")
            self.u.grab("Done.", timeout=5)
            return
        elif menu[0].lower() == "s" and sys.platform.lower() == "darwin":
            # Set the software update catalog to our current catalog url
            self.u.head("Setting SU CatalogURL")
            print("")
            url = self.build_url(catalog=self.current_catalog, version=self.current_macos)
            print("Setting catalog URL to:\n{}".format(url))
            print("")
            print("sudo softwareupdate --set-catalog {}".format(url))
            self.r.run({"args":["softwareupdate","--set-catalog",url],"sudo":True})
            print("")
            self.u.grab("Done",timeout=5)
            return
        elif menu[0].lower() == "r":
            self.find_recovery ^= True
        if menu[0].lower() in ["m","c","r"]:
            self.u.head("Parsing Data")
            print("")
            print("Re-scanning products after url preference toggled...")
            self.mac_prods = self.get_dict_for_prods(self.get_installers())
            return
        
        # Assume we picked something
        try:
            menu = int(menu)
        except:
            return
        if menu < 1 or menu > len(self.mac_prods):
            return
        self.download_prod(self.mac_prods[menu-1], dmg)

    def get_latest(self, dmg = False):
        self.u.head("Downloading Latest")
        print("")
        self.download_prod(sorted(self.mac_prods, key=lambda x:x['version'], reverse=True)[0], dmg)

    def get_for_product(self, prod, dmg = False):
        self.u.head("Downloading for {}".format(prod))
        print("")
        for p in self.mac_prods:
            if p["product"] == prod:
                self.download_prod(p, dmg)
                return
        print("{} not found".format(prod))

    def get_for_version(self, vers, dmg = False):
        self.u.head("Downloading for {}".format(vers))
        print("")
        # Map the versions to their names
        v = self.version_names.get(vers.lower(),vers.lower())
        v_dict = {}
        for n in self.version_names:
            v_dict[self.version_names[n]] = n
        n = v_dict.get(v, v)
        for p in sorted(self.mac_prods, key=lambda x:x['version'], reverse=True):
            pt = p["title"].lower()
            pv = p["version"].lower()
            # Need to compare verisons - n = name, v = version
            # p["version"] and p["title"] may contain either the version
            # or name - so check both
            # We want to make sure, if we match the name to the title, that we only match
            # once - so Sierra/High Sierra don't cross-match
            #
            # First check if p["version"] isn't " " or "1.0"
            if not pv in [" ","1.0"]:
                # Have a real version - match this first
                if pv.startswith(v):
                    self.download_prod(p, dmg)
                    return
            # Didn't match the version - or version was bad, let's check
            # the title
            # Need to make sure n is in the version name, but not equal to it,
            # and the version name is in p["title"] to disqualify
            # i.e. - "Sierra" exists in "High Sierra", but does not equal "High Sierra"
            # and "High Sierra" is in "macOS High Sierra 10.13.6" - This would match
            name_match = [x for x in self.version_names if n in x and x != n and x in pt]
            if (n in pt) and not len(name_match):
                self.download_prod(p, dmg)
                return
        print("'{}' not found".format(vers))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--latest", help="downloads the version available in the current catalog (overrides --version and --product)", action="store_true")
    parser.add_argument("-r", "--recovery", help="looks for RecoveryHDUpdate.pkg and RecoveryHDMetaDmg.pkg in lieu of com.apple.mpkg.OSInstall (overrides --dmg)", action="store_true")
    parser.add_argument("-d", "--dmg", help="downloads only the .dmg files", action="store_true")
    parser.add_argument("-s", "--savelocal", help="uses a locally saved sucatalog.plist if exists", action="store_true")
    parser.add_argument("-n", "--newlocal", help="downloads and saves locally, overwriting any prior local sucatalog.plist", action="store_true")
    parser.add_argument("-c", "--catalog", help="sets the CATALOG to use - publicrelease, public, customer, developer")
    parser.add_argument("-p", "--product", help="sets the product id to search for (overrides --version)")
    parser.add_argument("-v", "--version", help="sets the version of macOS to target - eg '-v 10.14' or '-v Yosemite'")
    parser.add_argument("-m", "--maxos", help="sets the max macOS version to consider when building the url - eg 10.14")
    parser.add_argument("-i", "--print-urls", help="only prints the download URLs, does not actually download them", action="store_true")
    args = parser.parse_args()

    g = gibMacOS()
    if args.recovery:
        args.dmg = False
        g.find_recovery = args.recovery

    if args.savelocal:
        g.save_local = True

    if args.newlocal:
        g.force_local = True

    if args.print_urls:
        g.print_urls = True

    if args.maxos:
        try:
            m = int(str(args.maxos).replace("10.",""))
            g.current_macos = m
        except:
            pass
    if args.catalog:
        # Set the catalog
        g.set_catalog(args.catalog)

    # Done setting up pre-requisites
    g.set_prods()

    if args.latest:
        g.get_latest(args.dmg)
        exit()
    if args.product != None:
        g.get_for_product(args.product, args.dmg)
        exit()
    if args.version != None:
        g.get_for_version(args.version, args.dmg)
        exit()

    while True:
        g.main(args.dmg)
