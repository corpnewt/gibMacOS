#!/usr/bin/env python2

# API: 2.1 (Incompatible with 2)
# Older USBCreator scripts (in USBCreate) and patches will not work until it is updated and/or ported to the above new API

# CUSTOM MODULE SPECIFICATIONS AND INFO FOR API 2:
# 
# * All custom modules must use the module() function to load the module, other functions are allowed internally, but all returns must be done from module()
# * All custom modules must return list t_mod_out (eventually becomes mod_out) with the mod_out item structure and ONLY the below items
# * task_id states the action taking place. It is an integer. There are some special actions like the below:
# * Value 100 for task_id means user has finished exp_test
# * Value 99 for task_id means user is still in clover_input or another input function
# * Value 98 for task_id means user is exiting from clover_input or another input function 
#
# * mod_out item structure
# * 0: p_id (use '-3' for no change) - Integer: PlatformID
# * 1: exp (use '-3' for no change) - String: ExperimentalPlatformVar
# * 2: dd (use '-3' for no change) - String: DD_Command
# * 3: pprobe (use '-3' for no change) - String: Partprobe_Command
# * 4: dosfs (use -3 for no change) - String: DosFsTools_Command
# * 5: misc_data - Nested List (this list goes in the mod_out list): MiscData
# 
# * A note on misc_data: only use this when needed and not used by any other module, as data entries by custom modules cannot and should not conflict (Think Flowol))
#
# * Good programmers should try to keep misc_data empty and do all checks in the module itself. It is only being provided for certain use cases in which data has to be stored for a long time.
# * Be warned that non-official custom modules are dangerous and can severely damage your computer
from __future__ import print_function # Use python3 prints in python 2
from six.moves import input as raw_input # python 3 raw_input support
import six
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
import platform

# Setup custom modules NOW (these may provide additional functionality, add support for now platforms or fix bugs (this will be expanded in API 3))
def check_module(api):
    if api != 2.1:
        print('Module uses API: ', api, ', but this version of USBCreator only supports API 2.1.')
        sys.exit(-1)
	
## Add custom USBCreate imports here (or to end if you wish) ##
import USBCreateClearScreen
check_module(USBCreateClearScreen.api) # Do this for modules unless specified otherwise

# task_id is where USBCreate is in execution. You can add code before it runs via this argument, modifying or patching code is coming in API 3 

global mod_out # It has to be global throughout all code
mod_out = ['-3', '-3', '-3', '-3', '-3', []] # Mod_out's structure
global t_mod_out # Same thing here
t_mod_out = mod_out # Initially they are the same
def modpost(task_id):
    global p_id
    global dd
    global pprobe
    global dosfs
    global misc_data
    global exp
    # Register custom USBCreate imports here (usually mod_out = module_name.module(arg)) ##
    # Structure:
    # t_mod_out = module_name.module(args)                        			# DESCRIPTION

    t_mod_out = USBCreateClearScreen.module(task_id)                   			# Clear Screen [OFFICIAL]

    # DO NOT CHANGE THE BELOW
    # Process element 0
    try:
        if t_mod_out[0] != '-3':
            mod_out[0] = t_mod_out[0]
            p_id = mod_out[0]
        if t_mod_out[1] != '-3':
            mod_out[1] = t_mod_out[1]
            exp = mod_out[1]
        if t_mod_out[2] != '-3':
            mod_out[2] = t_mod_out[2]
            dd = mod_out[2]
        if t_mod_out[3] != '-3':
            mod_out[3] = t_mod_out[3]
            pprobe = mod_out[3]
        if t_mod_out[4] != '-3':
            mod_out[4] = t_mod_out[4]
            dosfs = mod_out[4]
        mod_out[5] = t_mod_out[5] # No matter what, set misc_data in mod_out[5]
        misc_data = mod_out[5]
    except:
        print('Failed to load custom modules. Please remove bad or old custom modules. The support code for this error is CLEAR_SKY')
        sys.exit(-1) 
# And you're done...

## Actual USBCreator code, do not change this
# Get macOS, Linux or FreeBSD
modpost(0)
os_name = platform.system()
if os_name == 'Darwin':
    print('Found OS: macOS\nNote: Partprobe will not work so you need to make sure that said disk is unmounted and not in use. You will also need p7zip, dosfstools and gptfdisk installed. These can be installed from brew, MacPorts or from source\nPlease install all dependencies or USBCreator will not work correctly')
    p_id = 1
    exp = 1
    dd = 'gdd' # Needed for status=progress. (TODO: use --progress instead of status=progress on macOS. ASR may also be a good choice as well)
    pprobe = 'echo'
    dosfs = 'mkfs.vfat'
elif os_name == 'FreeBSD':
    print('Found OS: FreeBSD\nYou will need to have lsblk,  coreutils, gdisk and p7zip installed from pkg. Some or all functionality may be buggy and/or missing and partitioning may not work properly or at all')
    p_id = 2
    exp = 1
    dd = 'dd'
    pprobe = 'echo'
    dosfs = 'newfs_msdos'
elif os_name == 'Linux':
    print('Found OS: Linux\nThis should work correctly but may still have bugs. Not considered fully experimental however as I have tested it and it works.\nYou need p7zip, gptfdisk, dosfstools, parted and coreutils installed for this to work correctly or at all\nYou need p7zip AND p7zip-plugins on Fedora')
    p_id = 3
    exp = 0
    dd = 'dd'
    pprobe = 'partprobe'
    dosfs = 'mkfs.vfat'
else:
    print('')
try:
    test_var = p_id
except:
    print('Unsupported OS: ', os_name, '\nPlease ask for support at https://github.com/corpnewt/gibmacOS')
    p_id = -1
    sys.exit(-1)

def wait_for_input():
	wait_for_input = str(raw_input('\n\nHit ENTER once you have finished reading to continue: '))
wait_for_input()
# implement this for custom modules to use exp
def exp_test():
    if exp == 1:
        exp_test_input = str(raw_input('This configuration is EXPERIMENTAL. Are you sure you wish to continue (Y/N)? '))
        if exp_test_input == 'Y' or exp_test_input == 'y':
            return 0
        elif exp_test_input == 'N' or exp_test_input == 'n':
            print('Exiting...')
            modpost(98)
            sys.exit(-1)
        else:
            print('Invalid response, try again in 2 seconds... ')
            time.sleep(2)
            modpost(99)
            exp_test()
        time.sleep(3)
modpost(1)
exp_test()
modpost(100)
def check_admin():
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    return is_admin

is_admin = check_admin()
if is_admin == False:
    print('You must be running as root in order to use this tool!. Tap Ctrl-C to stop auto elavation. ')
    sleep(3)
    print('Attempting to elevate you via sudo')
    
    try:
        p = subprocess.Popen([
            'which',
            'sudo'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        c = p.communicate()[0].decode('utf-8', 'ignore').replace('\n', '')
        if six.PY2:
            os.execv(c, [
                sys.executable,
                'python2'] + sys.argv)
        else:
            # User is using python3
            os.execv(c, [
                sys.executable,
                'python3'] + sys.argv)
    except:
        print('An Elevation error has occured. Please share support code BUMBLEBEE')
        sys.exit(-1)

    is_admin = check_admin()
    if is_admin == False:
        print('An Elevation error has occured. Please share support code ROOTPAW')
        sys.exit(-1)
    
modpost(2)
a = str(raw_input('NOTE: USBCreate does not install Clover or Opencore.\nYou must do this by yourself using any hackintosh guide\n\nPlease hit ENTER to continue: '))
modpost(3)
try:
    print('Going to run gibMacOS.\nPlease choose the version of macOS you want.\nNOTE: You may change your catalog to get betas or other specific builds.\nNOTE 2: Please also ensure that you have picked and downloaded only 1 version of macOS. You may remove "macOS Downloads" and *.dmg/*.hfs to do this.')
    print('Hit ENTER to continue\n')
    tmp_var = raw_input('')
    modpost(999) # Use 999 to avoid conflict and complex rename
    if(six.PY2):
        call([
            'python2',
            'gibMacOS.command',
            '-r'])
    else:
        # User is using python3
        call([
            'python3',
            'gibMacOS.command',
            '-r'])
except:
    print('gibMacOS failed to execute. Please share support code FIRESTAR')
    sys.exit(-1)
folder_name = "'macOS Downloads'/*/*/*"
modpost(4)
try:
    call([
        'bash',
        'USBCreator/PkgCopy.command'])
except:
    print('Failed to copy pkg file. Please share support code DARKSTALKER')
    sys.exit(-1)
modpost(5)
print('Waiting for 3 seconds')
sleep(3)
if(p_id == 3):
    call([
        'lsblk',
        '-o',
        'NAME'])
if(p_id == 1):
    call([
        'diskutil',
        'list'])
if(p_id == 2):
    call([
        'lsblk'])
disk = str(raw_input('Please type in name of disk (ex: sdX, diskX, rdiskX etc.): '))
if(disk.__contains__('/dev/')):
    pass
else:
    disk = '/dev/' + disk
modpost(6)
#TODO: Add a way for modules to add more magic num tests
if(disk.__contains__('/dev/sd')):
    magic_num = ''
elif(disk.__contains__('/dev/nvme')):
    magic_num = 'p'
elif(disk.__contains__('/dev/disk')):
    magic_num = 's'
elif(disk.__contains__('/dev/rdisk')):
    magic_num = 's'
else:
    magic_num = str(raw_input('Please enter magic number now. This number is what sits between the disk and partition number.\nFor example in /dev/disk1sX, the magic number is s and in /dev/sdaX, the magic number is '' (just hit enter)\nIf you do not know this, enter lsblk or diskutil list to find out. Hit ENTER for /dev/sdXY cases where there is no magic number (or letter)\n'))
modpost(7)
confirm_str = 'WARNING: This will delete all data on ' + disk + '.\nIf you want to continue, wait for 3 seconds. Otherwise hit Ctrl-C\n'
print(confirm_str)
sleep(3)
call([
    'sgdisk',
    '--zap-all',
    disk])
call([pprobe])
call([
    'sgdisk',
    '-n1:1M:+1G', # Large size of greater than 1G is needed for FreeBSD's stupid newfs_msdos unless we use FAT16. Otherwise we reach an error over clusters
    '-t1:0700',
    disk])
call([
    'sgdisk',
    '-n2:0:0',
    '-t2:af00',
    disk])
call([
    pprobe])
modpost(8)
print('Image extraction in progress...\nType Y when asked if you are not sure.\nIn general, you should start with a clean download of gibMacOSto solve any extraction issues. ')
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
modpost(9)
outstr = 'of=' + disk + magic_num + '2'
print('Image will now be written to device.\nPlease be patient!')
sleep(5)
call([
    dd,
    'if=4.hfs',
    'bs=1M', # Needed for FreeBSD and MacOS for good write speeds 
    'status=progress',
    outstr])
efi_part = disk + magic_num + '1'
modpost(10)
sleep(3)
print("Formatting EFI on", efi_part, "...")
call([
    dosfs,
    efi_part])
bye_bye = str(raw_input("All Done!\n\nHit ENTER to exit: "))
modpost(11)
