```sh
/usr/bin/yt-dlp --downloader /usr/bin/ffmpeg --downloader-args "ffmpeg_i:-t 00:51:00 -seekable 0 -http_seekable 0" 'https://radiko.jp/#!/live/JOAK-FM' -o /home/tokiwa/Music/NHK/gendai_no_ongaku/$(date +\%Y-\%m-\%d)_gendai_no_ongaku.m4a
```

```clontab
10 8 * * 0 /usr/bin/yt-dlp --downloader /usr/bin/ffmpeg --downloader-args "ffmpeg_i:-t 00:51:00 -seekable 0 -http_seekable 0" 'https://radiko.jp/#!/live/JOAK-FM' -o /home/tokiwa/Music/NHK/gendai_no_ongaku/$(date +\%Y-\%m-\%d)_gendai_no_ongaku.m4a
```

