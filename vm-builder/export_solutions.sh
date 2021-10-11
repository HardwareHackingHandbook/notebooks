#!/bin/sh

# Run all notebooks to produce static output
cd /home/user/work/projects/chipwhisperer/0_Hardware_Hacking_Handbook_0 && jupyter nbconvert --to webpdf --output-dir ./solutions/ --allow-chromium-download --execute *.ipynb
