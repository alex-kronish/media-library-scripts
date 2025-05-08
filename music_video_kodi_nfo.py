#!/tools/conda/envs/Plex/bin/python
import os
import re
import argparse
import subprocess
import json
import datetime


def video_duration(file_name):
    minfo_cmd=["/usr/bin/mediainfo","--output=JSON",file_name]
    sproc=subprocess.Popen(minfo_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sproc_c=sproc.communicate()
    stdout,stderr = sproc_c
    minfo=json.loads(stdout)
    duration_in_secs=None
    duration_readable='None'
    mediatracks=minfo['media']['track']
    for track in mediatracks:
        if track.get('@type')=='Video':
            duration_in_secs=float(track.get("Duration"))
            if duration_in_secs:
                duration_readable=str(datetime.timedelta(seconds=duration_in_secs)).replace('.',',')
                duration_readable_len=len(duration_readable)
                try:
                    duration_readable_comma=duration_readable.index(',')
                except Exception as e:
                    duration_readable=duration_readable+',000000'
                    duration_readable_comma=duration_readable.index(',')
                duration_subseconds_unfixed=duration_readable[duration_readable_comma+1:duration_readable_len]
                duration_subseconds_fixed=duration_subseconds_unfixed[:3]
                #print(duration_subseconds_fixed)
                duration_new=duration_readable[0:duration_readable_comma]+','+duration_subseconds_fixed
                #print(duration_new)
            else:
                duration_readable='None'
    return duration_in_secs, duration_new

if __name__=='__main__':
    source_dir='/data/MusicVideos/'
    all_vids=[]
    artist_listing=os.listdir(source_dir)
    for artist in artist_listing:
        artist_dir=os.path.join(source_dir, artist)
        if os.path.isdir(artist_dir):
            songs=os.listdir(artist_dir)
            #print(artist_dir)
            #print(songs)
            for s in songs:
                song_dir=os.path.join(artist_dir, s)
                #print(song_dir)
                song_videos=os.listdir(song_dir)
                for f in song_videos:
                    video_file_path=os.path.join(song_dir, f)
                    if not f.endswith('.nfo'):
                        print(video_file_path)
                        metadata=video_file_path.split('/')
                        #print(metadata)
                        metadata.remove('')
                        metadata.remove('data')
                        metadata.remove('MusicVideos')
                        #duration_secs, duration_readable=video_duration(video_file_path)
                        extn_regex=r'\.\w+$'
                        video_extension=re.search(extn_regex, f).group(0)
                        srt_file=f.replace(video_extension, '.nfo')
                        row={"artist":metadata[0], "song":metadata[1], "fullly_qualified_filename":video_file_path, "file_name":metadata[2], "file_dir":song_dir,
                             "duration_in_seconds":None, "duration_readable":None, "srt_file_name":srt_file, "fully_qualified_srt_filename":os.path.join(song_dir, srt_file)}
                        all_vids.append(row)
    for data_row in all_vids:
        lines=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>','<musicvideo>','<artist>'+data_row['artist']+'</artist>','<title>'+data_row['song']+'</title>','</musicvideo>']
        subtitle_content='\n'.join(lines)+'\n'
        subtitle_already_exists=os.path.exists(data_row['fully_qualified_srt_filename'])
        if not subtitle_already_exists:
            srt=open(data_row['fully_qualified_srt_filename'],'wt')
            srt.write(subtitle_content)
            srt.close()
            print('Wrote subtitle file - '+data_row['fully_qualified_srt_filename'])
        else:
            print("Already exists, taking no action - "+ data_row['fully_qualified_srt_filename'])
        
