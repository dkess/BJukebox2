import asyncio
import json
from typing import List, NamedTuple, Optional

import aiohttp
from aiohttp import web

import bjb_mpd as mpd
import songinfo
from songinfo import Song

SongQueue = NamedTuple('SongQueue', [('user', str), ('songs', List[Song])])

class State:
    def __init__(self, app, backend):
        self.current = None # type: Optional[Song]
        self.queues = [] # type: List[SongQueue]

        self.app = app
        self.backend = backend

        self._cond = asyncio.Condition()

    def asNestedDict(self):
        '''Turns the state into data suitable for JSON encoding'''
        qs = [q._asdict() for q in self.queues]
        for q in qs:
            q['songs'] = [s._asdict() for s in q['songs']]

        return {
            'current': self.current._asdict() if self.current else "noone",
            'queues': qs
        }

    async def _event_loop(self):
        with (await self._cond):
            while await self._cond.wait():
                if self.current == None and self.queues:
                    # Pop from the queue
                    self.current = self.queues[0].songs.pop(0)

                    oldqueue = self.queues.pop(0)
                    if oldqueue.songs:
                        self.queues.append(oldqueue)

                    asyncio.ensure_future(self._play_current())

                # send new state to clients
                j = json.dumps(self.asNestedDict())
                for writer in self.app['connections']:
                    await writer(j)

    async def _play_current(self):
        streamurl = await songinfo.get_streamurl(self.current.url)
        await self.backend.add_to_playlist(streamurl)
        await asyncio.sleep(1)
        await self.backend.wait_for_song()

        with (await self._cond):
            self.current = None
            self._cond.notify_all()

    def start_event_loop(self):
        asyncio.ensure_future(self._event_loop())

    async def append_queue(self, user: str, song: Song):
        with (await self._cond):
            try:
                q = next(q for q in self.queues if q.user == user)
            except StopIteration:
                q = SongQueue(user=user, songs=[])
                self.queues.append(q)

            q.songs.append(song)
            print(self.asNestedDict())
            self._cond.notify_all()

    async def remove_song(self, user: str, index: int):
        with (await self._cond):
            try:
                q = next(q for q in self.queues if q.user == user)
                q.pop(index)
                self._cond.notify_all()
            except StopIteration:
                pass
            except IndexError:
                pass

routes = web.RouteTableDef()

@routes.get('/ws')
async def websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # TODO: validate
    username = await ws.receive_str()
    await ws.send_str('ok')
    request.app['connections'].append(ws.send_str)
    async for msg in ws:
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue
        smsg = msg.data.split(maxsplit=1)
        if len(smsg) == 2 and smsg[0] == 'queue':
            # queue song
            url = smsg[1]

            try:
                s = await songinfo.get_songinfo(url)
            except:
                await ws.send_str('error')
            else:
                await ws.send_str('ok')
                await request.app['state'].append_queue(username, s)
        elif len(smsg) == 2 and smsg[0] == 'remove':
            try:
                await request.app['state'].remove_song(username, int(smsg[1]))
            except ValueError:
                pass
        elif msg.data == 'skipme':
            await request.app['state'].skip()
        elif msg.data == 'volup':
            pass
        elif msg.data == 'voldown':
            pass

    request.app['connections'].remove(ws.send_str)
    return ws

async def app_factory():
    mpd_conn = mpd.MPDConnection('localhost', 6600)
    await mpd_conn.start()

    app = web.Application()
    app['connections'] = []

    app['state'] = State(app, mpd_conn)
    app['state'].start_event_loop()

    app['mpd'] = mpd_conn

    app.add_routes(routes)
    return app

if __name__ == '__main__':
    web.run_app(app_factory())
