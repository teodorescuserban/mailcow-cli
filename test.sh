#!/usr/bin/env bash

python -m pytest test_mailcow_cli.py -v --cov=mailcow_cli --cov-report=term-missing
