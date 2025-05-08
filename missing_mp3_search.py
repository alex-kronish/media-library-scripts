#!/tools/conda/envs/Plex/bin/python

import os
import re
import datetime
import json
import eyed3
import logging
import io


if __name__=="__main__":
    log_stream = io.StringIO()
    logging.basicConfig(stream=log_stream, level=logging.INFO)
    output_filename='/data/logs/missing_mp3_search_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt'
    print(output_filename)
    output=open(output_filename,'wt')
    start='/data/Music'
    listing=[]
    eyed3_err=[]
    mismatches=[]
    for path, directories, files in os.walk(start):
        files.sort()
        listing.append({"directory":path, "file_array":files})
    for l in listing:
        mp3_files=0
        max_track_number=0
        for f in l['file_array']:
            if f.endswith('.mp3'):
                this_file=os.path.join(l['directory'], f)
                mp3_files=mp3_files+1
                mp3_tags=eyed3.load(this_file)
                llog=log_stream.getvalue()
                if llog:
                    eyed3_err.append(llog.replace('\00','')+'\n')
                    eyed3_err.append("Eyed3 threw a warning for "+this_file+'\n\n')
                    log_stream.truncate(0)
                    eyed3_err.append('--------------------------------------------------------------------------------\n\n')
                this_track_number=mp3_tags.tag.track_num[0]
                #print(str(mp3_tags))
                if this_track_number is not None:
                    if int(this_track_number)>=max_track_number:
                        max_track_number=int(this_track_number)
        if max_track_number != mp3_files:
            mismatches.append("You're gonna wanna check this one out, I found "+str(mp3_files) +" files but the max track number detected was "+ str(max_track_number)+'\n')
            mismatches.append(l['directory']+'\n\n')
    output.write("File/Tag Mismatches: \n")
    for x in mismatches:
        output.write(x)
    output.write("\n\nEyeD3 errors:\n")
    for e in eyed3_err:
        output.write(e)
    output.close()