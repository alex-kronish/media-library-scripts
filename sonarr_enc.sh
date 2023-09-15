#!/bin/bash

env > /data/encode/sonarr_environment_variables.txt

if [ "${sonarr_eventtype}" = "Test" ]; then
	echo "This is a test"
	exit 0
fi
sourcefile=${sonarr_episodefile_path}
sourcefile_target=${sourcefile}
filename=$(basename -a "${sonarr_episodefile_path}")
original_filename=$filename
avi_flag=0
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



#ffmpeg -i "${sourcefile}" -c:v h264 -c:a ac3 -c:s copy -y  -map 0:a -map 0:v -map 0:s?  -preset slower -crf 22 -hide_banner -loglevel error  -max_muxing_queue_size 1024  "$outfile"

#turns out it's way faster if you use the GPU! who would have thought?
ffmpeg -hwaccel cuda -i "${sourcefile}" -c:v h264_nvenc -c:a ac3 -c:s copy -y  -map 0:a -map 0:v -map 0:s?  -preset slow -cq:v 30 -rc:v vbr -qmin 0 -b:v 0  -hide_banner -loglevel error  -max_muxing_queue_size 1024  "$outfile"

ffmpgstatus=$?

if [ $ffmpgstatus -eq 0 ]; then
	original_filesize=$(stat -c%s "$sourcefile")
	new_filesize=$(stat -c%s "$outfile")
	if [ $avi_flag -eq 1 ]; then  
		#avi is basically a dead format at this point, let's force it to use the new one.
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
	if [ $? -neq 0 ]; then
		episode_string="$sonarr_series_title | Season $sonarr_episodefile_seasonnumber | Episode $sonarr_episodefile_episodenumbers | Title $sonarr_episodefile_episodetitles | SonarrEpisodeID ${sonarr_episodefile_episodeids}"
		/tools/bots/flamedramon_notify/flamedramon.py --Message "Something has gone wrong unmonitoring the TV Show Episode:\n $episode_string"
	fi
else
	/tools/bots/flamedramon_notify/flamedramon.py --Message "ffmpeg was not able to encode $filename successfully and will need manual intervention."
	dttm=$(date +%Y%m%d_%H%M%S)
	error_target="/data/Unsorted/preprocess_backups/ffmpeg-error.${dttm}.${filename}"
	mv ${sourcefile}  ${error_target}
fi


