import sys, os, time, ssl
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
            response = urlopen(Request(url, headers=headers))
        except Exception as e:
            if sys.version_info >= (3, 0) or not (isinstance(e, urllib2.URLError) and "CERTIFICATE_VERIFY_FAILED" in str(e)):
                # Either py3, or not the right error for this "fix"
                return None
            # Py2 and a Cert verify error - let's set the unverified context
            context = ssl._create_unverified_context()
            try:
                response = urlopen(Request(url, headers=headers), context=context)
            except:
                # No fixing this - bail
                return None
        return response

    def get_size(self, size, suff=None):
        if size == -1:
            return "Unknown"
        ext = ["B","KB","MB","GB","TB","PB"]
        s = float(size)
        s_dict = {}
        # Iterate the ext list, and divide by 1000 each time
        for e in ext:
            s_dict[e] = s
            s /= 1000
        if suff and suff.upper() in s_dict:
            # We supplied the suffix - use it \o/
            bval = round(s_dict[suff.upper()], 2)
            biggest = suff.upper()
        else:
            # Get the maximum >= 1 type
            biggest = next((x for x in ext[::-1] if s_dict[x] >= 1), "B")
            # Round to 2 decimal places
            bval = round(s_dict[biggest], 2)
        return "{:,.2f} {}".format(bval, biggest)

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
            sys.stdout.write("Downloaded {}\r".format(b_s))

    def get_string(self, url, progress = True, headers = None):
        response = self.open_url(url, headers)
        if not response:
            return None
        CHUNK = 16 * 1024
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
        CHUNK = 16 * 1024
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
        return chunk_so_far

    def stream_to_file(self, url, file, progress = True, headers = None):
        response = self.open_url(url, headers)
        if not response:
            return None
        CHUNK = 16 * 1024
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
