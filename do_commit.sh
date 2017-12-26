#!/bin/bash
git commit -a -m "`grep -m1 -P "^RELEASE =" rssmailer.py |sed -r "s/RELEASE\s+=\s+'//;s/'.*$//"`"
