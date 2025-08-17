#!/bin/zsh

# tun_tests.sh
# Runs unit tests, and prints results to a file with a datetime

cd ../../test
pytest -v
date
cd ../scripts/zsh
