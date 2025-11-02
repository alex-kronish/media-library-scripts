#!/tools/conda/envs/Plex/bin/python

import os
import re
import argparse
import datetime

if __name__=='__main__':
    log_file_name='/data/logs/music_video_sorter_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt'
    print(log_file_name)
    lf=open(log_file_name,'wt')
    real=False
    parser=argparse.ArgumentParser()
    parser.add_argument("--Real",required=False,action='store_true')
    args,leftovers=parser.parse_known_args()
    if args.Real:
        real=True
        pass
    lf.write("Real = "+str(real)+'\n')
    #real=False
    #exit()
    start_dir='/data/MusicVideos/'
    listing=os.listdir(start_dir)
    listing.remove('to_download.txt')
    listing.sort()
    listing_filtered=[]
    for f in listing:
        full_file_path=os.path.join(start_dir,f)
        if not os.path.isdir(full_file_path):
            lf.write(f+'\n')
            listing_filtered.append(f)
    listing_filtered.sort()
    extraction_regex=r'^([\&\'\-\w\d\!\ \.\,]+?)(\ [\–\-\"][ ]?)([\(\)\-\+\,\△\&\#\$\w\d! \.\"\'\＂\⧸]+)'
    listing_regexed=[]
    for x in listing_filtered:
        s=re.search(extraction_regex,x)
        try:
            #print(s)
            artist=s.group(1).strip().replace('＂','').replace('\"','')
            #print('Group 1 '+s.group(1).strip().replace('＂',''))
            song=s.group(3).strip().replace('＂','').replace('\"','').replace('⧸','-')
            if artist.endswith('.'):
                artist=artist[:-1]
            if song.endswith('.'):
                song=song[:-1]
            lf.write(artist+' | '+song +'\n' )
            existing_file=os.path.join(start_dir, x)
            new_dir=os.path.join(start_dir, artist, song)
            lf.write(new_dir+'\n')
            final_file=os.path.join(new_dir,x.replace('＂','').replace('\"',''))
            lf.write(existing_file+ ' --> '+final_file+'\n'+'\n')
            if real:
                os.makedirs(new_dir, exist_ok=True)
                os.rename(existing_file, final_file)
        except Exception as e:
            lf.write(x+" was not matched on the regex, skipping"+'\n')
            pass
    print("Done!")