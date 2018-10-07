from Scripts import *
import os, sys, tempfile, shutil, zipfile

class WinUSB:

    def __init__(self):
        # Make sure we're on windows
        if not os.name=="nt":
            print("This script is only for Windows!")
            exit(1)
        # Setup initial vars
        self.d = diskwin.Disk()
        self.u = utils.Utils("BinaryDestructionPls")
        self.dl = downloader.Downloader()
        self.r = run.Run()
        self.scripts = "Scripts"
        self.s_path  = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts)
        self.dd_url  = "http://www.chrysocome.net/downloads/ddrelease64.exe"
        self.dd_name = os.path.basename(self.dd_url)
        self.z_url  = "https://www.7-zip.org/a/7z1805-x64.msi"
        self.z_name = "7z.exe"
        # From Tim Sutton's brigadier:  https://github.com/timsutton/brigadier/blob/master/brigadier
        self.z_path = os.path.join(os.environ['SYSTEMDRIVE'] + "\\", "Program Files", "7-Zip", "7z.exe")
        self.recovery_suffixes = (
            "recoveryhdupdate.pkg",
            "recoveryhdmetadmg.pkg"
        )

    def get_disks_of_type(self, disk_list, disk_type=(0,2)):
        disks = {}
        for disk in disk_list:
            if disk_list[disk].get("type",0) in disk_type:
                disks[disk] = disk_list[disk]
        return disks

    def check_dd(self):
        # Checks if ddrelease64.exe exists in our Scripts dir
        # and if not - downloads it
        #
        # Returns True if exists/downloaded successfully
        # or False if issues.
        # Check for dd.exe in the current dir
        if os.path.exists(os.path.join(self.s_path, self.dd_name)):
            print("Located {}!".format(self.dd_name))
            # Got it
            return True
        print("Couldn't locate {} - downloading...".format(self.dd_name))
        # Now we need to download
        self.dl.stream_to_file(self.dd_url, os.path.join(self.s_path, self.dd_name))
        print("")
        return os.path.exists(os.path.join(self.s_path, self.dd_name))

    def check_7z(self):
        # Check for 7z.exe in Program Files and if not - download the 7z msi and install
        #
        # Returns True if found, False if not
        if os.path.exists(self.z_path):
            print("Located {}!".format(self.z_name))
            # Got it
            return True
        print("Didn't locate {} - downloading...".format(self.z_name))
        # Didn't find it - let's do some stupid stuff
        temp = tempfile.mkdtemp()
        self.dl.stream_to_file(self.z_url, os.path.join(temp, self.z_name))
        print("")
        print("Installing 7zip...")
        # From Tim Sutton's brigadier:  https://github.com/timsutton/brigadier/blob/master/brigadier
        self.r.run({"args":["msiexec", "/qn", "/i", os.path.join(temp, self.z_name)],"stream":True})
        print("")
        return os.path.exists(self.z_path)

    def get_size(self, size):
        # Returns the size passed as human readable
        if size == -1:
            return "Unknown"
        ext = ["B","KB","MB","GB","PB"]
        s = float(size)
        s_dict = {}
        # Iterate the ext list, and divide by 1000 each time
        for e in ext:
            s_dict[e] = s
            s /= 1000
        # Get the maximum >= 1 type
        biggest = next((x for x in ext[::-1] if s_dict[x] >= 1), "B")
        # Round to 2 decimal places
        bval = round(s_dict[biggest], 2)
        # Strip any orphaned, trailing 0's
        non_zero = False
        z_list = []
        for z in str(bval).split(".")[1][::-1]:
            if z == "0" and not non_zero:
                # We have a zero - and haven't hit a non-zero yet
                continue
            # Either got a non-zero, or non_zero is already set
            non_zero = True # Set again - just in case
            z_list.append(z)
        if len(z_list):
            return "{}.{} {}".format(str(bval).split(".")[0], "".join(z_list[::-1]), biggest)
        else:
            return "{} {}".format(str(bval).split(".")[0], biggest)

    def diskpart_erase(self, disk):
        # Generate a script that we can pipe to diskpart to erase our disk
        self.u.head("Creating DiskPart Script")
        print("")
        # Then we'll re-gather our disk info on success and move forward
        # Using MBR to effectively set the individual partition types
        # Keeps us from having issues mounting the EFI on Windows -
        # and also lets us explicitly set the partition id for the main
        # data partition.
        dp_script = "\n".join([
            "select disk {}".format(disk.get("index",-1)),
            "clean",
            "convert mbr",
            "create partition primary size=200",
            "format quick fs=fat32 label='CLOVER'",
            "create partition primary id=AB", # AF = HFS, AB = Recovery
            "active"
        ])
        temp = tempfile.mkdtemp()
        script = os.path.join(temp, "diskpart.txt")
        try:
            with open(script,"w") as f:
                f.write(dp_script)
        except:
            shutil.rmtree(temp)
            print("Error creating script!")
            print("")
            self.u.grab("Press [enter] to return...")
            return
        # Let's try to run it!
        out = self.r.run({"args":["diskpart","/s",script],"stream":True})
        # Ditch our script regardless of whether diskpart worked or not
        shutil.rmtree(temp)
        if out[2] != 0:
            # Error city!
            print("")
            print("DiskPart exited with non-zero status ({}).  Aborting.".format(out[2]))
            print("")
            self.u.grab("Press [enter] to return...")
            return
        # We should now have a fresh drive to work with
        # Let's write an image or something
        self.u.head("Updating Disk Information")
        print("")
        print("Re-populating list...")
        self.d.update()
        print("Relocating disk {}".format(disk["index"]))
        disk = self.d.disks[str(disk["index"])]
        self.select_package(disk)

    def select_package(self, disk):
        self.u.head("Select Recovery Package")
        print("")
        print("{}. {} - {} ({})".format(
            disk.get("index",-1), 
            disk.get("model","Unknown"), 
            self.get_size(disk.get("size",-1)),
            ["Unknown","No Root Dir","Removable","Local","Network","Disc","RAM Disk"][disk.get("type",0)]
            ))
        print("")
        print("M. Main Menu")
        print("Q. Quit")
        print("")
        menu = self.u.grab("Please paste the recovery update pkg path to extract:  ")
        if menu.lower() == "q":
            self.u.custom_quit()
        if menu.lower() == "m":
            return
        path = self.u.check_path(menu)
        if not path:
            self.select_package(disk)
            return
        # Got the package - let's make sure it's named right - just in case
        if os.path.basename(path).lower() == "4.hfs":
            # We have an hfs image already - bypass extraction
            self.dd_image(disk, path)
            return
        # If it's a directory, find the first recovery hit
        if os.path.isdir(path):
            for f in os.listdir(path):
                if f.lower().endswith(self.recovery_suffixes):
                    path = os.path.join(path, f)
                    break
        # Make sure it's named right for recovery stuffs
        if not path.lower().endswith(self.recovery_suffixes):
            self.u.head("Invalid Package")
            print("")
            print("{} is not in the available recovery package names:\n{}".format(os.path.basename(path), ", ".join(self.recovery_suffixes)))
            print("")
            print("Ensure you're passing a proper recovery package.")
            print("")
            self.u.grab("Press [enter] to return to package selection...")
            self.select_package(disk)
            return
        temp = tempfile.mkdtemp()
        print(temp)
        cwd = os.getcwd()
        os.chdir(temp)
        # Extract in sections and remove any files we run into
        out = self.r.run({"args":[self.z_path, "e", "-txar", path, "*.dmg"],"stream":True})
        if out[2] != 0:
            shutil.rmtree(temp,ignore_errors=True)
            print("An error occurred extracting: {}".format(out[2]))
            print("")
            self.u.grab("Press [enter] to return...")
            return
        # No files to delete here - let's extract the next part
        out = self.r.run({"args":[self.z_path, "e", "*.dmg", "*/Base*.dmg"],"stream":True})
        if out[2] != 0:
            shutil.rmtree(temp,ignore_errors=True)
            print("An error occurred extracting: {}".format(out[2]))
            print("")
            self.u.grab("Press [enter] to return...")
            return
        # If we got here - we should delete everything in the temp folder except
        # for a .dmg that starts with Base
        del_list = [x for x in os.listdir(temp) if not (x.lower().startswith("base") and x.lower().endswith(".dmg"))]
        for d in del_list:
            os.remove(os.path.join(temp, d))
            # shutil.rmtree(os.path.join(temp, d),ignore_errors=True)
        # Onto the last command
        out = self.r.run({"args":[self.z_path, "e", "-tdmg", "Base*.dmg", "*.hfs"],"stream":True})
        if out[2] != 0:
            shutil.rmtree(temp,ignore_errors=True)
            print("An error occurred extracting: {}".format(out[2]))
            print("")
            self.u.grab("Press [enter] to return...")
            return
        # If we got here - we should delete everything in the temp folder except
        # for a .dmg that starts with Base
        del_list = [x for x in os.listdir(temp) if not x.lower().endswith(".hfs")]
        for d in del_list:
            os.remove(os.path.join(temp, d))
            # shutil.rmtree(os.path.join(temp, d),ignore_errors=True)
        print("Extracted successfully!")
        hfs = next((x for x in os.listdir(temp) if x.lower().endswith(".hfs")),None)
        # Now to dd our image - if it exists
        if not hfs:
            print("Missing the .hfs file!  Aborting.")
            print("")
            self.u.grab("Press [enter] to return...")
        else:
            self.dd_image(disk, os.path.join(temp, hfs))
        shutil.rmtree(temp,ignore_errors=True)

    def dd_image(self, disk, image):
        # Let's dd the shit out of our disk
        self.u.head("Copying Image To Drive")
        print("")
        print("Image: {}".format(image))
        print("")
        print("Disk {}. {} - {} ({})".format(
            disk.get("index",-1), 
            disk.get("model","Unknown"), 
            self.get_size(disk.get("size",-1)),
            ["Unknown","No Root Dir","Removable","Local","Network","Disc","RAM Disk"][disk.get("type",0)]
            ))
        print("")
        args = [
            os.path.join(self.s_path, self.dd_name),
            "if={}".format(image),
            "of=\\\\?\\Device\Harddisk{}\Partition2".format(disk.get("index",-1)),
            "bs=8M",
            "--progress"
        ]
        print(" ".join(args))
        print("")
        print("This may take some time!")
        print("")
        out = self.r.run({"args":args})
        if len(out[1].split("Error")) > 1:
            # We had some error text - dd, even when failing likes to give us a 0
            # status code.  It also sends a ton of text through stderr - so we comb
            # that for "Error" then split by that to skip the extra fluff and show only
            # the error.
            print("An error occurred:\n\n{}".format("Error"+out[1].split("Error")[1]))
        else:
            print("Done!")
        print("")
        self.u.grab("Press [enter] to return to the main menu...")

    def main(self):
        # Let's make sure we have the required files needed
        self.u.head("Checking Required Tools")
        print("")
        if not self.check_dd():
            print("Couldn't find or install {} - aborting!".format(self.dd_name))
            exit(1)
        if not self.check_7z():
            print("Couldn't find or install {} - aborting!".format(self.z_name))
            exit(1)
        # Let's just setup a real simple interface and try to write some data
        self.u.head("Gathering Disk Info")
        print("")
        print("Populating list...")
        self.d.update()
        print("")
        print("Done!")
        # Let's serve up a list of *only* removable media
        self.u.head("Potential Removable Media")
        print("")
        # rem_disks = self.get_disks_of_type(self.d.disks)

        # SHOWING ALL DISKS CURRENTLY - CHANGE THIS FOR RELEASE!!!!
        rem_disks = self.d.disks

        # Types: 0 = Unknown, 1 = No Root Dir, 2 = Removable, 3 = Local, 4 = Network, 5 = Disc, 6 = RAM disk

        print("!WARNING!  This list includes both Removable AND")
        print("!WARNING!  Unknown disk types.  Be ABSOLUTELY sure")
        print("!WARNING!  before selecting a disk!")
        print("")
        for disk in sorted(rem_disks):
            print("{}. {} - {} ({})".format(
                disk, 
                rem_disks[disk].get("model","Unknown"), 
                self.get_size(rem_disks[disk].get("size",-1)),
                ["Unknown","No Root Dir","Removable","Local","Network","Disc","RAM Disk"][rem_disks[disk].get("type",0)]
                ))
            if not len(rem_disks[disk].get("partitions",{})):
                print("   No Mounted Partitions")
            else:
                parts = rem_disks[disk]["partitions"]
                for p in sorted(parts):
                    print("   {}. {} ({}) {} - {}".format(
                        p,
                        parts[p].get("letter","No Letter"),
                        "No Name" if not parts[p].get("name",None) else parts[p].get("name","No Name"),
                        parts[p].get("file system","Unknown FS"),
                        self.get_size(parts[p].get("size",-1))
                    ))
        print("")
        print("Q. Quit")
        print("")
        menu = self.u.grab("Please select a disk:  ")
        if not len(menu):
            self.main()
            return
        if menu.lower() == "q":
            self.u.custom_quit()
        selected_disk = rem_disks.get(menu,None)
        if not selected_disk:
            self.u.head("Invalid Choice")
            print("")
            print("Disk {} is not an option.".format(menu))
            print("")
            self.u.grab("Returning in 5 seconds...", timeout=5)
            self.main()
            return
        # Got a disk!
        while True:
            self.u.head("Erase {}".format(selected_disk.get("model","Unknown")))
            print("")
            print("{}. {} - {} ({})".format(
                selected_disk.get("index",-1), 
                selected_disk.get("model","Unknown"), 
                self.get_size(selected_disk.get("size",-1)),
                ["Unknown","No Root Dir","Removable","Local","Network","Disc","RAM Disk"][selected_disk.get("type",0)]
                ))
            print("")
            print("If you continue - THIS DISK WILL BE ERASED")
            print("ALL DATA WILL BE LOST AND ALL PARTITIONS WILL")
            print("BE REMOVED!!!!!!!")
            print("")
            yn = self.u.grab("Continue? (y/n):  ")
            if yn.lower() == "n":
                self.main()
                return
            if yn.lower() == "y":
                break
        # Got the OK to erase!  Let's format a diskpart script!
        self.diskpart_erase(selected_disk)
        self.main()

w = WinUSB()
w.main()
