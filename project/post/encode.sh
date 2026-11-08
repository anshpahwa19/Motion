#!/bin/bash
# Encode final picture sequence + mix -> MP4 (H.264 High, 24 fps, AAC 48 kHz).
# usage: encode.sh <frames_dir> <mix.wav> <out.mp4>
set -e
FR=$1; MIX=$2; OUT=$3
ffmpeg -y -hide_banner -loglevel error -framerate 24 -i "$FR/f%05d.png" -i "$MIX" \
  -vf "hqdn3d=0.8:0.8:3.5:3.5,noise=alls=7:allf=t+u,format=yuv420p" \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:v libx264 -preset slow -crf 20 -profile:v high -tune film -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest "$OUT"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact "$OUT"
