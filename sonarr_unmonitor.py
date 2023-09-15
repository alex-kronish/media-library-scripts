#!/tools/conda/bin/python

import requests
import json
import os
import sys
import argparse

if __name__=='__main__':
    api_key="sonarr api key goes here"
    host="http://localhost:8989"
    parser=argparse.ArgumentParser()
    parser.add_argument('-i','--EpisodeID')
    args=parser.parse_args()
    episode_id = args.EpisodeID
    api_headers={'X-Api-Key': api_key, 'Content-Type': 'application/json'}
    put_url=host+'/api/v3/episode/monitor'
    episode_data2={
        "episodeIds": [episode_id],
        "monitored":False
    }
    print("PUT | "+put_url)
    print("PUT BODY: ")
    print(json.dumps(episode_data2, indent=1))
    episode_put=requests.put(put_url, headers=api_headers, json=episode_data2)
    http_status_code_2=episode_put.status_code
    print("HTTP Status Code = "+ str(http_status_code_2))
    if http_status_code_2 < 200 or http_status_code_2 > 299:
        print("Something went wrong calling the API to unmonitor the episode")
        print(episode_put.text)
        exit(9)
    else:
        print("Successfully unmonitored...")
