#!/usr/bin/env python3
from Scripts import downloader,utils,run,plist
import os, shutil, time, sys, argparse, re, json

class ProgramError(Exception):
    def __init__(self, message, title = "Error"):
        super(Exception, self).__init__(message)
        self.title = title


class gibMacOS:
    def __init__(self, interactive = True, download_dir = None):
        self.interactive = interactive
        self.download_dir = download_dir
        self.d = downloader.Downloader()
        self.u = utils.Utils("gibMacOS", interactive=interactive)
        self.r = run.Run()
        self.min_w = 80
        self.min_h = 24
        if os.name == "nt":
            self.min_w = 120
            self.min_h = 30
        self.resize()

        self.catalog_suffix = {
            "public" : "beta",
            "publicrelease" : "",
            "customer" : "customerseed",
            "developer" : "seed"
        }
        
        # Load settings.json if it exists in the Scripts folder
        self.settings_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"Scripts","settings.json")
        self.settings = {}
        if os.path.exists(self.settings_path):
            try: self.settings = json.load(open(self.settings_path))
            except: pass
        
        self.current_macos = self.settings.get("current_macos",20) # if > 16, assume X-5, else 10.X
        self.min_macos = 5
        self.print_urls = self.settings.get("print_urls",False)
        self.print_json = False
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
            "catalina" : "10.15",
            "big sur" : "11",
            "monterey" : "12",
            "ventura" : "13",
            "sonoma" : "14",
            "sequoia" : "15"
        }
        self.current_catalog = self.settings.get("current_catalog","publicrelease")
        self.catalog_data    = None
        self.scripts = "Scripts"
        self.plist   = "sucatalog.plist"
        self.save_local = False
        self.force_local = False
        self.find_recovery = self.settings.get("find_recovery",False)
        self.recovery_suffixes = (
            "RecoveryHDUpdate.pkg",
            "RecoveryHDMetaDmg.pkg"
        )
        self.settings_to_save = (
            "current_macos",
            "current_catalog",
            "print_urls",
            "find_recovery"
        )

    def resize(self, width=0, height=0):
        if not self.interactive:
            return
        width = width if width > self.min_w else self.min_w
        height = height if height > self.min_h else self.min_h
        self.u.resize(width, height)

    def save_settings(self):
        # Ensure we're using the latest values
        for setting in self.settings_to_save:
            self.settings[setting] = getattr(self,setting,None)
        try:
            json.dump(self.settings,open(self.settings_path,"w"),indent=2)
        except Exception as e:
            raise ProgramError(
                    "Failed to save settings to:\n\n{}\n\nWith error:\n\n - {}\n".format(self.settings_path,repr(e)),
                    title="Error Saving Settings")

    def set_prods(self):
        self.resize()
        if not self.get_catalog_data(self.save_local):
            message = "The currently selected catalog ({}) was not reachable\n".format(self.current_catalog)
            if self.save_local:
                message += "and I was unable to locate a valid {} file in the\n{} directory.\n".format(self.plist, self.scripts)
            message += "Please ensure you have a working internet connection."
            raise ProgramError(message, title="Catalog Data Error")
        self.u.head("Parsing Data")
        self.u.info("Scanning products after catalog download...\n")
        self.mac_prods = self.get_dict_for_prods(self.get_installers())

    def set_catalog(self, catalog):
        self.current_catalog = catalog.lower() if catalog.lower() in self.catalog_suffix else "publicrelease"

    def num_to_macos(self,macos_num,for_url=True):
        if for_url: # Resolve 8-5 to their names and show Big Sur as 10.16
            return self.mac_os_names_url.get(str(macos_num),"10.{}".format(macos_num)) if macos_num <= 16 else str(macos_num-5)
        # Return 10.xx for anything Catalina and lower, otherwise 11+
        return "10.{}".format(macos_num) if macos_num <= 15 else str(macos_num-5)

    def macos_to_num(self,macos):
        try:
            macos_parts = [int(x) for x in macos.split(".")][:2 if macos.startswith("10.") else 1]
            if macos_parts[0] == 11: macos_parts = [10,16] # Big sur
        except:
            return None
        if len(macos_parts) > 1: return macos_parts[1]
        return 5+macos_parts[0]

    def get_macos_versions(self,minos=None,maxos=None,catalog=""):
        if minos is None: minos = self.min_macos
        if maxos is None: maxos = self.current_macos
        if minos > maxos: minos,maxos = maxos,minos # Ensure min is less than or equal
        os_versions = [self.num_to_macos(x,for_url=True) for x in range(minos,maxos+1)]
        if catalog:
            # We have a custom catalog - prepend the first entry + catalog to the list
            custom_cat_entry = os_versions[-1]+catalog
            os_versions.append(custom_cat_entry)
        return os_versions

    def build_url(self, **kwargs):
        catalog = kwargs.get("catalog", self.current_catalog).lower()
        catalog = catalog if catalog.lower() in self.catalog_suffix else "publicrelease"
        version = int(kwargs.get("version", self.current_macos))
        return "https://swscan.apple.com/content/catalogs/others/index-{}.merged-1.sucatalog".format(
            "-".join(reversed(self.get_macos_versions(self.min_macos,version,catalog=self.catalog_suffix.get(catalog,""))))
        )

    def get_catalog_data(self, local = False):
        # Gets the data based on our current_catalog
        url = self.build_url(catalog=self.current_catalog, version=self.current_macos)
        self.u.head("Downloading Catalog")
        if local:
            self.u.info("Checking locally for {}".format(self.plist))
            cwd = os.getcwd()
            os.chdir(os.path.dirname(os.path.realpath(__file__)))
            if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts, self.plist)):
                self.u.info(" - Found - loading...")
                try:
                    with open(os.path.join(os.getcwd(), self.scripts, self.plist), "rb") as f:
                        self.catalog_data = plist.load(f)
                    os.chdir(cwd)
                    return True
                except:
                    self.u.info(" - Error loading - downloading instead...\n")
                    os.chdir(cwd)
            else:
                self.u.info(" - Not found - downloading instead...\n")
        self.u.info("Currently downloading {} catalog from:\n\n{}\n".format(self.current_catalog, url))
        try:
            b = self.d.get_bytes(url, self.interactive)
            self.u.info("")
            self.catalog_data = plist.loads(b)
        except:
            self.u.info("Error downloading!")
            return False
        try:
            # Assume it's valid data - dump it to a local file
            if local or self.force_local:
                self.u.info(" - Saving to {}...".format(self.plist))
                cwd = os.getcwd()
                os.chdir(os.path.dirname(os.path.realpath(__file__)))
                with open(os.path.join(os.getcwd(), self.scripts, self.plist), "wb") as f:
                    plist.dump(self.catalog_data, f)
                os.chdir(cwd)
        except:
            self.u.info(" - Error saving!")
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
                val = plist_dict.get("Products",{}).get(p,{}).get("ExtendedMetaInfo",{}).get("InstallAssistantPackageIdentifiers",{})
                if val.get("OSInstall",{}) == "com.apple.mpkg.OSInstall" or val.get("SharedSupport","").startswith("com.apple.pkg.InstallAssistant"):
                    mac_prods.append(p)
            else:
                # Find out if we have any of the recovery_suffixes
                if any(x for x in plist_dict.get("Products",{}).get(p,{}).get("Packages",[]) if x["URL"].endswith(self.recovery_suffixes)):
                    mac_prods.append(p)
        return mac_prods

    def get_build_version(self, dist_dict):
        build = version = name = "Unknown"
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
        try:
            name = re.search(r"<title>(.+?)</title>",dist_file).group(1)
        except:
            pass
        try:
            # XXX: This is parsing a JavaScript array from the script part of the dist file.
            device_ids = re.search(r"var supportedDeviceIDs\s*=\s*\[([^]]+)\];", dist_file)[1]
            device_ids = set(i.lower() for i in re.findall(r"'([^',]+)'", device_ids))
        except:
            device_ids = set()
        return (build,version,name,device_ids)

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
            prodd["installer"] = plist_dict.get("Products",{}).get(prod,{}).get("ExtendedMetaInfo",{}).get("InstallAssistantPackageIdentifiers",{}).get("OSInstall",{}) == "com.apple.mpkg.OSInstall"
            prodd["time"] = time.mktime(prodd["date"].timetuple()) + prodd["date"].microsecond / 1E6
            prodd["version"] = smd.get("CFBundleShortVersionString","Unknown").strip()
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
            # Get size
            prodd["size"] = self.d.get_size(sum([i["Size"] for i in prodd["packages"]]))
            # Attempt to get the build/version/name/device-ids info from the dist
            prodd["build"],v,n,prodd["device_ids"] = self.get_build_version(plist_dict.get("Products",{}).get(prod,{}).get("Distributions",{}))
            prodd["title"] = smd.get("localization",{}).get("English",{}).get("title",n)
            self.u.info(" -->{}. {} ({}){}".format(
                str(len(prod_list)+1).rjust(3),
                prodd["title"],
                prodd["build"],
                " - FULL Install" if self.find_recovery and prodd["installer"] else ""
            ))
            if v.lower() != "unknown":
                prodd["version"] = v
            prod_list.append(prodd)
        # Sort by newest
        prod_list = sorted(prod_list, key=lambda x:x["time"], reverse=True)
        return prod_list

    def download_prod(self, prod, dmg = False):
        # Takes a dictonary of details and downloads it
        self.resize()
        name = "{} - {} {} ({})".format(prod["product"], prod["version"], prod["title"], prod["build"]).replace(":","").strip()
        download_dir = self.download_dir or os.path.join(os.path.dirname(os.path.realpath(__file__)), "macOS Downloads", self.current_catalog, name)
        dl_list = []
        for x in prod["packages"]:
            if not x.get("URL",None):
                continue
            if dmg and not x.get("URL","").lower().endswith(".dmg"):
                continue
            # add it to the list
            dl_list.append(x)
        if not len(dl_list):
            raise ProgramError("There were no files to download")
        done = []
        if self.print_json:
            print(self.product_to_json(prod))
            if self.interactive:
                print("")
                self.u.grab("Press [enter] to return...")
            return
        elif self.print_urls:
            self.u.head("Download Links")
            print("{}:\n".format(name))
            print("\n".join([" - {} ({}) \n   --> {}".format(
                os.path.basename(x["URL"]),
                self.d.get_size(x["Size"],strip_zeroes=True) if x.get("Size") is not None else "?? MB",
                x["URL"]
            ) for x in dl_list]))
            if self.interactive:
                print("")
                self.u.grab("Press [enter] to return...")
            return
        # Only check the dirs if we need to
        if self.download_dir is None and os.path.exists(download_dir):
            while True:
                self.u.head("Already Exists")
                self.u.info("It looks like you've already downloaded {}\n".format(name))
                if not self.interactive:
                    return
                menu = self.u.grab("Redownload? (y/n):  ")
                if not len(menu):
                    continue
                if menu[0].lower() == "n":
                    return
                if menu[0].lower() == "y":
                    break
            # Remove the old copy, then re-download
            shutil.rmtree(download_dir)
        # Make it new
        os.makedirs(download_dir)
        for c,x in enumerate(dl_list,start=1):
            url = x["URL"]
            self.u.head("Downloading File {} of {}".format(c, len(dl_list)))
            if len(done):
                self.u.info("\n".join(["{} --> {}".format(y["name"], "Succeeded" if y["status"] else "Failed") for y in done]))
                self.u.info("")
            if dmg:
                self.u.info("NOTE: Only Downloading DMG Files\n")
            self.u.info("Downloading {} for {}...\n".format(os.path.basename(url), name))
            try:
                result = self.d.stream_to_file(url, os.path.join(download_dir, os.path.basename(url)))
                assert result is not None
                done.append({"name":os.path.basename(url), "status":True})
            except:
                done.append({"name":os.path.basename(url), "status":False})
        succeeded = [x for x in done if x["status"]]
        failed    = [x for x in done if not x["status"]]
        self.u.head("Downloaded {} of {}".format(len(succeeded), len(dl_list)))
        self.u.info("Succeeded:")
        if len(succeeded):
            for x in succeeded:
                self.u.info("  {}".format(x["name"]))
        else:
            self.u.info("  None")
        self.u.info("\nFailed:")
        if len(failed):
            for x in failed:
                self.u.info("  {}".format(x["name"]))
        else:
            self.u.info("  None")
        self.u.info("\nFiles saved to:\n  {}\n".format(download_dir))
        if self.interactive:
            self.u.grab("Press [enter] to return...")
        elif len(failed):
            raise ProgramError("{} files failed to download".format(len(failed)))

    def product_to_json(self, prod):
        prod_dict = {}
        for key in ["product", "version", "build", "title", "size", "packages"]:
            if key in prod:
                prod_dict[key] = prod[key]
        prod_dict["date"] = prod["date"].isoformat()
        prod_dict["deviceIds"] = list(prod["device_ids"])
        return json.dumps(prod_dict,indent=2)

    def show_catalog_url(self):
        self.resize()
        self.u.head()
        print("Current Catalog:   {}".format(self.current_catalog))
        print("Max macOS Version: {}".format(self.num_to_macos(self.current_macos,for_url=False)))
        print("")
        print("{}".format(self.build_url()))
        if self.interactive:
            print("")
            self.u.grab("Press [enter] to return...")

    def pick_catalog(self):
        self.resize()
        self.u.head("Select SU Catalog")
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
            self.save_settings()
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
        print("Currently set to {}".format(self.num_to_macos(self.current_macos,for_url=False)))
        print("")
        print("M. Main Menu")
        print("Q. Quit")
        print("")
        print("Please type the max macOS version for the catalog url")
        menu = self.u.grab("eg. 10.15 for Catalina, 11 for Big Sur, 12 for Monterey:  ")
        if not len(menu):
            self.pick_macos()
            return
        if menu[0].lower() == "m":
            return
        elif menu[0].lower() == "q":
            self.u.custom_quit()
        # At this point - we should have something in the proper format
        version = self.macos_to_num(menu)
        if not version: return
        self.current_macos = version
        self.save_settings()
        # At this point, we should be good
        self.get_catalog_data()

    def main(self, dmg = False):
        lines = []
        lines.append("Available Products:")
        lines.append(" ")
        if not len(self.mac_prods):
            lines.append("No installers in catalog!")
            lines.append(" ")
        for num,p in enumerate(self.mac_prods,start=1):
            var1 = "{}. {} {}".format(num, p["title"], p["version"])
            if p["build"].lower() != "unknown":
                var1 += " ({})".format(p["build"])
            var2 = "   - {} - Added {} - {}".format(p["product"], p["date"], p["size"])
            if self.find_recovery and p["installer"]:
                # Show that it's a full installer
                var2 += " - FULL Install"
            lines.append(var1)
            lines.append(var2)
        lines.append(" ")
        lines.append("M. Change Max-OS Version (Currently {})".format(self.num_to_macos(self.current_macos,for_url=False)))
        lines.append("C. Change Catalog (Currently {})".format(self.current_catalog))
        lines.append("I. Only Print URLs (Currently {})".format("On" if self.print_urls else "Off"))
        if sys.platform.lower() == "darwin":
            lines.append("S. Set Current Catalog to SoftwareUpdate Catalog")
            lines.append("L. Clear SoftwareUpdate Catalog")
        lines.append("R. Toggle Recovery-Only (Currently {})".format("On" if self.find_recovery else "Off"))
        lines.append("U. Show Catalog URL")
        lines.append("Q. Quit")
        lines.append(" ")
        self.resize(len(max(lines)), len(lines)+5)
        self.u.head()
        print("\n".join(lines))
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
            self.save_settings()
            return
        elif menu[0].lower() == "l" and sys.platform.lower() == "darwin":
            # Clear the software update catalog
            self.u.head("Clearing SU CatalogURL")
            print("sudo softwareupdate --clear-catalog")
            self.r.run({"args":["softwareupdate","--clear-catalog"],"sudo":True})
            print("")
            self.u.grab("Done.", timeout=5)
            return
        elif menu[0].lower() == "s" and sys.platform.lower() == "darwin":
            # Set the software update catalog to our current catalog url
            self.u.head("Setting SU CatalogURL")
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
            self.save_settings()
        if menu[0].lower() in ["m","c","r"]:
            self.resize()
            self.u.head("Parsing Data")
            print("Re-scanning products after url preference toggled...\n")
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

    def get_latest(self, device_id = None, dmg = False):
        self.u.head("Downloading Latest")
        prods = sorted(self.mac_prods, key=lambda x:x['version'], reverse=True)
        if device_id:
            prod = next(p for p in prods if device_id.lower() in p["device_ids"])
            if not prod:
                raise ProgramError("No version found for Device ID '{}'".format(device_id))
        else:
            prod = prods[0]
        self.download_prod(prod, dmg)

    def get_for_product(self, prod, dmg = False):
        self.u.head("Downloading for {}".format(prod))
        for p in self.mac_prods:
            if p["product"] == prod:
                self.download_prod(p, dmg)
                return
        raise ProgramError("{} not found".format(prod))

    def get_for_version(self, vers, build = None, device_id = None, dmg = False):
        self.u.head("Downloading for {} {}".format(vers, build or ""))
        # Map the versions to their names
        v = self.version_names.get(vers.lower(),vers.lower())
        v_dict = {}
        for n in self.version_names:
            v_dict[self.version_names[n]] = n
        n = v_dict.get(v, v)
        for p in sorted(self.mac_prods, key=lambda x:x['version'], reverse=True):
            if build and p["build"] != build:
                continue
            if device_id and device_id.lower() not in p["device_ids"]:
                continue
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
        raise ProgramError("'{}' '{}' not found".format(vers, build or ""))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--latest", help="downloads the version available in the current catalog (overrides --build, --version and --product)", action="store_true")
    parser.add_argument("-r", "--recovery", help="looks for RecoveryHDUpdate.pkg and RecoveryHDMetaDmg.pkg in lieu of com.apple.mpkg.OSInstall (overrides --dmg)", action="store_true")
    parser.add_argument("-d", "--dmg", help="downloads only the .dmg files", action="store_true")
    parser.add_argument("-s", "--savelocal", help="uses a locally saved sucatalog.plist if exists", action="store_true")
    parser.add_argument("-n", "--newlocal", help="downloads and saves locally, overwriting any prior local sucatalog.plist", action="store_true")
    parser.add_argument("-c", "--catalog", help="sets the CATALOG to use - publicrelease, public, customer, developer")
    parser.add_argument("-p", "--product", help="sets the product id to search for (overrides --version)")
    parser.add_argument("-v", "--version", help="sets the version of macOS to target - eg '-v 10.14' or '-v Yosemite'")
    parser.add_argument("-b", "--build", help="sets the build of macOS to target - eg '22G120' (must be used together with --version)")
    parser.add_argument("-m", "--maxos", help="sets the max macOS version to consider when building the url - eg 10.14")
    parser.add_argument("-D", "--device-id", help="use with --version or --latest to search for versions supporting the specified Device ID - eg VMM-x86_64 for any x86_64")
    parser.add_argument("-i", "--print-urls", help="only prints the download URLs, does not actually download them", action="store_true")
    parser.add_argument("-j", "--print-json", help="only prints the product metadata in JSON, does not actually download it", action="store_true")
    parser.add_argument("--no-interactive", help="run in non-interactive mode (auto-enabled when using --product or --version)", action="store_true")
    parser.add_argument("-o", "--download-dir", help="overrides directory where the downloaded files are saved")
    args = parser.parse_args()

    if args.build and not (args.latest or args.product or args.version):
        print("The --build option requires a --version")
        exit(1)

    interactive = not any((args.no_interactive,args.product,args.version))
    g = gibMacOS(interactive=interactive, download_dir=args.download_dir)

    if args.recovery:
        args.dmg = False
        g.find_recovery = args.recovery

    if args.savelocal:
        g.save_local = True

    if args.newlocal:
        g.force_local = True

    if args.print_urls:
        g.print_urls = True

    if args.print_json:
        g.print_json = True

    if args.maxos:
        try:
            version = g.macos_to_num(args.maxos)
            if version: g.current_macos = version
        except:
            pass
    if args.catalog:
        # Set the catalog
        g.set_catalog(args.catalog)

    try:
        # Done setting up pre-requisites
        g.set_prods()

        if args.latest:
            g.get_latest(device_id=args.device_id, dmg=args.dmg)
        elif args.product != None:
            g.get_for_product(args.product, args.dmg)
        elif args.version != None:
            g.get_for_version(args.version, args.build, device_id=args.device_id, dmg=args.dmg)
        elif g.interactive:
            while True:
                try:
                    g.main(args.dmg)
                except ProgramError as e:
                    g.u.head(e.title)
                    print(str(e))
                    print("")
                    g.u.grab("Press [enter] to return...")
        else:
            raise ProgramError("No command specified")
    except ProgramError as e:
        print(str(e))
        if g.interactive:
            print("")
            g.u.grab("Press [enter] to exit...")
        else:
            exit(1)
    exit(0)
