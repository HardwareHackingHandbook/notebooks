# notebooks
Companion notebooks to the Hardware Hacking Handbook. These are the Jupyter notebooks found under `labs/`.

# Downloading a ready made VM
You can get a ready made VM [here](https://dl.hardwarehacking.io/Hardware%20Hacking%20Handbook%20Jupyter.ova). The SHA512 checksum is [here](https://dl.hardwarehacking.io/Hardware%20Hacking%20Handbook%20Jupyter.ova.sha512sum). It was built using the instructions below. We recommend you use this option, as it is the least error-prone.

# VM build for Hardware Hacking Handbook
The `vm-builder` containings the needed vagrant file and scripts for building the HHH Jupyter vm. It should take care of everything needed, including installing packages, installing python modules using pip, enabling needed jupyter extensions, and running jupyter. It's based on chipwhisperer-vagrant.

The created VM is called Hardware Hacking Handbook Jupyter.

## Building the VM
To build the VM, run `build.sh`. It requires vagrant and Virtualbox to be installed. In Windows, you may need the [vagrant-wsl2 plugin](https://stackoverflow.com/questions/65001570/connection-refused-in-vagrant-using-wsl-2), and read [Vagrant on WSL2](https://www.vagrantup.com/docs/other/wsl)

During the VM build, a `solutions/` subdirectory is created, which has the output of all the notebooks as PDF. (Spoiler alert!)

## Connecting to Jupyter
Jupyter can now be connected to via `localhost:8888`. The default password is '123456hhh', without quotes. If you need to log into the VM itself, you can use username 'root' and password 'vagrant'.

Note: Jupyter is essentially remote code execution as a service. Though it's somewhat sandboxed inside Docker inside the VM, take care of what networks you expose it it.

**JUYPTER CAN ONLY BE CONNECTED TO ON FIREFOX/CHROME, EDGE/SAFARI DON'T WORK, OTHER BROWSERS UNTESTED**
## Potential Issues and Troubleshooting
Most issues occur when moving the VM to a new machine.

* VM Freezes on Boot
    * This is typically caused by Serial Port 1 being disabled. It can be fixed by enabling it and setting Port Mode to Disconnected
* Permission Error when running VM
    * Usually caused by trying to run the VM on a Unix-like host off an NTFS filesystem (say a USB flash drive). Can be fixed by copying the VM files onto the host's normal file system
