#!/bin/bash
# Streamlink playlist - Run: bash streamlink_playlist.sh

echo "Playing AriseNewsChannel..."
streamlink --player vlc "https://www.youtube.com/@AriseNewsChannel/live" best &
sleep 2
echo "Playing TVCNewsNigeria..."
streamlink --player vlc "https://www.youtube.com/@TVCNewsNigeria/live" best &
sleep 2
echo "Playing NewsCentralAfrica..."
streamlink --player vlc "https://www.youtube.com/@NewsCentralAfrica/live" best &
sleep 2
echo "Playing NTALive..."
streamlink --player vlc "https://www.youtube.com/@NTALive/live" best &
sleep 2
echo "Playing SilverbirdN24Live..."
streamlink --player vlc "https://www.youtube.com/@SilverbirdN24Live/live" best &
sleep 2
echo "Playing AITLivestream1..."
streamlink --player vlc "https://www.youtube.com/@AITLivestream1/live" best &
sleep 2
echo "Playing VOP903FM..."
streamlink --player vlc "https://www.youtube.com/@VOP903FM/live" best &
sleep 2
wait
