import asyncio

import mpd
from mpd.asyncio import MPDClient

async def wait_for_ok(reader):
    while True:
        data = await reader.readline()
        if data.startswith(b'OK'):
            return

class MPDConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.mpd = MPDClient()

        self._playlist_empty = asyncio.Event()
        self._adding_song = False

    async def start(self):
        await self.mpd.connect(self.host, self.port)
        asyncio.ensure_future(self._event_loop())

    async def wait_for_song(self):
        '''Returns when the playlist is empty'''
        await self._playlist_empty.wait()

    def is_ready(self):
        '''Immediately returns true if the playlist is empty, false otherwise.'''
        return self._playlist_empty.is_set()

    async def add_to_playlist(self, url):
        if self._adding_song:
            raise Exception

        self._adding_song = True
        self._playlist_empty.clear()
        print()
        print(url)
        print()
        try:
            await self.mpd.add(url)
            await self.mpd.play()
        except mpd.CommandError:
            pass
        self._adding_song = False

    async def skip(self):
        await self.mpd.clear()

    async def _event_loop(self):
        while True:
            status = await self.mpd.status()
            if status['playlistlength'] == '0':
                if not self._adding_song:
                    self._playlist_empty.set()
            else:
                self._playlist_empty.clear()

            async for subsystems in self.mpd.idle():
                if 'playlist' in subsystems or 'player' in subsystems:
                    break

async def play_song(song):
    print('playing song {}'.format(song))
