#!/tools/conda/envs/Plex/bin/python

#import os
import sys
import argparse
#import datetime
#import time
import requests


# This script exists specifically because the linux Plex Medida Scanner seems to be broken, 
# it always seems to crash and the .dmp file it references never seems to exist, making troubleshooting impossible.
plex_token={'X-Plex-Token':'Plex Token goes here. You can get this by viewing the XML in the plex web interface for any media item'}
port_num='32400'
ip_addr='192.168.2.124' #replace with the IP of your plex server, or localhost if you're doing this on the same box.

if __name__=='__main__':
    script_name=sys.argv[0]
    parser=argparse.ArgumentParser()
    parser.add_argument("--LibraryID",required=True)
    args=parser.parse_args()
    library_id=args.LibraryID
    print("*****************************************************")
    print("* Script: "+script_name)
    print("* LibraryID: "+library_id)
    print("*****************************************************")
    url='http://'+ip_addr+':'+port_num+'/library/sections/'+library_id+'/refresh'
    req=requests.get(url,params=plex_token)
    http_response_code=req.status_code
    response_body=req.text
    req_url=req.url
    print("GET | "+req_url)
    print("    HTTP Status Code: "+str(http_response_code))
    print("    JSON Response:")
    print(response_body)
    print("")
    print("done")
