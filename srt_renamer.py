#!/tools/conda/envs/Plex/bin/python

import os
import re
import argparse
import json

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument("--SourceDir",required=True)
    args=parser.parse_args()
    source_dir=args.SourceDir
    directory_listing_unfiltered=os.listdir(source_dir)
    file_list_dict={}
    extn_regex_srt=r'\.srt$'
    extn_regex_vid=r'(\.mp4|\.mkv|\.avi)$'
    extn_regex=r'\.\w+$'
    episode_regex=r'S\d\dE\d\d'
    #step 1 is to build the video files...
    for v in directory_listing_unfiltered:
        full_file_name=os.path.join(source_dir, v)
        #print(full_file_name)
        episode_id_raw=re.search(episode_regex,v)
        if episode_id_raw:
            episode_id=episode_id_raw.group(0)
            srt_match=re.search(extn_regex_srt,v)
            vid_match=re.search(extn_regex_vid,v)
            if not file_list_dict.get(episode_id):
                file_list_dict[episode_id]={}
            if vid_match:
                file_list_dict[episode_id]['video_file']=full_file_name
        #print(str(episode_id))
        #print("")
    #step 2 is to find the subtitles and assign them to the video files, and check if they're already correct.
    for s in directory_listing_unfiltered:
        full_file_name=os.path.join(source_dir, s)
        #print(full_file_name)
        episode_id_raw=re.search(episode_regex,s)
        if episode_id_raw:
            episode_id=episode_id_raw.group(0)
            srt_match=re.search(extn_regex_srt,s)
            vid_match=re.search(extn_regex_vid,s)
            if not file_list_dict.get(episode_id):
                file_list_dict[episode_id]={}
            if srt_match:
                new_subs_file=re.sub(extn_regex, '.srt', file_list_dict[episode_id]['video_file'])
                file_list_dict[episode_id]['subtitle_file']=full_file_name
                file_list_dict[episode_id]['new_subtitle_file']=new_subs_file
                if new_subs_file==full_file_name:
                    file_list_dict[episode_id]['already_correct']=True
                else:
                    file_list_dict[episode_id]['already_correct']=False
        #print(str(episode_id))
        print("")
    file_list_dict=dict(sorted(file_list_dict.items()))
    #step 3 is to do it
    for x in file_list_dict.keys():
        if not file_list_dict[x].get('subtitle_file'):
            print("No subtitle file found for "+x)
        elif file_list_dict[x]['already_correct']==True:
            print("Subs are already correct for "+x)
        else:
            print("RENAME "+x)
            print(file_list_dict[x]['subtitle_file'] +'  -->  '+file_list_dict[x]['new_subtitle_file'])
            os.rename(file_list_dict[x]['subtitle_file'], file_list_dict[x]['new_subtitle_file'])
    #print(json.dumps(file_list_dict,indent=1))