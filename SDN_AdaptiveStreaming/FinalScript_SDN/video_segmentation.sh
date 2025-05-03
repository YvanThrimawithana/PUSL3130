#!/bin/bash

sudo apt update

sudo apt install gpac-tools ffmpeg

ffmpeg -i bbb.mp4 \
-map v:0 -map a:0 -map v:0 -map a:0 -map v:0 -map a:0 -map v:0 -map a:0 \
-c:v libx264 -c:a aac \
-b:v:0 400k -s:0 426x240 -profile:v:0 baseline -bf 1 -g 48 -keyint_min 48 \
-b:v:1 800k -s:1 640x360 -profile:v:1 baseline -bf 1 -g 48 -keyint_min 48 \
-b:v:2 1500k -s:2 854x480 -profile:v:2 main -bf 1 -g 48 -keyint_min 48 \
-b:v:3 3000k -s:3 1280x720 -profile:v:3 main -bf 1 -g 48 -keyint_min 48 \
-b:a 128k \
-f dash -seg_duration 10 -use_template 1 -use_timeline 1 \
-init_seg_name "init-\$RepresentationID\$.m4s" \
-media_seg_name "chunk-\$RepresentationID\$-\$Number\$.m4s" \
-adaptation_sets "id=0,streams=v id=1,streams=a" \
dash_output/stream.mpd
