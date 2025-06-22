###     ###
# Imports #
###     ###

import datetime, os, plistlib, struct, sys, itertools, binascii
from io import BytesIO

if sys.version_info < (3,0):
    # Force use of StringIO instead of cStringIO as the latter
    # has issues with Unicode strings
    from StringIO import StringIO
else:
    from io import StringIO

try:
    basestring  # Python 2
    unicode
except NameError:
    basestring = str  # Python 3
    unicode = str

try:
    FMT_XML = plistlib.FMT_XML
    FMT_BINARY = plistlib.FMT_BINARY
except AttributeError:
    FMT_XML = "FMT_XML"
    FMT_BINARY = "FMT_BINARY"

###            ###
# Helper Methods #
###            ###

def wrap_data(value):
    if not _check_py3(): return plistlib.Data(value)
    return value

def extract_data(value):
    if not _check_py3() and isinstance(value,plistlib.Data): return value.data
    return value

def _check_py3():
    return sys.version_info >= (3, 0)

def _is_binary(fp):
    if isinstance(fp, basestring):
        return fp.startswith(b"bplist00")
    header = fp.read(32)
    fp.seek(0)
    return header[:8] == b'bplist00'

def _seek_past_whitespace(fp):
    offset = 0
    while True:
        byte = fp.read(1)
        if not byte:
            # End of file, reset offset and bail
            offset = 0
            break
        if not byte.isspace():
            # Found our first non-whitespace character
            break
        offset += 1
    # Seek to the first non-whitespace char
    fp.seek(offset)
    return offset

###                             ###
# Deprecated Functions - Remapped #
###                             ###

def readPlist(pathOrFile):
    if not isinstance(pathOrFile, basestring):
        return load(pathOrFile)
    with open(pathOrFile, "rb") as f:
        return load(f)

def writePlist(value, pathOrFile):
    if not isinstance(pathOrFile, basestring):
        return dump(value, pathOrFile, fmt=FMT_XML, sort_keys=True, skipkeys=False)
    with open(pathOrFile, "wb") as f:
        return dump(value, f, fmt=FMT_XML, sort_keys=True, skipkeys=False)

###                ###
# Remapped Functions #
###                ###

def load(fp, fmt=None, use_builtin_types=None, dict_type=dict):
    if _is_binary(fp):
        use_builtin_types = False if use_builtin_types is None else use_builtin_types
        try:
            p = _BinaryPlistParser(use_builtin_types=use_builtin_types, dict_type=dict_type)
        except:
            # Python 3.9 removed use_builtin_types
            p = _BinaryPlistParser(dict_type=dict_type)
        return p.parse(fp)
    elif _check_py3():
        offset = _seek_past_whitespace(fp)
        use_builtin_types = True if use_builtin_types is None else use_builtin_types
        # We need to monkey patch this to allow for hex integers - code taken/modified from 
        # https://github.com/python/cpython/blob/3.8/Lib/plistlib.py
        if fmt is None:
            header = fp.read(32)
            fp.seek(offset)
            for info in plistlib._FORMATS.values():
                if info['detect'](header):
                    P = info['parser']
                    break
            else:
                raise plistlib.InvalidFileException()
        else:
            P = plistlib._FORMATS[fmt]['parser']
        try:
            p = P(use_builtin_types=use_builtin_types, dict_type=dict_type)
        except:
            # Python 3.9 removed use_builtin_types
            p = P(dict_type=dict_type)
        if isinstance(p,plistlib._PlistParser):
            # Monkey patch!
            def end_integer():
                d = p.get_data()
                value = int(d,16) if d.lower().startswith("0x") else int(d)
                if -1 << 63 <= value < 1 << 64:
                    p.add_object(value)
                else:
                    raise OverflowError("Integer overflow at line {}".format(p.parser.CurrentLineNumber))
            def end_data():
                try:
                    p.add_object(plistlib._decode_base64(p.get_data()))
                except Exception as e:
                    raise Exception("Data error at line {}: {}".format(p.parser.CurrentLineNumber,e))
            p.end_integer = end_integer
            p.end_data = end_data
        return p.parse(fp)
    else:
        offset = _seek_past_whitespace(fp)
        # Is not binary - assume a string - and try to load
        # We avoid using readPlistFromString() as that uses
        # cStringIO and fails when Unicode strings are detected
        # Don't subclass - keep the parser local
        from xml.parsers.expat import ParserCreate
        # Create a new PlistParser object - then we need to set up
        # the values and parse.
        p = plistlib.PlistParser()
        parser = ParserCreate()
        parser.StartElementHandler = p.handleBeginElement
        parser.EndElementHandler = p.handleEndElement
        parser.CharacterDataHandler = p.handleData
        # We also need to monkey patch this to allow for other dict_types, hex int support
        # proper line output for data errors, and for unicode string decoding
        def begin_dict(attrs):
            d = dict_type()
            p.addObject(d)
            p.stack.append(d)
        def end_integer():
            d = p.getData()
            value = int(d,16) if d.lower().startswith("0x") else int(d)
            if -1 << 63 <= value < 1 << 64:
                p.addObject(value)
            else:
                raise OverflowError("Integer overflow at line {}".format(parser.CurrentLineNumber))
        def end_data():
            try:
                p.addObject(plistlib.Data.fromBase64(p.getData()))
            except Exception as e:
                raise Exception("Data error at line {}: {}".format(parser.CurrentLineNumber,e))
        def end_string():
            d = p.getData()
            if isinstance(d,unicode):
                d = d.encode("utf-8")
            p.addObject(d)
        p.begin_dict = begin_dict
        p.end_integer = end_integer
        p.end_data = end_data
        p.end_string = end_string
        if isinstance(fp, unicode):
            # Encode unicode -> string; use utf-8 for safety
            fp = fp.encode("utf-8")
        if isinstance(fp, basestring):
            # It's a string - let's wrap it up
            fp = StringIO(fp)
        # Parse it
        parser.ParseFile(fp)
        return p.root

def loads(value, fmt=None, use_builtin_types=None, dict_type=dict):
    if _check_py3() and isinstance(value, basestring):
        # If it's a string - encode it
        value = value.encode()
    try:
        return load(BytesIO(value),fmt=fmt,use_builtin_types=use_builtin_types,dict_type=dict_type)
    except:
        # Python 3.9 removed use_builtin_types
        return load(BytesIO(value),fmt=fmt,dict_type=dict_type)

def dump(value, fp, fmt=FMT_XML, sort_keys=True, skipkeys=False):
    if fmt == FMT_BINARY:
        # Assume binary at this point
        writer = _BinaryPlistWriter(fp, sort_keys=sort_keys, skipkeys=skipkeys)
        writer.write(value)
    elif fmt == FMT_XML:
        if _check_py3():
            plistlib.dump(value, fp, fmt=fmt, sort_keys=sort_keys, skipkeys=skipkeys)
        else:
            # We need to monkey patch a bunch here too in order to avoid auto-sorting
            # of keys
            writer = plistlib.PlistWriter(fp)
            def writeDict(d):
                if d:
                    writer.beginElement("dict")
                    items = sorted(d.items()) if sort_keys else d.items()
                    for key, value in items:
                        if not isinstance(key, basestring):
                            if skipkeys:
                                continue
                            raise TypeError("keys must be strings")
                        writer.simpleElement("key", key)
                        writer.writeValue(value)
                    writer.endElement("dict")
                else:
                    writer.simpleElement("dict")
            writer.writeDict = writeDict
            writer.writeln("<plist version=\"1.0\">")
            writer.writeValue(value)
            writer.writeln("</plist>")
    else:
        # Not a proper format
        raise ValueError("Unsupported format: {}".format(fmt))
    
def dumps(value, fmt=FMT_XML, skipkeys=False, sort_keys=True):
    # We avoid using writePlistToString() as that uses
    # cStringIO and fails when Unicode strings are detected
    f = BytesIO() if _check_py3() else StringIO()
    dump(value, f, fmt=fmt, skipkeys=skipkeys, sort_keys=sort_keys)
    value = f.getvalue()
    if _check_py3():
        value = value.decode("utf-8")
    return value

###                        ###
# Binary Plist Stuff For Py2 #
###                        ###

# From the python 3 plistlib.py source:  https://github.com/python/cpython/blob/3.11/Lib/plistlib.py
# Tweaked to function on both Python 2 and 3

class UID:
    def __init__(self, data):
        if not isinstance(data, int):
            raise TypeError("data must be an int")
        # It seems Apple only uses 32-bit unsigned ints for UIDs. Although the comment in
        # CoreFoundation's CFBinaryPList.c detailing the binary plist format theoretically
        # allows for 64-bit UIDs, most functions in the same file use 32-bit unsigned ints,
        # with the sole function hinting at 64-bits appearing to be a leftover from copying
        # and pasting integer handling code internally, and this code has not changed since
        # it was added. (In addition, code in CFPropertyList.c to handle CF$UID also uses a
        # 32-bit unsigned int.)
        #
        # if data >= 1 << 64:
        #    raise ValueError("UIDs cannot be >= 2**64")
        if data >= 1 << 32:
            raise ValueError("UIDs cannot be >= 2**32 (4294967296)")
        if data < 0:
            raise ValueError("UIDs must be positive")
        self.data = data

    def __index__(self):
        return self.data

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.data))

    def __reduce__(self):
        return self.__class__, (self.data,)

    def __eq__(self, other):
        if not isinstance(other, UID):
            return NotImplemented
        return self.data == other.data

    def __hash__(self):
        return hash(self.data)

class InvalidFileException (ValueError):
    def __init__(self, message="Invalid file"):
        ValueError.__init__(self, message)

_BINARY_FORMAT = {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}

_undefined = object()

class _BinaryPlistParser:
    """
    Read or write a binary plist file, following the description of the binary
    format.  Raise InvalidFileException in case of error, otherwise return the
    root object.
    see also: http://opensource.apple.com/source/CF/CF-744.18/CFBinaryPList.c
    """
    def __init__(self, use_builtin_types, dict_type):
        self._use_builtin_types = use_builtin_types
        self._dict_type = dict_type

    def parse(self, fp):
        try:
            # The basic file format:
            # HEADER
            # object...
            # refid->offset...
            # TRAILER
            self._fp = fp
            self._fp.seek(-32, os.SEEK_END)
            trailer = self._fp.read(32)
            if len(trailer) != 32:
                raise InvalidFileException()
            (
                offset_size, self._ref_size, num_objects, top_object,
                offset_table_offset
            ) = struct.unpack('>6xBBQQQ', trailer)
            self._fp.seek(offset_table_offset)
            self._object_offsets = self._read_ints(num_objects, offset_size)
            self._objects = [_undefined] * num_objects
            return self._read_object(top_object)

        except (OSError, IndexError, struct.error, OverflowError,
                UnicodeDecodeError):
            raise InvalidFileException()

    def _get_size(self, tokenL):
        """ return the size of the next object."""
        if tokenL == 0xF:
            m = self._fp.read(1)[0]
            if not _check_py3():
                m = ord(m)
            m = m & 0x3
            s = 1 << m
            f = '>' + _BINARY_FORMAT[s]
            return struct.unpack(f, self._fp.read(s))[0]

        return tokenL

    def _read_ints(self, n, size):
        data = self._fp.read(size * n)
        if size in _BINARY_FORMAT:
            return struct.unpack('>' + _BINARY_FORMAT[size] * n, data)
        else:
            if not size or len(data) != size * n:
                raise InvalidFileException()
            return tuple(int(binascii.hexlify(data[i: i + size]),16)
                         for i in range(0, size * n, size))
            '''return tuple(int.from_bytes(data[i: i + size], 'big')
                         for i in range(0, size * n, size))'''

    def _read_refs(self, n):
        return self._read_ints(n, self._ref_size)

    def _read_object(self, ref):
        """
        read the object by reference.
        May recursively read sub-objects (content of an array/dict/set)
        """
        result = self._objects[ref]
        if result is not _undefined:
            return result

        offset = self._object_offsets[ref]
        self._fp.seek(offset)
        token = self._fp.read(1)[0]
        if not _check_py3():
            token = ord(token)
        tokenH, tokenL = token & 0xF0, token & 0x0F

        if token == 0x00: # \x00 or 0x00
            result = None

        elif token == 0x08: # \x08 or 0x08
            result = False

        elif token == 0x09: # \x09 or 0x09
            result = True

        # The referenced source code also mentions URL (0x0c, 0x0d) and
        # UUID (0x0e), but neither can be generated using the Cocoa libraries.

        elif token == 0x0f: # \x0f or 0x0f
            result = b''

        elif tokenH == 0x10:  # int
            result = int(binascii.hexlify(self._fp.read(1 << tokenL)),16)
            if tokenL >= 3: # Signed - adjust
                result = result-((result & 0x8000000000000000) << 1)

        elif token == 0x22: # real
            result = struct.unpack('>f', self._fp.read(4))[0]

        elif token == 0x23: # real
            result = struct.unpack('>d', self._fp.read(8))[0]

        elif token == 0x33:  # date
            f = struct.unpack('>d', self._fp.read(8))[0]
            # timestamp 0 of binary plists corresponds to 1/1/2001
            # (year of Mac OS X 10.0), instead of 1/1/1970.
            result = (datetime.datetime(2001, 1, 1) +
                      datetime.timedelta(seconds=f))

        elif tokenH == 0x40:  # data
            s = self._get_size(tokenL)
            if self._use_builtin_types or not hasattr(plistlib, "Data"):
                result = self._fp.read(s)
            else:
                result = plistlib.Data(self._fp.read(s))

        elif tokenH == 0x50:  # ascii string
            s = self._get_size(tokenL)
            result =  self._fp.read(s).decode('ascii')
            result = result

        elif tokenH == 0x60:  # unicode string
            s = self._get_size(tokenL)
            result = self._fp.read(s * 2).decode('utf-16be')

        elif tokenH == 0x80:  # UID
            # used by Key-Archiver plist files
            result = UID(int(binascii.hexlify(self._fp.read(1 + tokenL)),16))

        elif tokenH == 0xA0:  # array
            s = self._get_size(tokenL)
            obj_refs = self._read_refs(s)
            result = []
            self._objects[ref] = result
            result.extend(self._read_object(x) for x in obj_refs)

        # tokenH == 0xB0 is documented as 'ordset', but is not actually
        # implemented in the Apple reference code.

        # tokenH == 0xC0 is documented as 'set', but sets cannot be used in
        # plists.

        elif tokenH == 0xD0:  # dict
            s = self._get_size(tokenL)
            key_refs = self._read_refs(s)
            obj_refs = self._read_refs(s)
            result = self._dict_type()
            self._objects[ref] = result
            for k, o in zip(key_refs, obj_refs):
                key = self._read_object(k)
                if hasattr(plistlib, "Data") and isinstance(key, plistlib.Data):
                    key = key.data
                result[key] = self._read_object(o)

        else:
            raise InvalidFileException()

        self._objects[ref] = result
        return result

def _count_to_size(count):
    if count < 1 << 8:
        return 1

    elif count < 1 << 16:
        return 2

    elif count < 1 << 32:
        return 4

    else:
        return 8

_scalars = (str, int, float, datetime.datetime, bytes)

class _BinaryPlistWriter (object):
    def __init__(self, fp, sort_keys, skipkeys):
        self._fp = fp
        self._sort_keys = sort_keys
        self._skipkeys = skipkeys

    def write(self, value):

        # Flattened object list:
        self._objlist = []

        # Mappings from object->objectid
        # First dict has (type(object), object) as the key,
        # second dict is used when object is not hashable and
        # has id(object) as the key.
        self._objtable = {}
        self._objidtable = {}

        # Create list of all objects in the plist
        self._flatten(value)

        # Size of object references in serialized containers
        # depends on the number of objects in the plist.
        num_objects = len(self._objlist)
        self._object_offsets = [0]*num_objects
        self._ref_size = _count_to_size(num_objects)

        self._ref_format = _BINARY_FORMAT[self._ref_size]

        # Write file header
        self._fp.write(b'bplist00')

        # Write object list
        for obj in self._objlist:
            self._write_object(obj)

        # Write refnum->object offset table
        top_object = self._getrefnum(value)
        offset_table_offset = self._fp.tell()
        offset_size = _count_to_size(offset_table_offset)
        offset_format = '>' + _BINARY_FORMAT[offset_size] * num_objects
        self._fp.write(struct.pack(offset_format, *self._object_offsets))

        # Write trailer
        sort_version = 0
        trailer = (
            sort_version, offset_size, self._ref_size, num_objects,
            top_object, offset_table_offset
        )
        self._fp.write(struct.pack('>5xBBBQQQ', *trailer))

    def _flatten(self, value):
        # First check if the object is in the object table, not used for
        # containers to ensure that two subcontainers with the same contents
        # will be serialized as distinct values.
        if isinstance(value, _scalars):
            if (type(value), value) in self._objtable:
                return

        elif hasattr(plistlib, "Data") and isinstance(value, plistlib.Data):
            if (type(value.data), value.data) in self._objtable:
                return

        elif id(value) in self._objidtable:
            return

        # Add to objectreference map
        refnum = len(self._objlist)
        self._objlist.append(value)
        if isinstance(value, _scalars):
            self._objtable[(type(value), value)] = refnum
        elif hasattr(plistlib, "Data") and isinstance(value, plistlib.Data):
            self._objtable[(type(value.data), value.data)] = refnum
        else:
            self._objidtable[id(value)] = refnum

        # And finally recurse into containers
        if isinstance(value, dict):
            keys = []
            values = []
            items = value.items()
            if self._sort_keys:
                items = sorted(items)

            for k, v in items:
                if not isinstance(k, basestring):
                    if self._skipkeys:
                        continue
                    raise TypeError("keys must be strings")
                keys.append(k)
                values.append(v)

            for o in itertools.chain(keys, values):
                self._flatten(o)

        elif isinstance(value, (list, tuple)):
            for o in value:
                self._flatten(o)

    def _getrefnum(self, value):
        if isinstance(value, _scalars):
            return self._objtable[(type(value), value)]
        elif hasattr(plistlib, "Data") and isinstance(value, plistlib.Data):
            return self._objtable[(type(value.data), value.data)]
        else:
            return self._objidtable[id(value)]

    def _write_size(self, token, size):
        if size < 15:
            self._fp.write(struct.pack('>B', token | size))

        elif size < 1 << 8:
            self._fp.write(struct.pack('>BBB', token | 0xF, 0x10, size))

        elif size < 1 << 16:
            self._fp.write(struct.pack('>BBH', token | 0xF, 0x11, size))

        elif size < 1 << 32:
            self._fp.write(struct.pack('>BBL', token | 0xF, 0x12, size))

        else:
            self._fp.write(struct.pack('>BBQ', token | 0xF, 0x13, size))

    def _write_object(self, value):
        ref = self._getrefnum(value)
        self._object_offsets[ref] = self._fp.tell()
        if value is None:
            self._fp.write(b'\x00')

        elif value is False:
            self._fp.write(b'\x08')

        elif value is True:
            self._fp.write(b'\x09')

        elif isinstance(value, int):
            if value < 0:
                try:
                    self._fp.write(struct.pack('>Bq', 0x13, value))
                except struct.error:
                    raise OverflowError(value) # from None
            elif value < 1 << 8:
                self._fp.write(struct.pack('>BB', 0x10, value))
            elif value < 1 << 16:
                self._fp.write(struct.pack('>BH', 0x11, value))
            elif value < 1 << 32:
                self._fp.write(struct.pack('>BL', 0x12, value))
            elif value < 1 << 63:
                self._fp.write(struct.pack('>BQ', 0x13, value))
            elif value < 1 << 64:
                self._fp.write(b'\x14' + value.to_bytes(16, 'big', signed=True))
            else:
                raise OverflowError(value)

        elif isinstance(value, float):
            self._fp.write(struct.pack('>Bd', 0x23, value))

        elif isinstance(value, datetime.datetime):
            f = (value - datetime.datetime(2001, 1, 1)).total_seconds()
            self._fp.write(struct.pack('>Bd', 0x33, f))

        elif (_check_py3() and isinstance(value, (bytes, bytearray))) or (hasattr(plistlib, "Data") and isinstance(value, plistlib.Data)):
            if not isinstance(value, (bytes, bytearray)):
                value = value.data # Unpack it
            self._write_size(0x40, len(value))
            self._fp.write(value)

        elif isinstance(value, basestring):
            try:
                t = value.encode('ascii')
                self._write_size(0x50, len(value))
            except UnicodeEncodeError:
                t = value.encode('utf-16be')
                self._write_size(0x60, len(t) // 2)
            self._fp.write(t)

        elif isinstance(value, UID) or (hasattr(plistlib,"UID") and isinstance(value, plistlib.UID)):
            if value.data < 0:
                raise ValueError("UIDs must be positive")
            elif value.data < 1 << 8:
                self._fp.write(struct.pack('>BB', 0x80, value))
            elif value.data < 1 << 16:
                self._fp.write(struct.pack('>BH', 0x81, value))
            elif value.data < 1 << 32:
                self._fp.write(struct.pack('>BL', 0x83, value))
            # elif value.data < 1 << 64:
            #    self._fp.write(struct.pack('>BQ', 0x87, value))
            else:
                raise OverflowError(value)

        elif isinstance(value, (list, tuple)):
            refs = [self._getrefnum(o) for o in value]
            s = len(refs)
            self._write_size(0xA0, s)
            self._fp.write(struct.pack('>' + self._ref_format * s, *refs))

        elif isinstance(value, dict):
            keyRefs, valRefs = [], []

            if self._sort_keys:
                rootItems = sorted(value.items())
            else:
                rootItems = value.items()

            for k, v in rootItems:
                if not isinstance(k, basestring):
                    if self._skipkeys:
                        continue
                    raise TypeError("keys must be strings")
                keyRefs.append(self._getrefnum(k))
                valRefs.append(self._getrefnum(v))

            s = len(keyRefs)
            self._write_size(0xD0, s)
            self._fp.write(struct.pack('>' + self._ref_format * s, *keyRefs))
            self._fp.write(struct.pack('>' + self._ref_format * s, *valRefs))

        else:
            raise TypeError(value)
