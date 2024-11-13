#!/bin/bash -e

# Cloning git repository
echo 'Cloning git repository'
cd /home/pi
#sudo -u "${FIRST_USER_NAME}" git clone https://github.com/jonnerd154/StargateProject-software sg1_v4
git clone -b ci https://github.com/ajtudela/StargateProject-software sg1_v4
sudo chown -R "${FIRST_USER_NAME}":"${FIRST_USER_NAME}" sg1_v4
ls -la