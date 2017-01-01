#!/bin/bash

fuser -k 5005/tcp
python android_version_checker.py
