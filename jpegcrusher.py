#!/tools/conda/bin/python
import subprocess
import logging
import argparse
import os
import re
import datetime
# -- argparser and setup
parser=argparse.ArgumentParser()
parser.add_argument("--Filename", required=True)
args=parser.parse_args()
filename=args.Filename
extn_regex=r'\.\w+$'
if not filename.startswith('/'):
    fully_qualified_source_file=os.path.join(os.getcwd(),filename)
else:
    fully_qualified_source_file=filename
if not os.path.isfile(fully_qualified_source_file):
    print(fully_qualified_source_file+" is not a file")
    exit(99)
print(fully_qualified_source_file)
file_extension=re.search(extn_regex,filename).group(0)
amt_to_truncate=-1*len(file_extension)
target_filename=os.path.basename(filename)[:amt_to_truncate]+'.jpegcrusher.'+datetime.datetime.now().strftime("%Y%m%d.%H%M%S")+file_extension
fully_qualified_target_file=os.path.join(os.getcwd(),target_filename)
print(fully_qualified_target_file)
#command=['/usr/bin/ffmpeg', '-i', fully_qualified_source_file, '-vf', 'format=yuv420p',  '-metadata', 'title=',  '-c:v', 'h264_nvenc', '-c:a', 'ac3', '-y', '-map', '0:a', '-map','0:v', '-preset','slow', '-cq:v','30', '-rc:v','vbr', '-qmin', '0', '-b:v','0', '-max_muxing_queue_size', '1024', '-ss', start, '-to', end, fully_qualified_target_file]
command=['/usr/bin/ffmpeg', '-i', fully_qualified_source_file, '-compression_level', '90', fully_qualified_target_file]
print("Original : "+fully_qualified_source_file)
print("New      : "+fully_qualified_target_file)
print(command)
proc=subprocess.Popen(command,shell=False,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=1,universal_newlines=True)
#proc_c=proc.communicate()
while (exit_code:=proc.poll()) is None:
    if proc.stdout:
        ffmpeg_line=proc.stdout.readline()#.decode('utf-8')
        if ffmpeg_line.strip() != '':
            print(str(ffmpeg_line).strip())
    if proc.stderr:
        ffmpeg_line_stderr=proc.stderr.readline()#.decode('utf-8')
        if ffmpeg_line_stderr.strip() !='':
            print(str(ffmpeg_line_stderr).strip())
exit_code=proc.returncode
print("-----------------------------------------------------------------------------")
print("ffmpeg exited with status code : "+str(exit_code))
new_sz=os.path.getsize(fully_qualified_target_file)
print("New filesize: "+str(new_sz))
