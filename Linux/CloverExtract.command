# For some reason, python has tarfile issues, to fix this, we extract clover by outselves
tar -xvf *.tar.lzma
printf "Clover successfully extracted\n"
mkdir srcdir
mount *.iso srcdir
printf "Clover successfully mounted\n"
cp -rf srcdir/* bootdir
printf "Clover successfully installed. Cleaning up... \n"
umount srcdir bootdir
rm -rvf srcdir bootdir *.iso *.tar.lzma
