#!/bin/python2

import os
import sys
import tempfile
import shutil
import zipfile
import platform
import json
import time
import subprocess
import ctypes
from subprocess import call
from time import sleep
import linecache
# From utils.py
def check_admin():
	# Returns whether or not we're admin
	try:
		is_admin = os.getuid() == 0
	except AttributeError:
		is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
	return is_admin
is_admin = check_admin()
if(is_admin == False):
	print("You must be running as root in order to use this tool!\nAttempting to elevate you via sudo")
	try:
		# From utils.py elevate()
		p = subprocess.Popen(["which", "sudo"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		c = p.communicate()[0].decode("utf-8", "ignore").replace("\n", "")
		os.execv(c, [ sys.executable, 'python2'] + sys.argv)
	except:
		print("Elevation error occured")
		sys.exit(-1)
	is_admin = check_admin()
	if(is_admin == False):
		print("Elevation error occured")
		sys.exit(-1)
# Hacky solution, but it works
try:
	call(["python2","gibMacOS.command"])
except:
	print("gibMacOS failed to execute")
	sys.exit(-1)
folder_name = "'macOS Downloads'/*/*/*"
try:
	call(['bash','PkgCopy.command'])
except:
	print("Failed to copy pkg file")
	sys.exit(-1)
# Now get clover from download_url.list
try:
	i = 1
	marked = 0
	# This should be enough right (?)
	while(i < 200 and marked == 0):
		clover_url = linecache.getline('download_url.list', i)
		clover_url = clover_url.rstrip("\n")
		contains = clover_url.__contains__("lzma")
		if(contains == True):
			marked = 1
		else:
			i+=1
		clover_url = linecache.getline('download_url.list', i)
		clover_url = clover_url.rstrip("\n")
	print "URL: ", clover_url
except:
	print("An unexpected error has occurred")
	sys.exit(-1)
print("Waiting for 3 seconds")
sleep(3)
# From pycdac
call([
    'lsblk',
    '-o',
    'NAME'])
disk = str(raw_input('Please type in name of disk: '))
disk = '/dev/' + disk
confirm_str = 'WARNING: This will delete all data on ' + disk + '.\nIf you want to continue, wait for 3 seconds. Otherwise hit Ctrl-C\n'
print confirm_str
sleep(3)
# Partition disks
call([
    'sgdisk',
    '--zap-all',
    disk])
call([
    'partprobe'])
call([
    'sgdisk',
    '-n1:1M:+512M',
    '-t1:0700',
    disk])
call([
    'sgdisk',
    '-n2:0:0',
    '-t2:af00',
    disk])
call([
    'partprobe'])
# Extract images
call([
    '7z',
    'e',
    '-txar',
    '*.pkg',
    '*.dmg'])
call([
    '7z',
    'e',
    '*.dmg',
    '*/Base*'])
call([
    '7z',
    'e',
    '-tdmg',
    'Base*.dmg',
    '*.hfs'])
outstr = 'of=' + disk + '2'
# Write image
call([
    'dd',
    'if=4.hfs',
    outstr,
    'status=progress'])
outstr = disk + '1'
# Install CLOVER
call([
    'mkfs.vfat',
    outstr])
#call(["rm", "-rf", clover_url, "*.iso"])
#call(["wget", clover_url])
#call(["tar", "-xvf", "*.lzma"])
#call(["mkdir", "srcdir"])
#call(["mount", "*.iso", "srcdir"])
#call(["mkdir", "bootdir"])
#call(["mount", outstr, "bootdir"])
#call(["cp", "-rf", "srcdir/*", "bootdir"])
