#!/bin/bash

set -ex

sudo systemctl stop procurando_bitucas.service
pyenv activate bitucas

git pull origin orangepi

python -m pip install .

sudo systemctl start procurando_bitucas.service
systemctl status procurando_bitucas.service
