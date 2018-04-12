from typing import List, NamedTuple, Optional

import aiohttp
from aiohttp import web

import mpd
import songinfo
from songinfo import Song

SongQueue = NamedTuple('SongQueue', [('user', str), ('songs', List[Song])])

class State:
    def __init__(self, app):
        self.current = None # type: Optional[Song]
        self.queues = [] # type: List[SongQueue]

        self.app = app

    async def append_queue(self, user: str, song: Song):
        if not self.queues:
            self.current = song
            streamurl = await songinfo.get_streamurl(song.url)
            await mpd.play_song(streamurl)
        else:
            try:
                q = next(q for q in self.queues if q.user == user)
            except StopIteration:
                q = SongQueue(user=user, songs=[])
                self.queues.append(q)


routes = web.RouteTableDef()

@routes.get('/ws')
async def websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # TODO: validate
    username = await ws.receive_str()
    async for msg in ws:
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue
        smsg = msg.data.split(maxsplit=1)
        if len(smsg) == 2 and smsg[0] == 'queue':
            # queue song
            url = smsg[1]

            s = await songinfo.get_songinfo(url)
            await request.app['state'].append_queue(username, s)
        elif len(smsg) == 2 and smsg[0] == 'remove':
            # remove from personal queue
            pass
        elif msg.data == 'skipme':
            pass
        elif msg.data == 'volup':
            pass
        elif msg.data == 'voldown':
            pass

async def app_factory():
    mpd_conn = mpd.MPDConnection()

    app = web.Application()
    app['connections'] = []
    app['state'] = State(app)
    app['mpd'] = mpd_conn

    app.add_routes(routes)
    return app

web.run_app(app_factoryapp())
