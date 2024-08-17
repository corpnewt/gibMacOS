import sys, os, time, ssl, gzip, multiprocessing
from io import BytesIO
# Python-aware urllib stuff
try:
    from urllib.request import urlopen, Request
    import queue as q
except ImportError:
    # Import urllib2 to catch errors
    import urllib2
    from urllib2 import urlopen, Request
    import Queue as q

TERMINAL_WIDTH = 120 if os.name=="nt" else 80

def get_size(size, suffix=None, use_1024=False, round_to=2, strip_zeroes=False):
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

def _process_hook(queue, total_size, update_interval=1.0, max_packets=0):
    bytes_so_far = 0
    packets = []
    speed = remaining = ""
    last_update = time.time()
    while True:
        # Write our info first so we have *some* status while
        # waiting for packets
        if total_size > 0:
            percent = float(bytes_so_far) / total_size
            percent = round(percent*100, 2)
            t_s = get_size(total_size)
            try:
                b_s = get_size(bytes_so_far, t_s.split(" ")[1])
            except:
                b_s = get_size(bytes_so_far)
            perc_str = " {:.2f}%".format(percent)
            bar_width = (TERMINAL_WIDTH // 3)-len(perc_str)
            progress = "=" * int(bar_width * (percent/100))
            sys.stdout.write("\r\033[K{}/{} | {}{}{}{}{}".format(
                b_s,
                t_s,
                progress,
                " " * (bar_width-len(progress)),
                perc_str,
                speed,
                remaining
            ))
        else:
            b_s = get_size(bytes_so_far)
            sys.stdout.write("\r\033[K{}{}".format(b_s, speed))
        sys.stdout.flush()
        # Now we gather the next packet
        try:
            packet = queue.get(timeout=update_interval)
            # Packets should be formatted as a tuple of
            # (timestamp, len(bytes_downloaded))
            # If "DONE" is passed, we assume the download
            # finished - and bail
            if packet == "DONE":
                print("") # Jump to the next line
                return
            # Append our packet to the list and ensure we're not
            # beyond our max.
            # Only check max if it's > 0
            packets.append(packet)
            if max_packets > 0:
                packets = packets[-max_packets:]
            # Increment our bytes so far as well
            bytes_so_far += packet[1]
        except q.Empty:
            # Didn't get anything - reset the speed
            # and packets
            packets = []
            speed = " | 0 B/s"
            remaining = " | ?? left" if total_size > 0 else ""
        except KeyboardInterrupt:
            print("") # Jump to the next line
            return
        # If we have packets and it's time for an update, process
        # the info.
        update_check = time.time()
        if packets and update_check - last_update >= update_interval:
            last_update = update_check # Refresh our update timestamp
            speed = " | ?? B/s"
            if len(packets) > 1:
                # Let's calculate the amount downloaded over how long
                try:
                    first,last = packets[0][0],packets[-1][0]
                    chunks = sum([float(x[1]) for x in packets])
                    t = last-first
                    assert t >= 0
                    bytes_speed = 1. / t * chunks
                    speed = " | {}/s".format(get_size(bytes_speed,round_to=1))
                    # Get our remaining time
                    if total_size > 0:
                        seconds_left = (total_size-bytes_so_far) / bytes_speed
                        days  = seconds_left // 86400
                        hours = (seconds_left - (days*86400)) // 3600
                        mins  = (seconds_left - (days*86400) - (hours*3600)) // 60
                        secs  = seconds_left - (days*86400) - (hours*3600) - (mins*60)
                        if days > 99 or bytes_speed == 0:
                            remaining = " | ?? left"
                        else:
                            remaining = " | {}{:02d}:{:02d}:{:02d} left".format(
                                "{}:".format(int(days)) if days else "",
                                int(hours),
                                int(mins),
                                int(round(secs))
                            )
                except:
                    pass
                # Clear the packets so we don't reuse the same ones
                packets = []

class Downloader:

    def __init__(self,**kwargs):
        self.ua = kwargs.get("useragent",{"User-Agent":"Mozilla"})
        self.chunk = 1048576 # 1024 x 1024 i.e. 1MiB
        if os.name=="nt": os.system("color") # Initialize cmd for ANSI escapes
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

    def _update_main_name(self):
        # Windows running python 2 seems to have issues with multiprocessing
        # if the case of the main script's name is incorrect:
        # e.g. Downloader.py vs downloader.py
        #
        # To work around this, we try to scrape for the correct case if
        # possible.
        try:
            path = os.path.abspath(sys.modules["__main__"].__file__)
        except AttributeError as e:
            # This likely means we're running from the interpreter
            # directly
            return None
        if not os.path.isfile(path):
            return None
        # Get the file name and folder path
        name = os.path.basename(path).lower()
        fldr = os.path.dirname(path)
        # Walk the files in the folder until we find our
        # name - then steal its case and update that path
        for f in os.listdir(fldr):
            if f.lower() == name.lower():
                # Got it
                new_path = os.path.join(fldr,f)
                sys.modules["__main__"].__file__ = new_path
                return new_path
        # If we got here, it wasn't found
        return None

    def open_url(self, url, headers = None):
        # Fall back on the default ua if none provided
        headers = self.ua if headers is None else headers
        # Wrap up the try/except block so we don't have to do this for each function
        try:
            response = urlopen(Request(url, headers=headers), context=self.ssl_context)
        except Exception as e:
            # No fixing this - bail
            return None
        return response

    def get_size(self, *args, **kwargs):
        return get_size(*args,**kwargs)

    def get_string(self, url, progress = True, headers = None, expand_gzip = True):
        response = self.get_bytes(url,progress,headers,expand_gzip)
        if response is None: return None
        return self._decode(response)

    def get_bytes(self, url, progress = True, headers = None, expand_gzip = True):
        response = self.open_url(url, headers)
        if response is None: return None
        try: total_size = int(response.headers['Content-Length'])
        except: total_size = -1
        chunk_so_far = b""
        packets = queue = process = None
        if progress:
            # Make sure our vars are initialized
            packets = [] if progress else None
            queue = multiprocessing.Queue()
            # Create the multiprocess and start it
            process = multiprocessing.Process(target=_process_hook,args=(queue,total_size))
            process.daemon = True
            # Filthy hack for earlier python versions on Windows
            if os.name == "nt" and hasattr(multiprocessing,"forking"):
                self._update_main_name()
            process.start()
        while True:
            chunk = response.read(self.chunk)
            if progress:
                # Add our items to the queue
                queue.put((time.time(),len(chunk)))
            if not chunk: break
            chunk_so_far += chunk
        if expand_gzip and response.headers.get("Content-Encoding","unknown").lower() == "gzip":
            fileobj = BytesIO(chunk_so_far)
            gfile   = gzip.GzipFile(fileobj=fileobj)
            return gfile.read()
        if progress:
            # Finalize the queue and wait
            queue.put("DONE")
            process.join()
        return chunk_so_far

    def stream_to_file(self, url, file_path, progress = True, headers = None, ensure_size_if_present = True):
        response = self.open_url(url, headers)
        if response is None: return None
        bytes_so_far = 0
        try: total_size = int(response.headers['Content-Length'])
        except: total_size = -1
        packets = queue = process = None
        if progress:
            # Make sure our vars are initialized
            packets = [] if progress else None
            queue = multiprocessing.Queue()
            # Create the multiprocess and start it
            process = multiprocessing.Process(target=_process_hook,args=(queue,total_size))
            process.daemon = True
            # Filthy hack for earlier python versions on Windows
            if os.name == "nt" and hasattr(multiprocessing,"forking"):
                self._update_main_name()
            process.start()
        with open(file_path, 'wb') as f:
            while True:
                chunk = response.read(self.chunk)
                bytes_so_far += len(chunk)
                if progress:
                    # Add our items to the queue
                    queue.put((time.time(),len(chunk)))
                if not chunk: break
                f.write(chunk)
        if progress:
            # Finalize the queue and wait
            queue.put("DONE")
            process.join()
        if ensure_size_if_present and total_size != -1:
            # We're verifying size - make sure we got what we asked for
            if bytes_so_far != total_size:
                return None # We didn't - imply it failed
        return file_path if os.path.exists(file_path) else None
