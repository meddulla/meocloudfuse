#!/usr/bin/env bash

apt-get update

# python virtual env
apt-get -y install python-pip python-dev
apt-get -y install virtualenvwrapper

export WORKON_HOME
echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bashrc

apt-get -y install fuse