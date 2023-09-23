#!/tools/conda/envs/Plex/bin/python

import subprocess
import argparse
import os

def stdout_stderr_tuple_to_string(input_tuple):
    z=[]
    for x in input_tuple:
        z.append(x.decode('utf-8'))
    y=''.join(z)
    return y

def detect(qualified_path_to_file):
    command="mediainfo --Inform='Video;%ScanType%,%ScanOrder%,%ScanType_StoreMethod%' \""+qualified_path_to_file+"\""
    cmd=subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    output=stdout_stderr_tuple_to_string(cmd)
    interlacing_strings=['Interleaved','Interlaced','MBAFF']
    interlaced_flag=False
    if not os.path.isfile(qualified_path_to_file):
        print(qualified_path_to_file +" : Not a video file")
        return 99
    for x in interlacing_strings:
        if x.lower() in output.lower():
            interlaced_flag=True
    if interlaced_flag:
        print(qualified_path_to_file +" : Interlaced")
        return 1
    else:
        if file_name != 'all':  #suppress output if it's progressive & we're checking the whole library
            print(qualified_path_to_file + " : Progressive")
        return 0
        


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument("--SourceFile",required=True)
    args=parser.parse_args()
    file_name=args.SourceFile
    if file_name=='all':
        files=[]
        tv_dir='/data/TV Shows/'
        structure=os.walk(tv_dir)
        for root, directories, filenames in structure:
            for s in filenames:
                video_file=os.path.join(root,s)
                if s.endswith(('.avi','.mkv','.mp4')):
                    files.append(video_file)
    else:
        files=[file_name]
    #print(str(files))
    files.sort()
    for f in files:
        rc=detect(f)
    exit(rc)
    
