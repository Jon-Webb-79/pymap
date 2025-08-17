#!/bin/zsh

# reun_tests.sh

# Runs unit tests and prints results to a file with a datetime stamp

zsh unit_tests.sh > test_results.txt
mv test_results.txt ../../test/test_results.txt
