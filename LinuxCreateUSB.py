#!/bin/python2

from Scripts import utils, downloader, run
import os
import sys
import tempfile
import shutil
import zipfile
import platform
import json
import time
import subprocess
from subprocess import call
from time import sleep
call([
    'lsblk',
    '-o',
    'NAME'])
disk = str(raw_input('Please type in name of disk: '))
disk = '/dev/' + disk
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
call([
    'dd',
    'if=4.hfs',
    outstr,
    'status=progress'])
outstr = disk + '1'
call([
    'mkfs.vfat',
    outstr])
