# -*- shell-mode -*-
# This file is a docker (https://www.docker.com/what-docker) recipe, which can be used to build
# a docker image which is ready to run a datatracker in development mode.
#
# It is used to build an image (once you've installed docker) using a command like this (assuming
# suitable replacement of $variables:
#
#	$ docker build -t $yourdockerid/datatracker:$version
#
# To use a pre-built image, assuming we're on OS X and have a checked-out datatracker repository
# at /Users/$login/src/6.8.1.dev0, you would start (again assuming you've installed docker)
# a container from an image, as follows:
# 
#	$ docker run -ti --name=$containername -v /Users/$login:/home/$login levkowetz/datatracker:$version /bin/bash
# 
# This maps your home directory to /home/$login in the container, and starts it running /bin/bash.
# 
# In this first version, the docker environment is set up so that tests will run successfully,
# but the database has *not* been loaded with a dump, and supporting files (drafts, charters, etc.)
# have *not* been downloaded.

FROM debian:wheezy
MAINTAINER Henrik Levkowetz <henrik@levkowetz.com>

# Default django runserver port
EXPOSE	8000

# Use backports
RUN echo "deb http://http.debian.net/debian wheezy-backports main contrib non-free" >> /etc/apt/sources.list

# Run apt-get noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install needed packages
#
# We're not including graphviz and ghostscript, needed for the 3 document
# dependency graph tests; they would increase the size of the image by about
# 15%, about 100MB.
#
RUN apt-get update && apt-get install -qy \
	bzip2 \
	ca-certificates \
	colordiff \
	gawk \
	ipython \
	less \
	libfreetype6 \
	libfontconfig \
	libjpeg8-dev \
	libmysqlclient-dev \
	libsvn1/wheezy-backports \
	libxml2-dev \
	libxslt-dev \
	locales \
	man \
	mysql-server \
	openssh-client \
	procps \
	pv \
	python \
	python-dev \
	python-m2crypto \
	python-subversion \
	realpath \
	rsync \
	subversion/wheezy-backports \
	sudo \
	vim \
	wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Enable some common locales
RUN sed -i -e 's/^. en_US/en_US/' -e 's/^. en_GB/en_GB/' -e 's/^. en_IE/en_IE/' /etc/locale.gen
RUN locale-gen

# Set up root password
RUN echo "root:root" | chpasswd

# MySQL
VOLUME /var/lib/mysql

# Pip
ENV PYTHONWARNINGS="ignore:a true SSLContext object,ignore:An HTTPS request has been made"
WORKDIR /usr/src
RUN wget -q https://bootstrap.pypa.io/get-pip.py && python get-pip.py && rm get-pip.py
RUN pip install certifi
RUN pip install virtualenv

# Phantomjs
WORKDIR /usr/local
RUN wget -q https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-1.9.7-linux-x86_64.tar.bz2 \
	&& tar xjf phantomjs-1.9.7-linux-x86_64.tar.bz2 
WORKDIR /usr/local/bin
RUN ln -s /usr/local/phantomjs-1.9.7-linux-x86_64/bin/phantomjs .

# idnits and dependencies
RUN wget -q -P /usr/local/bin/ https://tools.ietf.org/tools/idnits/idnits && chmod +x /usr/local/bin/idnits

ENV DDIR="/usr/local/share/datatracker"
RUN mkdir -p $DDIR
WORKDIR $DDIR

COPY requirements.txt ./
RUN pip --no-cache-dir install -r requirements.txt

COPY settings_local.py ./
COPY setprompt ./

COPY docker-init.sh /docker-init.sh
RUN chmod +x /docker-init.sh
ENTRYPOINT ["/docker-init.sh"]

CMD	/bin/bash