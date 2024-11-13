#!/bin/bash -e

# Cloning git repository
echo 'Cloning git repository'
cd /home/pi
sudo -u "${FIRST_USER_NAME}" git clone https://github.com/jonnerd154/StargateProject-software sg1_v4
