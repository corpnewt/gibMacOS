#!/bin/bash
# Autor: Broly
# License: GNU General Public License v3.0
# https://www.gnu.org/licenses/gpl-3.0.txt
# This script is inteded to create a opencore usb-installer on linux just like
#'Makeinstall.py" does on windows there for it should be executerd
# from /gibMacOS-master/ directory.
# dependency gibmacos https://github.com/corpnewt/gibMacOS

RED="\033[1;31m\e[3m"
NOCOLOR="\e[0m\033[0m"
YELLOW="\033[01;33m\e[3m"
set -e

# Checking for root Identifying distro pkg-manager and installing dependencies.
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be executed as root!${NOCOLOR}"
    exit 1
fi

echo -e "\e[3mWe need to install some important tools to proceed!\e[0m"
sleep 3s

declare -A osInfo;
osInfo[/etc/debian_version]="apt install -y"
osInfo[/etc/alpine-release]="apk --update add"
osInfo[/etc/centos-release]="yum install -y"
osInfo[/etc/fedora-release]="dnf install -y"
osInfo[/etc/arch-release]="pacman -S --noconfirm"

for f in ${!osInfo[@]}
do
    if [[ -f $f ]];then
        package_manager=${osInfo[$f]}
    fi
done
echo -e "\e[3mInstalling Depencencies...\e[0m"
package="wget curl p7zip"
package1="wget curl p7zip"
package2="wget curl p7zip-full"

if [ "${package_manager}" = "pacman -S --noconfirm" ]; then
    ${package_manager} ${package1}
    
    elif [ "${package_manager}" = "apt install -y" ]; then
    ${package_manager} ${package2}
    
    elif [ "${package_manager}" = "yum install -y" ]; then
    ${package_manager} ${package1}
    
    elif [ "${package_manager}" = "dnf install -y" ]; then
    ${package_manager} ${package}
    
else
    echo -e "${YELLOW}Warning: Your distro is not supported!${NOCOLOR}"
    echo -e "You must install the following tools: wget, curl and p7zip"
    while true
    do
    read -r -p "Want to continue at risk? (y/n) " input
    case $input in
        [yY])
    break
    ;;
        [nN])
    exit 1
    ;;
     *)
    echo "Invalid input..."
    ;;
    esac
    done
    
fi

# Simple menu to select the Downloaded version of macOS only usefull if you download
# multiple versions.
cd "$(dirname "$(find ./ -name "publicrelease")")"
cd publicrelease
echo -e "${YELLOW}Please select the downloaded macOS image!${NOCOLOR}"
if select d in */; do test -n "$d" && break; echo -e "${RED}>>> Invalid Selection !${NOCOLOR}"; done
then
    
    # checking if we have recovery.pkg  to proceed.
    
    cd "$d"
    FILE=(RecoveryHDMetaDmg.pkg)
    FILE1=(*.RecoveryHDUpdate.pkg)
    if [ -f "$FILE" ]; then
        echo "Using $FILE"
        7z e -txar $FILE *.dmg
        7z e *.dmg */Base*.dmg
        7z e -tdmg Base*.dmg *.hfs
        mv *.hfs base.hfs
        sleep 3s
        
        elif [ -f "$FILE1" ]; then
        mv $FILE1 $FILE
        7z e -txar $FILE *.dmg
        7z e *.dmg */Base*.dmg
        7z e -tdmg Base*.dmg *.hfs
        mv *.hfs base.hfs
        sleep 3s
        
    else
        echo -e "${YELLOW}Please Download macOS with gibmacos!${NOCOLOR}"
        exit 1
    fi
    
fi
# Print disk devices
# Read command output line by line into array ${lines [@]}
# Bash 3.x: use the following instead:
#   IFS=$'\n' read -d '' -ra lines < <(lsblk --nodeps -no name,size | grep "sd")
readarray -t lines < <(lsblk --nodeps -no name,size | grep "sd")

# Prompt the user to select the drive.
echo -e "${RED}WARNING: THE SELECTED DRIVE WILL BE FORMATED !!!${NOCOLOR}"
echo -e "${YELLOW}Please select the usb-drive!${NOCOLOR}"
select choice in "${lines[@]}"; do
    [[ -n $choice ]] || { echo -e "${RED}>>> Invalid Selection !${NOCOLOR}" >&2; continue; }
    break # valid choice was made; exit prompt.
done

# Split the chosen line into ID and serial number.
read -r id sn unused <<<"$choice"

# Move the recovery to /tmp delete everything in the current directory then bring it back.
teleport(){
if
mv $FILE /tmp/
sleep 2s
then
rm -rf *.*
mv /tmp/$FILE .
sleep 2s
else
exit 1
fi
}


# Here we partition the drive and dd the raw image to it.
partformat(){
if
  umount $(echo /dev/$id?*) > /dev/null 2>&1 || :
sleep 3s
    sgdisk --zap-all /dev/$id > /dev/null 2>&1
    sgdisk /dev/$id --new=0:0:+300MiB -t 0:ef00
    partprobe $(echo /dev/$id?*)
    sgdisk -e /dev/$id --new=0:0:+7000MiB -t 0:af00
    partprobe $(echo /dev/$id?*)
    sleep 3s
echo -e "\e[3mCopying image to usb-drive!\e[0m"
dd bs=8M if="$PWD/base.hfs" of=$(echo /dev/$id)2 status=progress oflag=sync
teleport
then
umount $(echo /dev/$id?*) > /dev/null 2>&1 || :
sleep 3s
else
  exit 1
fi
}

while true; do
    read -p "$(echo -e ${YELLOW}"Drive ($id) will be erased, do you wish to continue (y/n)? "${NOCOLOR})" yn
    case $yn in
        [Yy]* ) partformat; break;;
        [Nn]* ) teleport; exit;;
        * ) echo -e "${YELLOW}Please answer yes or no."${NOCOLOR};;
    esac
done

# Format the EFI partition for opencore
# and mount it in the /mnt.
if
mkfs.fat -F32 -n EFI $(echo /dev/$id)1
then
   mount -t vfat  $(echo /dev/$id)1 /mnt/ -o rw,umask=000; sleep 3s
else
  exit 1
fi

# Install opencore.
echo -e "\e[3mInstalling OpenCore!!\e[0m"
sleep 3s

# OpenCore Downloader fuction.

    if
    curl "https://api.github.com/repos/acidanthera/OpenCorePkg/releases/latest" \
    | grep -i browser_download_url \
    | grep RELEASE.zip \
    | cut -d'"' -f4 \
    | wget -qi -
    then
        7z x *RELEASE.zip -o/mnt/
    else
        exit 1
    fi
    sleep 5s
    chmod +x /mnt/
    rm -rf *RELEASE.zip
    umount $(echo /dev/$id)1
    mount -t vfat  $(echo /dev/$id)1 /mnt/ -o rw,umask=000
    sleep 3s

echo -e "\e[3mInstallation finished, open /mnt and edit oc for your machine!!\e[0m"
