import subprocess, plistlib, sys, os, time, json, csv
sys.path.append(os.path.abspath(os.path.dirname(os.path.realpath(__file__))))
from Scripts import run

class Disk:

    def __init__(self):
        self.r = run.Run()
        self.wmic = self._get_wmic()
        if self.wmic and not os.path.exists(self.wmic):
            self.wmic = None
        self.disks = {}
        self._update_disks()

    def _get_wmic(self):
        # Attempt to locate WMIC.exe
        wmic_list = self.r.run({"args":["where","wmic"]})[0].replace("\r","").split("\n")
        if wmic_list:
            return wmic_list[0]
        return None

    def update(self):
        self._update_disks()

    def _update_disks(self):
        self.disks = self.get_disks()

    def _get_rows(self, row_list):
        rows = []
        last_row = []
        for row in row_list:
            if not row.strip(): # Empty
                if last_row: # Got a row at least - append it and reset
                    rows.append(last_row)
                    last_row = []
                continue # Skip anything else
            # Not an empty row - let's try to get the info
            try: last_row.append(" : ".join(row.split(" : ")[1:]))
            except: pass
        return rows

    def _get_diskdrive(self):
        disks = []
        if self.wmic: # Use WMIC where possible
            try:
                wmic = self.r.run({"args":[self.wmic, "DiskDrive", "get", "DeviceID,Index,Model,Partitions,Size", "/format:csv"]})[0]
                # Get the rows - but skip the first 2 (empty, headers) and the last 1 (empty again)
                disks = list(csv.reader(wmic.replace("\r","").split("\n"), delimiter=","))[2:-1]
                # We need to skip the Node value for each row as well
                disks = [x[1:] for x in disks]
            except:
                pass
        if not disks: # Use PowerShell and parse the info manually
            try:
                ps = self.r.run({"args":["powershell", "-c", "Get-WmiObject -Class Win32_DiskDrive | Format-List -Property DeviceID,Index,Model,Partitions,Size"]})[0]
                # We need to iterate the rows and add each column manually
                disks = self._get_rows(ps.replace("\r","").split("\n"))
            except:
                pass
        return disks

    def _get_ldtop(self):
        disks = []
        if self.wmic: # Use WMIC where possible
            try:
                wmic = self.r.run({"args":[self.wmic, "path", "Win32_LogicalDiskToPartition", "get", "Antecedent,Dependent"]})[0]
                # Get the rows - but skip the first and last as they're empty
                disks = wmic.replace("\r","").split("\n")[1:-1]
            except:
                pass
        if not disks: # Use PowerShell and parse the info manually
            try:
                ps = self.r.run({"args":["powershell", "-c", "Get-WmiObject -Class Win32_LogicalDiskToPartition | Format-List -Property Antecedent,Dependent"]})[0]
                # We need to iterate the rows and add each column manually
                disks = self._get_rows(ps.replace("\r","").split("\n"))
                # We need to join the values with 2 spaces to match the WMIC output
                disks = ["  ".join(x) for x in disks]
            except:
                pass
        return disks

    def _get_logicaldisk(self):
        disks = []
        if self.wmic: # Use WMIC where possible
            try:
                wmic = self.r.run({"args":[self.wmic, "LogicalDisk", "get", "DeviceID,DriveType,FileSystem,Size,VolumeName", "/format:csv"]})[0]
                # Get the rows - but skip the first 2 (empty, headers) and the last 1 (empty again)
                disks = list(csv.reader(wmic.replace("\r","").split("\n"), delimiter=","))[2:-1]
                # We need to skip the Node value for each row as well
                disks = [x[1:] for x in disks]
            except:
                pass
        if not disks: # Use PowerShell and parse the info manually
            try:
                ps = self.r.run({"args":["powershell", "-c", "Get-WmiObject -Class Win32_LogicalDisk | Format-List -Property DeviceID,DriveType,FileSystem,Size,VolumeName"]})[0]
                # We need to iterate the rows and add each column manually
                disks = self._get_rows(ps.replace("\r","").split("\n"))
            except:
                pass
        return disks

    def get_disks(self):
        # We hate windows... all of us.
        #
        # This has to be done in 3 commands,
        # 1. To get the PHYSICALDISK entries, index, and model
        # 2. To get the drive letter, volume name, fs, and size
        # 3. To get some connection between them...
        #
        # May you all forgive me...

        disks = self._get_diskdrive()
        p_disks = {}
        for ds in disks:
            if len(ds) < 5:
                continue
            p_disks[ds[1]] = {
                "device":ds[0],
                "model":" ".join(ds[2:-2]),
                "type":0 # 0 = Unknown, 1 = No Root Dir, 2 = Removable, 3 = Local, 4 = Network, 5 = Disc, 6 = RAM disk
                }
            # More fault-tolerance with ints
            p_disks[ds[1]]["index"] = int(ds[1]) if len(ds[1]) else -1
            p_disks[ds[1]]["size"] = int(ds[-1]) if len(ds[-1]) else -1
            p_disks[ds[1]]["partitioncount"] = int(ds[-2]) if len(ds[-2]) else 0
            
        if not p_disks:
            # Drat, nothing
            return p_disks
        # Let's find a way to map this biz now
        ldtop = self._get_ldtop()
        for l in ldtop:
            l = l.lower()
            d = p = mp = None
            try:
                dp = l.split("deviceid=")[1].split('"')[1]
                mp = l.split("deviceid=")[-1].split('"')[1].upper()
                d = dp.split("disk #")[1].split(",")[0]
                p = dp.split("partition #")[1]
            except:
                pass
            if any([d, p, mp]):
                # Got *something*
                if p_disks.get(d,None):
                    if not p_disks[d].get("partitions",None):
                        p_disks[d]["partitions"] = {}
                    p_disks[d]["partitions"][p] = {"letter":mp}
        # Last attempt to do this - let's get the partition names!
        parts = self._get_logicaldisk()
        if not parts:
            return p_disks
        for ps in parts:
            if len(ps) < 2:
                # Need the drive letter and disk type at minimum
                continue
            # Organize!
            plt = ps[0] # get letter
            ptp = ps[1] # get disk type
            # Initialize
            pfs = pnm = None
            psz = -1 # Set to -1 initially for indeterminate size
            try:
                pfs = ps[2] # get file system
                psz = ps[3] # get size
                pnm = ps[4] # get the rest in the name
            except:
                pass
            for d in p_disks:
                p_dict = p_disks[d]
                for pr in p_dict.get("partitions",{}):
                    pr = p_dict["partitions"][pr]
                    if pr.get("letter","").upper() == plt.upper():
                        # Found it - set all attributes
                        pr["size"] = int(psz) if len(psz) else -1
                        pr["file system"] = pfs
                        pr["name"] = pnm
                        # Also need to set the parent drive's type
                        if len(ptp):
                            p_dict["type"] = int(ptp)
                        break
        return p_disks
