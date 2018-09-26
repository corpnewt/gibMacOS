###     ###
# Imports #
###     ###

import datetime
from io import BytesIO
import os
import plistlib
import struct
import sys

try:
    FMT_XML = plistlib.FMT_XML
except:
    FMT_XML = None

###            ###
# Helper Methods #
###            ###

def _check_py3():
    return True if sys.version_info >= (3, 0) else False

def _is_binary(fp):
    header = fp.read(32)
    fp.seek(0)
    return header[:8] == b'bplist00'

def _get_inst():
    if _check_py3():
        return (str)
    else:
        return (str, unicode)

###                             ###
# Deprecated Functions - Remapped #
###                             ###

def readPlist(pathOrFile):
    if not isinstance(pathOrFile, _get_inst()):
        return load(pathOrFile)
    with open(pathOrFile, "rb") as f:
        return load(f)

def writePlist(value, pathOrFile):
    if not isinstance(pathOrFile, _get_inst()):
        return dump(value, pathOrFile, fmt=FMT_XML, sort_keys=True, skipkeys=False)
    with open(pathOrFile, "wb") as f:
        return dump(value, f, fmt=FMT_XML, sort_keys=True, skipkeys=False)

###                ###
# Remapped Functions #
###                ###

def load(fp, fmt=None, use_builtin_types=True, dict_type=dict):
    if _check_py3():
        return plistlib.load(fp, fmt=fmt, use_builtin_types=use_builtin_types, dict_type=dict_type)
    elif not _is_binary(fp):
        return plistlib.readPlist(fp)
    else:
        return readBinaryPlistFile(fp)

def loads(value, fmt=None, use_builtin_types=True, dict_type=dict):
    if isinstance(value, _get_inst()):
        # We were sent a string - let's encode it to some utf-8 bytes for fun!
        value = value.encode("utf-8")
    fp = BytesIO(value)
    if _check_py3():
        return plistlib.load(fp, fmt=fmt, use_builtin_types=use_builtin_types, dict_type=dict_type)
    elif not _is_binary(fp):
        return plistlib.readPlistFromString(value)
    else:
        return readBinaryPlistFile(fp)

def dump(value, fp, fmt=FMT_XML, sort_keys=True, skipkeys=False):
    if _check_py3():
        plistlib.dump(value, fp, fmt=fmt, sort_keys=sort_keys, skipkeys=skipkeys)
    else:
        plistlib.writePlist(value, fp)
    
def dumps(value, fmt=FMT_XML, skipkeys=False):
    if _check_py3():
        return plistlib.dumps(value, fmt=fmt, skipkeys=skipkeys).encode("utf-8")
    else:
        return plistlib.writePlistToString(value).encode("utf-8")


###                        ###
# Binary Plist Stuff For Py2 #
###                        ###

# timestamp 0 of binary plists corresponds to 1/1/2001 (year of Mac OS X 10.0), instead of 1/1/1970.
MAC_OS_X_TIME_OFFSET = (31 * 365 + 8) * 86400

class InvalidFileException(ValueError):
    def __str__(self):
        return "Invalid file"
    def __unicode__(self):
        return "Invalid file"

def readBinaryPlistFile(in_file):
    """
    Read a binary plist file, following the description of the binary format: http://opensource.apple.com/source/CF/CF-550/CFBinaryPList.c
    Raise InvalidFileException in case of error, otherwise return the root object, as usual

    Original patch diffed here:  https://bugs.python.org/issue14455
    """
    in_file.seek(-32, os.SEEK_END)
    trailer = in_file.read(32)
    if len(trailer) != 32:
        return InvalidFileException()
    offset_size, ref_size, num_objects, top_object, offset_table_offset = struct.unpack('>6xBB4xL4xL4xL', trailer)
    in_file.seek(offset_table_offset)
    object_offsets = []
    offset_format = '>' + {1: 'B', 2: 'H', 4: 'L', 8: 'Q', }[offset_size] * num_objects
    ref_format = {1: 'B', 2: 'H', 4: 'L', 8: 'Q', }[ref_size]
    int_format = {0: (1, '>B'), 1: (2, '>H'), 2: (4, '>L'), 3: (8, '>Q'), }
    object_offsets = struct.unpack(offset_format, in_file.read(offset_size * num_objects))
    def getSize(token_l):
        """ return the size of the next object."""
        if token_l == 0xF:
            m = ord(in_file.read(1)) & 0x3
            s, f = int_format[m]
            return struct.unpack(f, in_file.read(s))[0]
        return token_l
    def readNextObject(offset):
        """ read the object at offset. May recursively read sub-objects (content of an array/dict/set) """
        in_file.seek(offset)
        token = in_file.read(1)
        token_h, token_l = ord(token) & 0xF0, ord(token) & 0x0F #high and low parts 
        if token == '\x00':
            return None
        elif token == '\x08':
            return False
        elif token == '\x09':
            return True
        elif token == '\x0f':
            return ''
        elif token_h == 0x10: #int
            result = 0
            for k in xrange((2 << token_l) - 1):
                result = (result << 8) + ord(in_file.read(1))
            return result
        elif token_h == 0x20: #real
            if token_l == 2:
                return struct.unpack('>f', in_file.read(4))[0]
            elif token_l == 3:
                return struct.unpack('>d', in_file.read(8))[0]
        elif token_h == 0x30: #date
            f = struct.unpack('>d', in_file.read(8))[0]
            return datetime.datetime.utcfromtimestamp(f + MAC_OS_X_TIME_OFFSET)
        elif token_h == 0x80: #data
            s = getSize(token_l)
            return in_file.read(s)
        elif token_h == 0x50: #ascii string
            s = getSize(token_l)
            return in_file.read(s)
        elif token_h == 0x60: #unicode string
            s = getSize(token_l)
            return in_file.read(s * 2).decode('utf-16be')
        elif token_h == 0x80: #uid
            return in_file.read(token_l + 1)
        elif token_h == 0xA0: #array
            s = getSize(token_l)
            obj_refs = struct.unpack('>' + ref_format * s, in_file.read(s * ref_size))
            return map(lambda x: readNextObject(object_offsets[x]), obj_refs)
        elif token_h == 0xC0: #set
            s = getSize(token_l)
            obj_refs = struct.unpack('>' + ref_format * s, in_file.read(s * ref_size))
            return set(map(lambda x: readNextObject(object_offsets[x]), obj_refs))
        elif token_h == 0xD0: #dict
            result = {}
            s = getSize(token_l)
            key_refs = struct.unpack('>' + ref_format * s, in_file.read(s * ref_size))
            obj_refs = struct.unpack('>' + ref_format * s, in_file.read(s * ref_size))
            for k, o in zip(key_refs, obj_refs):
                key = readNextObject(object_offsets[k])
                obj = readNextObject(object_offsets[o])
                result[key] = obj
            return result
        raise InvalidFileException()
    return readNextObject(object_offsets[top_object])
