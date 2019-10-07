#!/usr/bin/env python
from Scripts import *
import os, datetime, shutil, time, sys, argparse

# Using the techniques outlined by wolfmannight here:  https://www.insanelymac.com/forum/topic/338810-create-legit-copy-of-macos-from-apple-catalog/

class buildMacOSInstallApp:
    def __init__(self):
        self.r = run.Run()
        self.u = utils.Utils("Build macOS Install App")
        self.target_files = [
            "BaseSystem.dmg",
            "BaseSystem.chunklist",
            "InstallESDDmg.pkg",
            "InstallInfo.plist",
            "AppleDiagnostics.dmg",
            "AppleDiagnostics.chunklist"
        ]
        # Verify we're on macOS - this doesn't work anywhere else
        if not sys.platform == "darwin":
            self.u.head("WARNING")
            print("")
            print("This script only runs on macOS!")
            print("")
            exit(1)

    def mount_dmg(self, dmg, no_browse = False):
        # Mounts the passed dmg and returns the mount point(s)
        args = ["/usr/bin/hdiutil", "attach", dmg, "-plist", "-noverify"]
        if no_browse:
            args.append("-nobrowse")
        out = self.r.run({"args":args})
        if out[2] != 0:
            # Failed!
            raise Exception("Mount Failed!", "{} failed to mount:\n\n{}".format(os.path.basename(dmg), out[1]))
        # Get the plist data returned, and locate the mount points
        try:
            plist_data = plist.loads(out[0])
            mounts = [x["mount-point"] for x in plist_data.get("system-entities", []) if "mount-point" in x]
            return mounts
        except:
            raise Exception("Mount Failed!", "No mount points returned from {}".format(os.path.basename(dmg)))

    def unmount_dmg(self, mount_point):
        # Unmounts the passed dmg or mount point - retries with force if failed
        # Can take either a single point or a list
        if not type(mount_point) is list:
            mount_point = [mount_point]
        unmounted = []
        for m in mount_point:    
            args = ["/usr/bin/hdiutil", "detach", m]
            out = self.r.run({"args":args})
            if out[2] != 0:
                # Polite failed, let's crush this b!
                args.append("-force")
                out = self.r.run({"args":args})
                if out[2] != 0:
                    # Oh... failed again... onto the next...
                    print(out[1])
                    continue
            unmounted.append(m)
        return unmounted

    def main(self):
        while True:
            self.u.head()
            print("")
            print("Q. Quit")
            print("")
            fold = self.u.grab("Please drag and drop the output folder from gibMacOS here:  ")
            print("")
            if fold.lower() == "q":
                self.u.custom_quit()
            f_path = self.u.check_path(fold)
            if not f_path:
                print("That path does not exist!\n")
                self.u.grab("Press [enter] to return...")
                continue
            # Let's check if it's a folder.  If not, make the next directory up the target
            if not os.path.isdir(f_path):
                f_path = os.path.dirname(os.path.realpath(f_path))
            # Walk the contents of f_path and ensure we have all the needed files
            lower_contents = [y.lower() for y in os.listdir(f_path)]
            missing_list = [x for x in self.target_files if not x.lower() in lower_contents]
            if len(missing_list):
                self.u.head("Missing Required Files")
                print("")
                print("That folder is missing the following required files:")
                print(", ".join(missing_list))
                print("")
                self.u.grab("Press [enter] to return...")
            # Time to build the installer!
            cwd = os.getcwd()
            os.chdir(f_path)
            base_mounts = []
            try:
                self.u.head("Building Installer")
                print("")
                print("Taking ownership of downloaded files...")
                for x in self.target_files:
                    print(" - {}...".format(x))
                    self.r.run({"args":["chmod","a+x",x]})
                print("Mounting BaseSystem.dmg...")
                base_mounts = self.mount_dmg("BaseSystem.dmg")
                if not len(base_mounts):
                    raise Exception("Mount Failed!", "No mount points were returned from BaseSystem.dmg")
                base_mount = base_mounts[0] # Let's assume the first
                print("Locating Installer app...")
                install_app = next((x for x in os.listdir(base_mount) if os.path.isdir(os.path.join(base_mount,x)) and x.lower().endswith(".app") and not x.startswith(".")),None)
                if not install_app:
                    raise Exception("Installer app not located in {}".format(base_mount))
                print(" - Found {}".format(install_app))
                # Copy the .app over
                out = self.r.run({"args":["cp","-R",os.path.join(base_mount,install_app),os.path.join(f_path,install_app)]})
                if out[2] != 0:
                    raise Exception("Copy Failed!", out[1])
                print("Unmounting BaseSystem.dmg...")
                for x in base_mounts:
                    self.unmount_dmg(x)
                base_mounts = []
                shared_support = os.path.join(f_path,install_app,"Contents","SharedSupport")
                if not os.path.exists(shared_support):
                    print("Creating SharedSupport directory...")
                    os.makedirs(shared_support)
                print("Copying files to SharedSupport...")
                for x in self.target_files:
                    y = "InstallESD.dmg" if x.lower() == "installesddmg.pkg" else x # InstallESDDmg.pkg gets renamed to InstallESD.dmg - all others stay the same
                    print(" - {}{}".format(x, " --> {}".format(y) if y != x else ""))
                    out = self.r.run({"args":["cp","-R",os.path.join(f_path,x),os.path.join(shared_support,y)]})
                    if out[2] != 0:
                        raise Exception("Copy Failed!", out[1])
                print("Patching InstallInfo.plist...")
                with open(os.path.join(shared_support,"InstallInfo.plist"),"rb") as f:
                    p = plist.load(f)
                if "Payload Image Info" in p:
                    pii = p["Payload Image Info"]
                    if "URL" in pii: pii["URL"] = pii["URL"].replace("InstallESDDmg.pkg","InstallESD.dmg")
                    if "id" in pii: pii["id"] = pii["id"].replace("com.apple.pkg.InstallESDDmg","com.apple.dmg.InstallESD")
                    pii.pop("chunklistURL",None)
                    pii.pop("chunklistid",None)
                with open(os.path.join(shared_support,"InstallInfo.plist"),"wb") as f:
                    plist.dump(p,f)
                print("")
                print("Created:  {}".format(install_app))
                print("Saved to: {}".format(os.path.join(f_path,install_app)))
                print("")
                self.u.grab("Press [enter] to return...")
            except Exception as e:
                print("An error occurred:")
                print(" - {}".format(e))
                print("")
                if len(base_mounts):
                    for x in base_mounts:
                        print(" - Unmounting {}...".format(x))
                        self.unmount_dmg(x)
                    print("")
                self.u.grab("Press [enter] to return...")

if __name__ == '__main__':
    b = buildMacOSInstallApp()
    b.main()
