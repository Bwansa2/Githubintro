#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 14 08:26:45 2021

@author: c1ph3r
"""

import pdb
import json 

def lambda_handler(event, context):
    data=(event.body) 
    return {'statusCode': 200, 'body': data} 

def json_to_file(js):
    with open(js) as data:
        file = json.load(data)
    return file
    

def main():
    '''https://jsonlint.com/   for checking validity of json file'''
    myjsonfile='ir_log.json'
    file=json_to_file(myjsonfile)
    data= json.dumps(file)
    #rint(data)
    with open('ir_log.txt', 'w') as fp:
        fp.write(data)
    
if __name__ == "__main__":
    main()