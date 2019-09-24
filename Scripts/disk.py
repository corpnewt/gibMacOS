import subprocess, plistlib, sys, os, time, json
sys.path.append(os.path.abspath(os.path.dirname(os.path.realpath(__file__))))
import run
if sys.version_info < (3,0):
    # Force use of StringIO instead of cStringIO as the latter
    # has issues with Unicode strings
    from StringIO import StringIO

class Disk:

    def __init__(self):
        self.r = run.Run()
        self.diskutil = self.get_diskutil()
        self.os_version = ".".join(
            self.r.run({"args":["sw_vers", "-productVersion"]})[0].split(".")[:2]
        )
        self.full_os_version = self.r.run({"args":["sw_vers", "-productVersion"]})[0]
        if len(self.full_os_version.split(".")) < 3:
            # Add .0 in case of 10.14
            self.full_os_version += ".0"
        self.sudo_mount_version = "10.13.6"
        self.sudo_mount_types   = ["efi"]
        self.apfs = {}
        self._update_disks()

    def _get_str(self, val):
        # Helper method to return a string value based on input type
        if (sys.version_info < (3,0) and isinstance(val, unicode)) or (sys.version_info >= (3,0) and isinstance(val, bytes)):
            return val.encode("utf-8")
        return str(val)

    def _get_plist(self, s):
        p = {}
        try:
            if sys.version_info >= (3, 0):
                p = plistlib.loads(s.encode("utf-8"))
            else:
                # p = plistlib.readPlistFromString(s)
                # We avoid using readPlistFromString() as that uses
                # cStringIO and fails when Unicode strings are detected
                # Don't subclass - keep the parser local
                from xml.parsers.expat import ParserCreate
                # Create a new PlistParser object - then we need to set up
                # the values and parse.
                pa = plistlib.PlistParser()
                # We also monkey patch this to encode unicode as utf-8
                def end_string():
                    d = pa.getData()
                    if isinstance(d,unicode):
                        d = d.encode("utf-8")
                    pa.addObject(d)
                pa.end_string = end_string
                parser = ParserCreate()
                parser.StartElementHandler = pa.handleBeginElement
                parser.EndElementHandler = pa.handleEndElement
                parser.CharacterDataHandler = pa.handleData
                if isinstance(s, unicode):
                    # Encode unicode -> string; use utf-8 for safety
                    s = s.encode("utf-8")
                # Parse the string
                parser.Parse(s, 1)
                p = pa.root
        except Exception as e:
            print(e)
            pass
        return p

    def _compare_versions(self, vers1, vers2, pad = -1):
        # Helper method to compare ##.## strings
        #
        # vers1 < vers2 = True
        # vers1 = vers2 = None
        # vers1 > vers2 = False
        #
        # Must be separated with a period
        
        # Sanitize the pads
        pad = -1 if not type(pad) is int else pad
        
        # Cast as strings
        vers1 = str(vers1)
        vers2 = str(vers2)
        
        # Split to lists
        v1_parts = vers1.split(".")
        v2_parts = vers2.split(".")
        
        # Equalize lengths
        if len(v1_parts) < len(v2_parts):
            v1_parts.extend([str(pad) for x in range(len(v2_parts) - len(v1_parts))])
        elif len(v2_parts) < len(v1_parts):
            v2_parts.extend([str(pad) for x in range(len(v1_parts) - len(v2_parts))])
        
        # Iterate and compare
        for i in range(len(v1_parts)):
            # Remove non-numeric
            v1 = ''.join(c for c in v1_parts[i] if c.isdigit())
            v2 = ''.join(c for c in v2_parts[i] if c.isdigit())
            # If empty - make it a pad var
            v1 = pad if not len(v1) else v1
            v2 = pad if not len(v2) else v2
            # Compare
            if int(v1) < int(v2):
                return True
            elif int(v1) > int(v2):
                return False
        # Never differed - return None, must be equal
        return None

    def update(self):
        self._update_disks()

    def _update_disks(self):
        self.disks = self.get_disks()
        self.disk_text = self.get_disk_text()
        if self._compare_versions("10.12", self.os_version):
            self.apfs = self.get_apfs()
        else:
            self.apfs = {}

    def get_diskutil(self):
        # Returns the path to the diskutil binary
        return self.r.run({"args":["which", "diskutil"]})[0].split("\n")[0].split("\r")[0]

    def get_disks(self):
        # Returns a dictionary object of connected disks
        disk_list = self.r.run({"args":[self.diskutil, "list", "-plist"]})[0]
        return self._get_plist(disk_list)

    def get_disk_text(self):
        # Returns plain text listing connected disks
        return self.r.run({"args":[self.diskutil, "list"]})[0]

    def get_disk_info(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        disk_list = self.r.run({"args":[self.diskutil, "info", "-plist", disk_id]})[0]
        return self._get_plist(disk_list)

    def get_disk_fs(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        return self.get_disk_info(disk_id).get("FilesystemName", None)

    def get_disk_fs_type(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        return self.get_disk_info(disk_id).get("FilesystemType", None)

    def get_apfs(self):
        # Returns a dictionary object of apfs disks
        output = self.r.run({"args":"echo y | " + self.diskutil + " apfs list -plist", "shell" : True})
        if not output[2] == 0:
            # Error getting apfs info - return an empty dict
            return {}
        disk_list = output[0]
        p_list = disk_list.split("<?xml")
        if len(p_list) > 1:
            # We had text before the start - get only the plist info
            disk_list = "<?xml" + p_list[-1]
        return self._get_plist(disk_list)

    def is_apfs(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        # Takes a disk identifier, and returns whether or not it's apfs
        for d in self.disks.get("AllDisksAndPartitions", []):
            if not "APFSVolumes" in d:
                continue
            if d.get("DeviceIdentifier", "").lower() == disk_id.lower():
                return True
            for a in d.get("APFSVolumes", []):
                if a.get("DeviceIdentifier", "").lower() == disk_id.lower():
                    return True
        return False

    def is_apfs_container(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        # Takes a disk identifier, and returns whether or not that specific 
        # disk/volume is an APFS Container
        for d in self.disks.get("AllDisksAndPartitions", []):
            # Only check partitions
            for p in d.get("Partitions", []):
                if disk_id.lower() == p.get("DeviceIdentifier", "").lower():
                    return p.get("Content", "").lower() == "apple_apfs"
        return False

    def is_cs_container(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        # Takes a disk identifier, and returns whether or not that specific 
        # disk/volume is an CoreStorage Container
        for d in self.disks.get("AllDisksAndPartitions", []):
            # Only check partitions
            for p in d.get("Partitions", []):
                if disk_id.lower() == p.get("DeviceIdentifier", "").lower():
                    return p.get("Content", "").lower() == "apple_corestorage"
        return False

    def is_core_storage(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        if self._get_physical_disk(disk_id, "Logical Volume on "):
            return True
        return False

    def get_identifier(self, disk):
        # Should be able to take a mount point, disk name, or disk identifier,
        # and return the disk's identifier
        # Iterate!!
        if not disk or not len(self._get_str(disk)):
            return None
        disk = self._get_str(disk).lower()
        if disk.startswith("/dev/r"):
            disk = disk[len("/dev/r"):]
        elif disk.startswith("/dev/"):
            disk = disk[len("/dev/"):]
        if disk in self.disks.get("AllDisks", []):
            return disk
        for d in self.disks.get("AllDisksAndPartitions", []):
            for a in d.get("APFSVolumes", []):
                if disk in [ self._get_str(a.get(x, "")).lower() for x in ["DeviceIdentifier", "VolumeName", "VolumeUUID", "DiskUUID", "MountPoint"] ]:
                    return a.get("DeviceIdentifier", None)
            for a in d.get("Partitions", []):
                if disk in [ self._get_str(a.get(x, "")).lower() for x in ["DeviceIdentifier", "VolumeName", "VolumeUUID", "DiskUUID", "MountPoint"] ]:
                    return a.get("DeviceIdentifier", None)
        # At this point, we didn't find it
        return None

    def get_top_identifier(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        return disk_id.replace("disk", "didk").split("s")[0].replace("didk", "disk")
        
    def _get_physical_disk(self, disk, search_term):
        # Change disk0s1 to disk0
        our_disk = self.get_top_identifier(disk)
        our_term = "/dev/" + our_disk
        found_disk = False
        our_text = ""
        for line in self.disk_text.split("\n"):
            if line.lower().startswith(our_term):
                found_disk = True
                continue
            if not found_disk:
                continue
            if line.lower().startswith("/dev/disk"):
                # At the next disk - bail
                break
            if search_term.lower() in line.lower():
                our_text = line
                break
        if not len(our_text):
            # Nothing found
            return None
        our_stores = "".join(our_text.strip().split(search_term)[1:]).split(" ,")
        if not len(our_stores):
            return None
        for store in our_stores:
            efi = self.get_efi(store)
            if efi:
                return store
        return None

    def get_physical_store(self, disk):
        # Returns the physical store containing the EFI
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        if not self.is_apfs(disk_id):
            return None
        return self._get_physical_disk(disk_id, "Physical Store ")

    def get_core_storage_pv(self, disk):
        # Returns the core storage physical volume containing the EFI
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        if not self.is_core_storage(disk_id):
            return None
        return self._get_physical_disk(disk_id, "Logical Volume on ")

    def get_parent(self, disk):
        # Disk can be a mount point, disk name, or disk identifier
        disk_id = self.get_identifier(disk)
        if self.is_apfs(disk_id):
            disk_id = self.get_physical_store(disk_id)
        elif self.is_core_storage(disk_id):
            disk_id = self.get_core_storage_pv(disk_id)
        if not disk_id:
            return None
        if self.is_apfs(disk_id):
            # We have apfs - let's get the container ref
            for a in self.apfs.get("Containers", []):
                # Check if it's the whole container
                if a.get("ContainerReference", "").lower() == disk_id.lower():
                    return a["ContainerReference"]
                # Check through each volume and return the parent's container ref
                for v in a.get("Volumes", []):
                    if v.get("DeviceIdentifier", "").lower() == disk_id.lower():
                        return a.get("ContainerReference", None)
        else:
            # Not apfs - go through all volumes and whole disks
            for d in self.disks.get("AllDisksAndPartitions", []):
                if d.get("DeviceIdentifier", "").lower() == disk_id.lower():
                    return d["DeviceIdentifier"]
                for p in d.get("Partitions", []):
                    if p.get("DeviceIdentifier", "").lower() == disk_id.lower():
                        return d["DeviceIdentifier"]
        # Didn't find anything
        return None

    def get_efi(self, disk):
        disk_id = self.get_parent(self.get_identifier(disk))
        if not disk_id:
            return None
        # At this point - we should have the parent
        for d in self.disks["AllDisksAndPartitions"]:
            if d.get("DeviceIdentifier", "").lower() == disk_id.lower():
                # Found our disk
                for p in d.get("Partitions", []):
                    if p.get("Content", "").lower() == "efi":
                        return p.get("DeviceIdentifier", None)
        return None

    def mount_partition(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        sudo = False
        if not self._compare_versions(self.full_os_version, self.sudo_mount_version) and self.get_content(disk_id).lower() in self.sudo_mount_types:
            sudo = True
        out = self.r.run({"args":[self.diskutil, "mount", disk_id], "sudo":sudo})
        self._update_disks()
        return out

    def unmount_partition(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        out = self.r.run({"args":[self.diskutil, "unmount", disk_id]})
        self._update_disks()
        return out

    def is_mounted(self, disk):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        m = self.get_mount_point(disk_id)
        return (m != None and len(m))

    def get_volumes(self):
        # Returns a list object with all volumes from disks
        return self.disks.get("VolumesFromDisks", [])

    def _get_value_apfs(self, disk, field, default = None):
        return self._get_value(disk, field, default, True)

    def _get_value(self, disk, field, default = None, apfs_only = False):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        # Takes a disk identifier, and returns the requested value
        for d in self.disks.get("AllDisksAndPartitions", []):
            for a in d.get("APFSVolumes", []):
                if a.get("DeviceIdentifier", "").lower() == disk_id.lower():
                    return a.get(field, default)
            if apfs_only:
                # Skip looking at regular partitions
                continue
            if d.get("DeviceIdentifier", "").lower() == disk_id.lower():
                return d.get(field, default)
            for a in d.get("Partitions", []):
                if a.get("DeviceIdentifier", "").lower() == disk_id.lower():
                    return a.get(field, default)
        return None

    # Getter methods
    def get_content(self, disk):
        return self._get_value(disk, "Content")

    def get_volume_name(self, disk):
        return self._get_value(disk, "VolumeName")

    def get_volume_uuid(self, disk):
        return self._get_value(disk, "VolumeUUID")

    def get_disk_uuid(self, disk):
        return self._get_value(disk, "DiskUUID")

    def get_mount_point(self, disk):
        return self._get_value(disk, "MountPoint")

    def open_mount_point(self, disk, new_window = False):
        disk_id = self.get_identifier(disk)
        if not disk_id:
            return None
        mount = self.get_mount_point(disk_id)
        if not mount:
            return None
        out = self.r.run({"args":["open", mount]})
        return out[2] == 0

    def get_mounted_volumes(self):
        # Returns a list of mounted volumes
        vol_list = self.r.run({"args":["ls", "-1", "/Volumes"]})[0].split("\n")
        vol_list = [ x for x in vol_list if x != "" ]
        return vol_list

    def get_mounted_volume_dicts(self):
        # Returns a list of dicts of name, identifier, mount point dicts
        vol_list = []
        for v in self.get_mounted_volumes():
            i = self.get_identifier(os.path.join("/Volumes", v))
            if i == None:
                i = self.get_identifier("/")
                if not self.get_volume_name(i) == v:
                    # Not valid and not our boot drive
                    continue
            vol_list.append({
                "name" : self.get_volume_name(i),
                "identifier" : i,
                "mount_point" : self.get_mount_point(i),
                "disk_uuid" : self.get_disk_uuid(i),
                "volume_uuid" : self.get_volume_uuid(i)
            })
        return vol_list

    def get_disks_and_partitions_dict(self):
        # Returns a list of dictionaries like so:
        # { "disk0" : { "partitions" : [ 
        #    { 
        #      "identifier" : "disk0s1", 
        #      "name" : "EFI", 
        #      "mount_point" : "/Volumes/EFI"
        #     } 
        #  ] } }
        disks = {}
        for d in self.disks.get("AllDisks", []):
            # Get the parent and make sure it has an entry
            parent     = self.get_parent(d)
            top_disk   = self.get_top_identifier(d)
            if top_disk == d and not self.is_core_storage(d):
                # Top level, skip
                continue
            # Not top level - make sure it's not an apfs container or core storage container
            if self.is_apfs_container(d):
                continue
            if self.is_cs_container(d):
                continue
            if not parent in disks:
                disks[parent] = { "partitions" : [] }
            disks[parent]["partitions"].append({
                "name" : self.get_volume_name(d),
                "identifier" : d,
                "mount_point" : self.get_mount_point(d),
                "disk_uuid" : self.get_disk_uuid(d),
                "volume_uuid" : self.get_volume_uuid(d)
            })
        return disks
