#!/bin/bash

env > /data/encode/radarr_environment_variables.txt

if [ "${radarr_eventtype}" = "Test" ]; then
	echo "This is a test"
	exit 0
fi
sourcefile=${radarr_moviefile_path}
filename=$(basename -a "${radarr_moviefile_path}")
outfile="/data/encode/output/${filename}"
targetfile="/data/Movies/${filename}"
unproc="/data/Unsorted/preprocess_backups/${filename}"
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
	if (( original_filesize > new_filesize )); then
		mv "${sourcefile}" "${unproc}"
		mv "${outfile}" "${targetfile}"
	else
		mv "${outfile}"  "/data/Unsorted/preprocess_backups/ffmpeg-not-smaller.${filename}"
		mv "${sourcefile}" "${targetfile}"
	fi
	#unmonitor
	/data/encode/radarr_unmonitor.py --MovieID ${radarr_movie_id}
	if [ $? -ne 0 ]; then
		mv_string="$radarr_movie_title | Year $radarr_movie_year | Radarr Movie ID ${radarr_movie_id}"
		/tools/bots/flamedramon_notify/flamedramon.py --Message "Something has gone wrong unmonitoring the Movie:\n $mv_string"
	fi
else
	/tools/bots/flamedramon_notify/flamedramon.py --Message "ffmpeg was not able to encode $filename successfully and will need manual intervention."
fi

