#!/tools/conda/envs/Plex/bin/python
import subprocess
import argparse
import datetime
import os
import re


def stdout_stderr_tuple_to_string(input_tuple):
    z=[]
    for x in input_tuple:
        if x is not None:
            y = x.decode('utf-8')
            for yl in y.split('\n'):
                z.append(yl)
    return z

def current_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def directory_listing(rootdir,logfile):
    rc_list=[]
    for path, subdirs, files in os.walk(rootdir):
        for name in files:
            f=os.path.join(path, name)
            logfile.write("Listing | "+ f+'\n')
            rc_list.append(f)
    return rc_list

if __name__=='__main__':
    logfile_timestamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    logfile_name='/data/logs/qbittorrent_split_rar_detection_'+logfile_timestamp+'.txt'
    logfile=open(logfile_name,'wt+')
    parser=argparse.ArgumentParser()
    parser.add_argument("--TorrentRootDir",required=True)
    args=parser.parse_args()
    working_dir = args.TorrentRootDir
    files=directory_listing(working_dir,logfile)
    files.sort()
    extn_regex_r00=r'\.[Rr]\d+$'
    split_rar_count=0
    rar_file_present=0
    rar_file=[]
    for f in files:
        r00_search=re.search(extn_regex_r00, f)
        if f.lower().endswith('.part01.rar') and 'sample' not in f.lower():
            rar_file_present=rar_file_present+1
            logfile.write("Deteced a part01.rar : "+f+'\n')
            rar_file.append(f)
        elif f.lower().endswith('.rar') and 'sample' not in f.lower():
            rar_file_present=rar_file_present+1
            rar_file.append(f)
            logfile.write('detected .rar file: '+f+'\n')
        elif r00_search is not None and not 'sample' in f.lower():
            split_rar_count=split_rar_count+1
            logfile.write('detected split rar file .r## : '+f +'\n')
    if rar_file_present==0:
        logfile.write("Rar file not detected. Exiting."+'\n')
        logfile.close()
        exit(0)
    else:
        logfile.write("Found a rar. Using rar extraction."+'\n')
        for r in rar_file:
            logfile.write("Extraction start: "+current_timestamp() +' | '+r+'\n')
            command=['/usr/bin/unrar', 'x', '-o+', '-e', r]
            subproc_tuple=subprocess.Popen(command,shell=False,cwd=working_dir,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
            subproc_lines=stdout_stderr_tuple_to_string(subproc_tuple)
            for line in subproc_lines:
                logfile.write('* ' +current_timestamp() +' *  '+line+'\n')
            logfile.write("Extraction complete: "+current_timestamp() +' | '+r+'\n')
    logfile.close()
    print("done")