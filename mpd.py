import asyncio
from enum import Enum

class MPDInterrupt(Enum):
    PLAYER = auto()
    PLAYLIST = auto()

INTERRUPTS = {
    b'player': MPDInterrupt.PLAYER,
    b'playlist': MPDInterrupt.PLAYLIST,
}

async def wait_for_ok(reader):
    while True:
        data = await reader.readline()
        if data.startswith(b'OK'):
            return

class MPDConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        # Semaphore is incremented when we are ready to play a song
        self._want_song = asyncio.Event()

        self._is_idle = asyncio.Semaphore(0)

    async def wait_for_song(self):
        '''Returns when the playlist is empty'''
        await self._want_song.wait()

    async def play_song(self, url):
        if not self._want_song.is_set():
            raise Exception

        yield from self._is_idle.acquire()

        '''
        with (yield from self._mutate_playlist):
            r, w = await asyncio.open_connection(self.host, self.port)
            wait_for_ok(r)
            w.write(b'add ' + url.encode() + b'\n')
            wait_for_ok(r)
            w.write(b'play\n')
            wait_for_ok(r)
        '''

    async def _get_status(self):
        writer.write(b'status\n')
        while True:
            data = self.reader.readline()
            sdata = data.strip().split(b' ', 1)
            if len(sdata) == 2 and sdata[0] == b'playlistlength':
                if sdata[1] == b'0':
                    self._want_song.set()
                else:
                    self._want_song.clear()
                break

        await wait_for_ok(self.reader)

    async def _idle(self):
        writer.write(b'idle\n')
        self._is_idle.release()
        interrupts = set()
        errors = []
        while True:
            data = await self.reader.readline()
            sdata = data.strip().split(b' ', 1)
            if len(sdata) == 2 and sdata[0] == b'changed:':
                if sdata[1] in INTERRUPTS:
                    interrupts.add(INTERRUPTS[sdata[1]])
            elif data.startswith(b'error:'):
                errors.append(data)
            elif data.startswith(b'OK'):
                break

            if self._is_idle.locked():
                self._is_idle.acquire()

        if self._is_idle.locked():
            self._is_idle.acquire()

    async def _event_loop(self):
        while True:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            data = await self.reader.readline()
            if not data.startswith(b'OK'):
                raise Exception
            while True:
                await self._get_status()
                interrupts, errors = await self._idle()
                if errors:
                    self.writer.write(b'clearerror\n')
                    wait_for_ok(self.reader)
                    self.writer.write(b'clear\n')
                    wait_for_ok(self.reader)

    async def start(self):
        asyncio.ensure_future(self._event_loop())

async def play_song(song):
    print('playing song {}'.format(song))
