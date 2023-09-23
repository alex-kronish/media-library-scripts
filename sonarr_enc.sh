#!/bin/bash

env > /data/encode/sonarr_environment_variables.txt

if [ "${sonarr_eventtype}" = "Test" ]; then
	echo "This is a test"
	#exit 0
	sonarr_episodefile_path="/data/Unsorted/preprocess_backups/test_file/Hypothetical - S01E03 - Episode 3.mkv"
fi
sourcefile=${sonarr_episodefile_path}
touch "$sourcefile"
sourcefile_target=${sourcefile}
filename=$(basename -a "${sonarr_episodefile_path}")
original_filename=$filename
avi_flag=0
dttm=$(date +%Y%m%d_%H%M%S)
if [[ $filename == *.avi ]]; then
        temp_no_extension=${filename:0:-4}
	new_filename="${temp_no_extension}.mp4"
	filename=$new_filename
	avi_flag=1
	sourcefile_target="${sourcefile:0:-4}.mp4"
fi

outfile="/data/encode/output/${filename}"
unproc="/data/Unsorted/preprocess_backups/${original_filename}"
echo $sourcefile
echo $filename
echo $outfile


clamscan "${sourcefile}"

virus=$?

if [ $virus -ne 0 ]; then
        /tools/bots/flamedramon_notify/flamedramon.py --Message "VIRUS SCAN ISSUE:  ${sourcefile}"
        exit 99
fi

#check for interlacing
/tools/scripts/check_for_interlacing.py --SourceFile "${sourcefile}"
interlaced_flag=$?
if [ $interlaced_flag -eq 1 ]; then
	filter="-filter:v yadif"
else
	filter=""
fi
ffmpeg_command_file="/data/Unsorted/preprocess_backups/ffmpeg.shell.command.${dttm}.${filename}.txt"
ffmpeg_output_file="/data/Unsorted/preprocess_backups/ffmpeg.shell.output.${dttm}.${filename}.txt"
#ffmpeg -i "${sourcefile}" -c:v h264 -c:a ac3 -c:s copy -y  -map 0:a -map 0:v -map 0:s?  -preset slower -crf 22 -hide_banner -loglevel error  -max_muxing_queue_size 1024  "$outfile"
ffmpeg_command="ffmpeg -hwaccel cuda -i \"${sourcefile}\" -c:v h264_nvenc $filter -c:a ac3 -c:s copy -y  -map 0:a -map 0:v -map 0:s?  -preset slow -cq:v 30 -rc:v vbr -qmin 0 -b:v 0 -max_muxing_queue_size 1024  \"$outfile\"   > \"${ffmpeg_output_file}\" 2>&1"
#turns out it's way faster if you use the GPU! who would have thought?
echo ${ffmpeg_command} > "${ffmpeg_command_file}"
#ffmpeg -hwaccel cuda -i "${sourcefile}" -c:v h264_nvenc $filter -c:a ac3 -c:s copy -y  -map 0:a -map 0:v -map 0:s?  -preset slow -cq:v 30 -rc:v vbr -qmin 0 -b:v 0  -hide_banner -loglevel error  -max_muxing_queue_size 1024  "$outfile"
eval "${ffmpeg_command}"
ffmpgstatus=$?

if [ $ffmpgstatus -eq 0 ]; then
	original_filesize=$(stat -c%s "$sourcefile")
	new_filesize=$(stat -c%s "$outfile")
	if [ $avi_flag -eq 1 ]; then  
		#avi is basically a dead format at this point, let's force it to use the new one.
		new_filesize=1
	elif [ $interlaced_flag -eq 1 ]; then  #try and avoid keeping interlaced versions
		new_filesize=1
	fi
	if (( original_filesize > new_filesize )); then
		mv "${sourcefile}" "${unproc}"
		mv "${outfile}" "${sourcefile_target}"
		#this part is confusing, so $outfile is now located at $sourcefile, so while i'm giving it the sourcefile variable, it's moving the newly encoded file.
		/data/encode/sonarr_move_to_plex.py --SourceFile "${sourcefile_target}"
	else
		#if the orginal file is smaller there's no reason to use the new one.
		mv "${outfile}" "/data/Unsorted/preprocess_backups/ffmpeg-not-smaller.${filename}"
		/data/encode/sonarr_move_to_plex.py --SourceFile "${sourcefile_target}"
	fi
	#unmonitor
	/data/encode/sonarr_unmonitor.py --EpisodeID ${sonarr_episodefile_episodeids}
	if [ $? -ne 0 ]; then
		episode_string="$sonarr_series_title 
		Season $sonarr_episodefile_seasonnumber 
		Episode $sonarr_episodefile_episodenumbers 
		Title $sonarr_episodefile_episodetitles 
		SonarrEpisodeID ${sonarr_episodefile_episodeids}"
		/tools/bots/flamedramon_notify/flamedramon.py --Message "Something has gone wrong unmonitoring the TV Show Episode: $episode_string"
	fi
else
	/tools/bots/flamedramon_notify/flamedramon.py --Message "ffmpeg was not able to encode $filename successfully and will need manual intervention."
	error_target="/data/Unsorted/preprocess_backups/ffmpeg-error.${dttm}.${filename}"
	mv "${sourcefile}"  "${error_target}"
fi


