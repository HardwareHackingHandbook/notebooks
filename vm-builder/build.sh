#!/bin/bash

HHH="Hardware Hacking Handbook Jupyter"
URL="https://nostarch.com/hardwarehacking"

vagrant destroy # remove lingering copies, will ask for user permission

set -e          # quit on error
cp -r ../labs . # Copy labs into current directory so they get included in the VM 
vagrant up      # Build the vm
vagrant halt    # Done building, turn orf the VM
VBoxManage sharedfolder remove "$HHH" --name vagrant    # Shared folder no longer needed
VBoxManage export "$HHH" --output "$HHH.ova" --manifest --vsys 0 --vmname "$HHH" --producturl "$URL" # Package the VM up
sha512sum "$HHH.ova" > "$HHH.ova.sha512sum"
