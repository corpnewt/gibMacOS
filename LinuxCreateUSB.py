#!/bin/python2

# NOTE: Pycdc is being used to format code

# CODE STARTS HERE

# Source Generated with Decompyle++
# File: LinuxCreateUSB.pyc (Python 2.7)

import os
import sys
import tempfile
import shutil
import zipfile
import platform
import time
import subprocess
import ctypes
from subprocess import call
from time import sleep
import linecache

def check_admin():
    
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    return is_admin

is_admin = check_admin()
if is_admin == False:
    print 'You must be running as root in order to use this tool!. Tap Ctrl-C to stop auto elavation. '
    sleep(3)
    print 'Attempting to elevate you via sudo'
    
    try:
        p = subprocess.Popen([
            'which',
            'sudo'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        c = p.communicate()[0].decode('utf-8', 'ignore').replace('\n', '')
        os.execv(c, [
            sys.executable,
            'python2'] + sys.argv)
    except:
        print ' An Elevation error has occured. Please share support code BUMBLEBEE'
        sys.exit(-1)

    is_admin = check_admin()
    if is_admin == False:
        print ' An Elevation error has occured. Please share support code ROOTPAW'
        sys.exit(-1)
    

def clover_input():
    
    try:
        clover_only = str(raw_input('\nWould you like to just install clover without the other stuff (Clover install failed). \nDisk must be partitioned in order to do this. \nType C to just install clover or type N to continue the full usb creation. \nType Q to exit. \nIf unsure type N\n'))
    except:
        print 'Invalid response, try again'
        clover_input()

    if clover_only == 'C':
        return 1
    if clover_only == 'N':
        return 0
    if clover_only == 'Q':
        print 'Exiting...'
        sys.exit(-1)
    else:
        print 'Invalid response, try again'
        clover_input()

clover = clover_input()
if clover == 0:
    
    try:
        call([
            'python2',
            'gibMacOS.command',
            '-r'])
    except:
        print 'gibMacOS failed to execute. Please share support code FIRESTAR'
        sys.exit(-1)

    folder_name = "'macOS Downloads'/*/*/*"
if clover == 1:
    print 'Ignore all mv errors...'

try:
    call([
        'bash',
        'Linux/PkgCopy.command'])
except:
    print 'Failed to copy pkg file. Please share support code DARKSTALKER'
    sys.exit(-1)


try:
    i = 1
    marked = 0
    while i < 200 and marked == 0:
        print 'Reading the clover download list'
        clover_url = linecache.getline('download_url.list', i)
        clover_url = clover_url.rstrip('\n')
        contains = clover_url.__contains__('lzma')
        if contains == True:
            marked = 1
        else:
            i += 1
        clover_url = linecache.getline('download_url.list', i)
        clover_url = clover_url.rstrip('\n')
    print 'Got clover download URL as: ', clover_url
except:
    print 'An unexpected error has occurred. Please share support code RAVENPAW'
    sys.exit(-1)

print 'Waiting for 3 seconds'
sleep(3)
call([
    'lsblk',
    '-o',
    'NAME'])
disk = str(raw_input('Please type in name of disk (ex: sda, sdX etc.): '))
disk = '/dev/' + disk
if clover == 0:
    confirm_str = 'WARNING: This will delete all data on ' + disk + '.\nIf you want to continue, wait for 3 seconds. Otherwise hit Ctrl-C\n'
    print confirm_str
    sleep(3)
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
    print "Image extraction in progress...\nType Y when asked if you are not sure.\nIn general, delete old files in checkout to solve the 'problem'. "
    sleep(3)
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
    print 'Image will now be written to device.\nPlease be patient!'
    call([
        'dd',
        'if=4.hfs',
        outstr,
        'status=progress'])
outstr = disk + '1'
print 'Installing CLOVER on ', outstr, '\nPlease wait...'
sleep(3)
call([
    'mkfs.vfat',
    outstr])
call([
    'rm',
    '-rf',
    '*.tar.lzma',
    '*.iso'])
call([
    'wget',
    clover_url])
print "Clover extraction might error out. If so, don't panic. Just install it manually by extracting and mounting iso and copying all files to your USB."
sleep(3)
call([
    'mkdir',
    'bootdir'])
call([
    'mount',
    outstr,
    'bootdir'])
call([
    'bash',
    'Linux/CloverExtract.command'])
