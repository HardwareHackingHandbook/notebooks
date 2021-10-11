#!/bin/bash
#. /home/user/.pyenv/versions/cw/bin/activate
cd /home/user/work/projects/chipwhisperer
echo "running jupyter" > ../cronjupyter.log
export BOKEH_RESOURCES=inline
jupyter notebook --no-browser 2>> ../jupyter.log >> ../jupyter.log
echo "Notebook didn't run or stopped!" >> ../cronjupyter.log
