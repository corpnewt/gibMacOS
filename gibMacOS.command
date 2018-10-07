#!/usr/bin/python
from Scripts import *
import os, datetime, shutil, time, sys, argparse

class gibMacOS:
    def __init__(self):
        self.d = downloader.Downloader()
        self.u = utils.Utils("gibMacOS")
        self.min_w = 80
        self.min_h = 24
        self.u.resize(self.min_w, self.min_h)

        self.catalog_suffix = {
            "public" : "beta",
            "publicrelease" : "",
            "customer" : "customerseed",
            "developer" : "seed"
        }
        self.current_macos = 14
        self.min_macos = 5
        self.mac_os_names_url = {
            "8" : "mountainlion",
            "7" : "lion",
            "6" : "snowleopard",
            "5" : "leopard"
        }
        self.current_catalog = "publicrelease"
        self.catalog_data    = None
        self.scripts = "Scripts"
        self.plist   = "cat.plist"
        self.saves   = "macOS Downloads"
        self.save_local = False
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
        url = url.replace(ver_s, ver_s+self.catalog_suffix[catalog])
        return url

    def get_catalog_data(self, local = False):
        # Gets the data based on our current_catalog
        url = self.build_url(catalog=self.current_catalog, version=self.current_macos)
        self.u.head("Downloading Catalog")
        print("")
        print("Currently downloading {} catalog from\n\n{}\n".format(self.current_catalog, url))
        try:
            b = self.d.get_bytes(url)
            self.catalog_data = plist.loads(b)
            # Assume it's valid data - dump it to a local file
            if local:
                cwd = os.getcwd()
                os.chdir(os.path.dirname(os.path.realpath(__file__)))
                with open(os.path.join(os.getcwd(), self.scripts, self.plist), "wb") as f:
                    plist.dump(self.catalog_data, f)
                os.chdir(cwd)
        except:
            if local:
                # Check if we have one locally in our scripts directory
                if not os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts, self.plist)):
                    return False
                # It does - try to load it
                try:
                    cwd = os.getcwd()
                    os.chdir(os.path.dirname(os.path.realpath(__file__)))
                    with open(os.path.join(os.getcwd(), self.scripts, self.plist), "rb") as f:
                        self.catalog_data = plist.load(f)
                    os.chdir(cwd)
                except:
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
                # Find out if we have any of the recovert_suffixes
                if any(x for x in plist_dict.get("Products",{}).get(p,{}).get("Packages",[]) if x["URL"].endswith(self.recovery_suffixes)):
                    mac_prods.append(p)
        return mac_prods

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
            prod_list.append(prodd)
        # Sort by newest
        prod_list = sorted(prod_list, key=lambda x:x["time"], reverse=True)
        return prod_list

    def download_prod(self, prod, dmg = False):
        # Takes a dictonary of details and downloads it
        self.resize()
        cwd = os.getcwd()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        name = "{} - {} {}".format(prod["product"], prod["version"], prod["title"])
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

    def main(self, dmg = False):
        self.u.head()
        print("")
        print("Available Products:")
        print("")
        num = 0
        w = 0
        if not len(self.mac_prods):
            print("No installers in catalog!")
            print("")
            exit()
        for p in self.mac_prods:
            num += 1
            var1 = "{}. {} {}".format(num, p["title"], p["version"])
            var2 = "   - {} - Added {}".format(p["product"], p["date"])
            if self.find_recovery and p["installer"]:
                # Show that it's a full installer
                var2 += " - FULL Install"
            w = len(var1) if len(var1) > w else w
            w = len(var2) if len(var2) > w else w
            print(var1)
            print(var2)
        print("")
        print("R. Toggle Recovery-Only (Currently {})".format("On" if self.find_recovery else "Off"))
        print("U. Show Catalog URL")
        print("Q. Quit")
        self.resize(w, (num*2)+11)
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
        elif menu[0].lower() == "r":
            self.find_recovery ^= True
            self.u.head("Parsing Data")
            print("")
            print("Re-scanning products after recovery preference toggled...")
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
        self.download_prod(self.mac_prods[-1], dmg)

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
        for p in self.mac_prods:
            if p["version"] == vers:
                self.download_prod(p, dmg)
                return
        print("10.{} not found".format(vers))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--latest", help="downloads the version avaialble in the current catalog (overrides --version and --product)", action="store_true")
    parser.add_argument("-r", "--recovery", help="looks for RecoveryHDUpdate.pkg and RecoveryHDMetaDmg.pkg in lieu of com.apple.mpkg.OSInstall (overrides --dmg)", action="store_true")
    parser.add_argument("-d", "--dmg", help="downloads only the .dmg files", action="store_true")
    parser.add_argument("-c", "--catalog", help="sets the CATALOG to use - publicrelease, public, customer, developer")
    parser.add_argument("-p", "--product", help="sets the product id to search for (overrides --version)")
    parser.add_argument("-v", "--version", help="sets the version of macOS to target - eg 10.14")
    parser.add_argument("-m", "--maxos", help="sets the max macOS version to consider when building the url - eg 10.14")
    args = parser.parse_args()

    g = gibMacOS()
    if args.recovery:
        args.dmg = False
        g.find_recovery = args.recovery

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
