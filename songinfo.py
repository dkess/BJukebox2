import asyncio
from typing import NamedTuple, Optional

import youtube_dl

Song = NamedTuple('Song', [('title', str), ('thumbnail_url', Optional[str]), ('url', str)])

ydl_args = {"noplaylist": True,
            "simulate": True, # don't actually download songs
            "default_search": "ytsearch1", # fallback to youtube search
            "quiet": True, # don't spam stdout
           }

def get_songinfo_block(url: str) -> Song:
    ydl = youtube_dl.YoutubeDL(ydl_args)

    dl = ydl.extract_info(url)

    # extract first search result
    if "entries" in dl:
        dl = dl["entries"][0]

    return Song(
            title=dl['title'],
            thumbnail_url=dl.get('thumbnail'),
            url=dl.get('webpage_url', url))

async def get_songinfo(url: str) -> Song:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_songinfo_block, url)

async def get_streamurl(url: str) -> str:
    # Call the youtube-dl binary, because getting all these options to work
    # is annoying with the library.
    create = asyncio.create_subprocess_exec(
            'youtube-dl',
            '-f', '140/http_mp3_128_url/bestaudio',
            '--get-url',
            '--no-playlist',
            '--',
            url,
            stdout=asyncio.subprocess.PIPE)

    proc = await create
    line = await proc.stdout.readline()
    proc.kill()
    return line.decode().strip()
