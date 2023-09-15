#!/tools/conda/bin/python

import os
import sys
import shutil
import argparse
import subprocess

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('-f','--SourceFile')
    args=parser.parse_args()
    src_file=args.SourceFile
    source_file_list=src_file.split(os.path.sep)
    source_file_list.remove("")
    source_file_list.remove("data")
    source_file_list.remove("Sonarr")
    print("source file list:")
    print(str(source_file_list))
    series_folder_name = source_file_list[0].replace('\'','')
    season_folder_name = source_file_list[1].replace('\'','')
    episode_file_name= source_file_list[2].replace('\'','')
    plex_base='/data/TV Shows'
    qualified_series_folder_name=os.path.join(plex_base,series_folder_name)
    qualified_season_folder_name=os.path.join(qualified_series_folder_name,season_folder_name)
    qualified_episode_filename=os.path.join(qualified_season_folder_name,episode_file_name)
    if os.path.exists(qualified_series_folder_name):
        print("Series folder already exists - "+qualified_series_folder_name)
    else:
        print("Series folder does not exist, creating it")
        os.mkdir(qualified_series_folder_name)
    if os.path.exists(qualified_season_folder_name):
        print("Season folder already exists - "+qualified_season_folder_name)
    else:
        print("Season folder does not exist, creating it")
        os.mkdir(qualified_season_folder_name)
    print("TARGET FILE: "+ qualified_episode_filename)
    print("SOURCE FILE: "+ src_file)
    shutil.move(src_file,qualified_episode_filename)
    subprocess.Popen('touch \"'+qualified_series_folder_name+'\"', shell=True)
    subprocess.Popen('touch \"'+qualified_season_folder_name+'\"', shell=True)
    print("Complete!")


