import subprocess, plistlib, sys, os, time, json, csv
sys.path.append(os.path.abspath(os.path.dirname(os.path.realpath(__file__))))
import run

class Disk:

    def __init__(self):
        self.r = run.Run()
        self.wmic = os.path.join(os.environ['SYSTEMDRIVE'] + "\\", "Windows", "System32", "wbem", "WMIC.exe")
        self._update_disks()

    def update(self):
        self._update_disks()

    def _update_disks(self):
        self.disks = self.get_disks()

    def get_disks(self):
        # We hate windows... all of us.
        #
        # This has to be done in 3 commands,
        # 1. To get the PHYSICALDISK entries, index, and model
        # 2. To get the drive letter, volume name, fs, and size
        # 3. To get some connection between them...
        #
        # May you all forgive me...

        disks = self.r.run({"args":[self.wmic, "diskdrive", "get", "deviceid,model,index,size,partitions", "/format:csv"]})[0]
        csdisk = csv.reader(disks.replace("\r","").split("\n"), delimiter=",")
        disks = list(csdisk)
        if not len(disks) > 3:
            # Not enough info there - csv is like:
            # 1. Empty row
            # 2. Headers
            # 3->X-1. Rest of the info
            # X. Last empty row
            return {}
        # New format is:
        # Node, Device, Index, Model, Partitions, Size
        disks = disks[2:-1]
        p_disks = {}
        for d in disks:
            # Skip the Node value
            ds = d[1:]
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
            
        if not len(p_disks):
            # Drat, nothing
            return p_disks
        # Let's find a shitty way to map this biz now
        shit = self.r.run({"args":[self.wmic, "path", "Win32_LogicalDiskToPartition", "get", "antecedent,dependent"]})[0]
        shit = shit.replace("\r","").split("\n")[1:]
        for s in shit:
            s = s.lower()
            d = p = mp = None
            try:
                dp = s.split("deviceid=")[1].split('"')[1]
                d = dp.split("disk #")[1].split(",")[0]
                p = dp.split("partition #")[1]
                mp = s.split("deviceid=")[2].split('"')[1].upper()
            except:
                pass
            if any([d, p, mp]):
                # Got *something*
                if p_disks.get(d,None):
                    if not p_disks[d].get("partitions",None):
                        p_disks[d]["partitions"] = {}
                    p_disks[d]["partitions"][p] = {"letter":mp}
        # Last attempt to do this - let's get the partition names!
        parts = self.r.run({"args":[self.wmic, "logicaldisk", "get", "deviceid,filesystem,volumename,size,drivetype", "/format:csv"]})[0]
        cspart = csv.reader(parts.replace("\r","").split("\n"), delimiter=",")
        parts = list(cspart)
        if not len(parts) > 2:
            return p_disks
        parts = parts[2:-1]
        for p in parts:
            # Again, skip the Node value
            ps = p[1:]
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
