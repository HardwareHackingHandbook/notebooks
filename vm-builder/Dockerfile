FROM ubuntu:latest

SHELL ["/bin/bash", "-c"]

RUN apt-get -y update && DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata
RUN apt-get -y install udev cron python3.8 python3-pip libgmp-dev curl git net-tools build-essential make libssl-dev zlib1g-dev libbz2-dev	 libreadline-dev libsqlite3-dev wget libncurses5-dev libncursesw5-dev	 xz-utils tk-dev libffi-dev liblzma-dev  gcc-avr	 avr-libc	 gcc-arm-none-eabi	 jq	 pandoc	 libmpfr-dev libmpc-dev	 vim	 usbutils	 libusb-1.0.0-dev firefox-geckodriver  gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget chromium-driver && apt-get clean

RUN adduser --disabled-password --gecos "" user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

RUN git config --global user.name "user" && git config --global user.email "user@example.com" && git config --global core.autocrlf true
RUN mkdir -p /home/user/work/projects && cd /home/user/work/projects && git clone https://github.com/newaetech/chipwhisperer && cd chipwhisperer && git checkout develop # XXX 5.6.1
#RUN cd /home/user/work/projects/chipwhisperer && git pull && git submodule init jupyter/ && git submodule update

RUN pip install wheel
RUN pip install --upgrade pip
RUN pip install cufflinks plotly phoenixAES terminaltables numpy nbparameterise gmpy2 scared fastdtw fastecdsa selenium bokeh cycler datashader jupyter_client jupyter jupyter_contrib_nbextensions pandas holoviews matplotlib PyYAML tqdm colorama PyCryptoDome ipywidgets nbconvert pyppeteer && pip cache purge

USER root
RUN cd /home/user/work/projects/chipwhisperer; python3 setup.py develop

# USB permissions
	RUN cp /home/user/work/projects/chipwhisperer/hardware/*-newae.rules /etc/udev/rules.d/
RUN usermod -a -G plugdev user && usermod -a -G dialout user

# copy cron script from user folder
USER user
COPY --chown=user run_jupyter.sh export_solutions.sh /home/user/
RUN chmod oug+x /home/user/run_jupyter.sh /home/user/export_solutions.sh

# jupyter stuff
RUN jupyter contrib nbextension install --user
RUN python3 -m notebook.auth password 123456hhh

# copy jupyter config
RUN mkdir -p /home/user/.jupyter
COPY --chown=user jupyter_notebook_config.py /home/user/.jupyter/

# Enable jupyter extensions
RUN jupyter nbextension enable toc2/main
RUN jupyter nbextension enable collapsible_headings/main
RUN jupyter nbextensions_configurator enable --user

# XXX TODO this should become a git clone
COPY --chown=user labs "/home/user/work/projects/chipwhisperer/0_Hardware_Hacking_Handbook_0"

ENTRYPOINT /home/user/run_jupyter.sh
