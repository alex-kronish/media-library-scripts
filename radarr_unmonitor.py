#!/tools/conda/bin/python

import requests
import json
import os
import sys
import argparse

if __name__=='__main__':
    api_key="radarr api key goes here"
    host="http://localhost:7878"
    parser=argparse.ArgumentParser()
    parser.add_argument('-i','--MovieID')
    args=parser.parse_args()
    movie_id = args.MovieID
    api_headers={'X-Api-Key': api_key, 'Content-Type': 'application/json'}
    get_url=host+'/api/v3/movie/'+movie_id
    put_url=host+'/api/v3/movie/'+movie_id+'?moveFiles=false'
    print("GET | "+get_url)
    movie_get=requests.get(get_url, headers=api_headers)
    http_status_code_1=movie_get.status_code
    print("HTTP Status Code = "+ str(http_status_code_1))
    if http_status_code_1 < 200 or http_status_code_1 > 299:
        print("Something went wrong calling the API to get movie data")
        print(movie_get.text)
    else:
        movie_data=movie_get.json()
        movie_data['monitored']=False
        print("PUT | "+put_url)
        print("PUT BODY: ")
        print(json.dumps(movie_data, indent=1))
        movie_put=requests.put(put_url, headers=api_headers, json=movie_data)
        http_status_code_2=movie_put.status_code
        print("HTTP Status Code = "+ str(http_status_code_2))
        if http_status_code_2 < 200 or http_status_code_2 > 299:
            print("Something went wrong calling the API to unmonitor the movie")
            print(movie_put.text)
            exit(9)
        else:
            print("Successfully unmonitored...")
