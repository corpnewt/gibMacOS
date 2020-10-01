import sys, os, time, ssl, gzip
from io import BytesIO
# Python-aware urllib stuff
if sys.version_info >= (3, 0):
    from urllib.request import urlopen, Request
else:
    # Import urllib2 to catch errors
    import urllib2
    from urllib2 import urlopen, Request

class Downloader:

    def __init__(self,**kwargs):
        self.ua = kwargs.get("useragent",{"User-Agent":"Mozilla"})

        # Provide reasonable default logic to workaround macOS CA file handling 
        cafile = ssl.get_default_verify_paths().openssl_cafile
        try:
            # If default OpenSSL CA file does not exist, use that from certifi
            if not os.path.exists(cafile):
                import certifi
                cafile = certifi.where()
            self.ssl_context = ssl.create_default_context(cafile=cafile)
        except:
            # None of the above worked, disable certificate verification for now
            self.ssl_context = ssl._create_unverified_context()
        return

    def _decode(self, value, encoding="utf-8", errors="ignore"):
        # Helper method to only decode if bytes type
        if sys.version_info >= (3,0) and isinstance(value, bytes):
            return value.decode(encoding,errors)
        return value

    def open_url(self, url, headers = None):
        # Fall back on the default ua if none provided
        headers = self.ua if headers == None else headers
        # Wrap up the try/except block so we don't have to do this for each function
        try:
            response = urlopen(Request(url, headers=headers), context=self.ssl_context)
        except Exception as e:
            # No fixing this - bail
            return None
        return response

    def get_size(self, size, suffix=None, use_1024=False, round_to=2, strip_zeroes=False):
        # size is the number of bytes
        # suffix is the target suffix to locate (B, KB, MB, etc) - if found
        # use_2014 denotes whether or not we display in MiB vs MB
        # round_to is the number of dedimal points to round our result to (0-15)
        # strip_zeroes denotes whether we strip out zeroes 

        # Failsafe in case our size is unknown
        if size == -1:
            return "Unknown"
        # Get our suffixes based on use_1024
        ext = ["B","KiB","MiB","GiB","TiB","PiB"] if use_1024 else ["B","KB","MB","GB","TB","PB"]
        div = 1024 if use_1024 else 1000
        s = float(size)
        s_dict = {} # Initialize our dict
        # Iterate the ext list, and divide by 1000 or 1024 each time to setup the dict {ext:val}
        for e in ext:
            s_dict[e] = s
            s /= div
        # Get our suffix if provided - will be set to None if not found, or if started as None
        suffix = next((x for x in ext if x.lower() == suffix.lower()),None) if suffix else suffix
        # Get the largest value that's still over 1
        biggest = suffix if suffix else next((x for x in ext[::-1] if s_dict[x] >= 1), "B")
        # Determine our rounding approach - first make sure it's an int; default to 2 on error
        try:round_to=int(round_to)
        except:round_to=2
        round_to = 0 if round_to < 0 else 15 if round_to > 15 else round_to # Ensure it's between 0 and 15
        bval = round(s_dict[biggest], round_to)
        # Split our number based on decimal points
        a,b = str(bval).split(".")
        # Check if we need to strip or pad zeroes
        b = b.rstrip("0") if strip_zeroes else b.ljust(round_to,"0") if round_to > 0 else ""
        return "{:,}{} {}".format(int(a),"" if not b else "."+b,biggest)

    def _progress_hook(self, response, bytes_so_far, total_size):
        if total_size > 0:
            percent = float(bytes_so_far) / total_size
            percent = round(percent*100, 2)
            t_s = self.get_size(total_size)
            try:
                b_s = self.get_size(bytes_so_far, t_s.split(" ")[1])
            except:
                b_s = self.get_size(bytes_so_far)
            sys.stdout.write("Downloaded {} of {} ({:.2f}%)\r".format(b_s, t_s, percent))
        else:
            b_s = self.get_size(bytes_so_far)
            sys.stdout.write("Downloaded {}\r".format(b_s))

    def get_string(self, url, progress = True, headers = None):
        response = self.open_url(url, headers)
        if not response:
            return None
        CHUNK = 1024 * 1024
        bytes_so_far = 0
        try:
            total_size = int(response.headers['Content-Length'])
        except:
            total_size = -1
        chunk_so_far = "".encode("utf-8")
        while True:
            chunk = response.read(CHUNK)
            bytes_so_far += len(chunk)
            if progress:
                self._progress_hook(response, bytes_so_far, total_size)
            if not chunk:
                break
            chunk_so_far += chunk
        return self._decode(chunk_so_far)

    def get_bytes(self, url, progress = True, headers = None):
        response = self.open_url(url, headers)
        if not response:
            return None
        CHUNK = 1024 * 1024
        bytes_so_far = 0
        try:
            total_size = int(response.headers['Content-Length'])
        except:
            total_size = -1
        chunk_so_far = "".encode("utf-8")
        while True:
            chunk = response.read(CHUNK)
            bytes_so_far += len(chunk)
            if progress:
                self._progress_hook(response, bytes_so_far, total_size)
            if not chunk:
                break
            chunk_so_far += chunk
        if response.headers.get('Content-Encoding') == "gzip":
            fileobj = BytesIO(chunk_so_far)
            file = gzip.GzipFile(fileobj=fileobj)
            return file.read()
        return chunk_so_far

    def stream_to_file(self, url, file, progress = True, headers = None):
        response = self.open_url(url, headers)
        if not response:
            return None
        CHUNK = 1024 * 1024
        bytes_so_far = 0
        try:
            total_size = int(response.headers['Content-Length'])
        except:
            total_size = -1
        with open(file, 'wb') as f:
            while True:
                chunk = response.read(CHUNK)
                bytes_so_far += len(chunk)
                if progress:
                    self._progress_hook(response, bytes_so_far, total_size)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.exists(file):
            return file
        else:
            return None
