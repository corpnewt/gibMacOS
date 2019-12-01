# API: 2

printf 'NOTE: On FreeBSD and macOS, this step has a 50% chance of failing. Also there may be some looks-like errors but these are fake and harmless\n'

# For some reason, python has tarfile issues, to fix this, we extract clover by outselves
tar -xvf *.tar.lzma
printf "Clover successfully extracted\n"
mkdir srcdir
mount *.iso srcdir # Attempt 1
mount_msdosfs *.iso srcdir # Attempt 2
mount -t cd9660 -o ro /dev/`mdconfig -o readonly -f *.iso` srcdir # Attempt 3
printf "Clover is now mounted on srcdir\n"
cp -rf srcdir/* bootdir
printf "Clover successfully installed. Cleaning up... \n"
umount srcdir bootdir
rm -rvf srcdir bootdir *.tar.lzma 
# Don't remove *.iso 
