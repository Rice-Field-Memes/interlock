import interlock as il
from http.server import HTTPServer, BaseHTTPRequestHandler
from lib.InterlockMediaService import MediaService
import json
import random


interlock = il.Interlock('./lib/InterlockConfig.json', True)

rooms = interlock.get_rooms()
media_service = MediaService()


class Serv(BaseHTTPRequestHandler):

    def GetRoom(self, room):
        room_devices = self.GetDevices(room)
        room_scenes = self.GetScenes(room)
        this_room = {
            "id": room.room_name,
            "label": room.room_label,
            "image": room.room_image,
            "main": room.main,
            "on": room.lights_on(),
            "devices": room_devices,
            "scenes": room_scenes,
            "svg": room.svg
        }
        return this_room

    def GetScenes(self, room):
        room_scenes = []
        for scene in room.scenes:
            room_scenes.append({
                "id": scene.id,
                "label": scene.label,
                "room": scene.room.room_name
            })
        return room_scenes

    def GetDevice(self, device):
        if device.product_name == 'insight':
            state = {
                "on": device.get_state()
            }
        elif device.service == 'hue':
            state = {
                "on": device.get_state(),
                "reachable": device.reachable,
                "brightness": device.brightness,
                "hue": device.hue,
                "red": device.red,
                "green": device.green,
                "blue": device.blue
            }
        elif device.type == 'speakers':
            media = device.get_media()
            if media is not None:
                media_state = device.get_state()
                volume = device.volume()
                state = {
                    "playing": True if media_state == "PLAYING" else False,
                    "paused": True if media_state == "PAUSED" else False,
                    "track": {
                        "title": media.title,
                        "image": media.image,
                        "artist": media.artist,
                        "album": media.album
                    },
                    "volume": volume
                }
            else:
                state = {
                    "playing": False
                }
        else:
            state = None
        return {
                    "label": device.label,
                    "product_name": device.product_name,
                    "service": device.service,
                    "device_id": device.id,
                    "device_type": device.type,
                    "state": state
                }

    def GetDevices(self, room, OnlyLights=False):
        room_devices = []
        for device in room.devices:
            if not OnlyLights or device.is_light:
                device_obj = self.GetDevice(device)
                room_devices.append(device_obj)
        return room_devices

    def APIRequest(self):
        response = "unknown api request"
        code = 404
        url_parts = self.path.split("/")
        print(url_parts)
        if len(url_parts) > 2:
            if url_parts[2] == 'rooms':
                if len(url_parts) == 3:
                    rooms_return = []
                    for room in rooms:
                        this_room = self.GetRoom(room)
                        rooms_return.append(this_room)
                    response = {"rooms": rooms_return}
                elif len(url_parts) >= 4:
                    room_name = url_parts[3]
                    room = interlock.room(room_name)
                    if room:
                        if len(url_parts) == 4:
                            response = {"room": self.GetRoom(room)}
                        else:
                            if url_parts[4] == 'lights':
                                if len(url_parts) == 5:
                                    lights = self.GetDevices(room, True)
                                    response = {"lights": lights}
                                else:
                                    if url_parts[5] == "off":
                                        room.turn_off_lights()
                                        response = {"msg": "lights turned off"}
                                    elif url_parts[5] == "on":
                                        room.turn_on_lights()
                                        response = {"msg": "lights turned on"}
                                    elif 0 <= float(url_parts[5]) <= 1:
                                        room.set_brightness(float(url_parts[5]))
                                        response = {"msg": "brightness updated"}
                            if url_parts[4] == "off":
                                room.turn_off()
                                response = {"msg": "room turned off"}
                            if url_parts[4] == "on":
                                room.turn_on()
                                response = {"msg": "room turned on"}
                            if room.get_scene(url_parts[4]) is not None:
                                scene = room.get_scene(url_parts[4])
                                scene.run()
                            if url_parts[4] == "create_scene":
                                scene_name = url_parts[5]
                                scene = room.create_scene(scene_name)


                    else:
                        response = "unknown room"
            elif url_parts[2] == 'devices':
                if len(url_parts) == 3:
                    pass
                elif len(url_parts) >= 4:
                    device_name = url_parts[3]
                    device_name = device_name.replace('%20', ' ')
                    device = interlock.device(device_name)
                    if device:
                        if len(url_parts) > 4:
                            print(url_parts[4])
                            if url_parts[4] == "off":
                                if device.type == "rgb_light" or device.type == "switch":
                                    device.turn_off()
                                    response = {"msg": "turned off"}
                            elif url_parts[4] == "on":
                                if device.type == "rgb_light" or device.type == "switch":
                                    device.turn_on()
                                    response = {"msg": "turned on"}
                            elif url_parts[4] == "play":
                                if device.type == "speakers" or device.type == "display":
                                    if len(url_parts) > 6:
                                        service = None
                                        if url_parts[5] == 'google_play':
                                            service = interlock.play_music
                                            service_type = 'audio'
                                        if service is not None:
                                            if url_parts[6] == 'library':
                                                songs = service.get_library()
                                                media_list = service.create_track_objs(songs)
                                                random.shuffle(media_list)
                                                song = media_list[0]
                                                title = song.title
                                                artist = song.artist
                                                image = song.image
                                                media_service.set_output(device)
                                                media_service.start()
                                                media_service.play(media_list)
                                                url = song.get_url()
                                                # device.play_audio(url, title, image)
                                                response = {"song": {"title": title, "artist": artist, "image": image}}

                                        else:
                                            raise Exception('invalid music provider')
                                    else:
                                        media_service.play()
                                        response = {"msg": "device resumed"}
                            elif url_parts[4] == "pause":
                                if device.type == "speakers" or device.type == "display":
                                    media_service.pause()
                                    response = {"msg": "device paused"}
                            elif url_parts[4] == "stop":
                                if device.type == "speakers" or device.type == "display":
                                    media_service.stop()
                                    response = {"msg": "device stoped"}
                            elif url_parts[4] == "volume":
                                if device.type == "speakers" or device.type == "display":
                                    device.volume(url_parts[5])
                                    response = {"msg": "device volume updated"}
                            elif url_parts[4] == "mute":
                                if device.type == "speakers" or device.type == "display":
                                    device.volume(0)
                                    response = {"msg": "device muted"}
                            elif url_parts[4] == "next":
                                if device.type == "speakers" or device.type == "display":
                                    item = media_service.next()
                                    title = item.title
                                    artist = item.artist
                                    image = item.image
                                    response = {"song": {"title": title, "artist": artist, "image": image}}
                            elif url_parts[4] == "queue":
                                if device.type == "speakers" or device.type == "display":
                                    if len(url_parts) == 5:
                                        queue = media_service.get_queue()
                                        items = []
                                        for item in queue:
                                            items.append(item.jsonify())
                                        response = {"queue": items}
                                    else:
                                        if url_parts[5] == "shuffle":
                                            pass  # shuffle queue
                                        elif url_parts[5] == "clear":
                                            pass  # clear the queue
                                        elif url_parts[5] == "move":
                                            pass  # moves items in the queue
                        else:
                            device_obj = self.GetDevice(device)
                            response = device_obj
                    else:
                        response = "unknown device"
            elif url_parts[2] == "media":
                pass
        if response != "unknown api request":
            code = 200
        return response, code

    def do_GET(self):
        file_to_open = None
        if self.path == '/' or self.path == '' or self.path == '/home':
            self.path = '/index.html'
        elif self.path[0:4] == '/api':
            response, response_code = self.APIRequest()
            if type(response) is str:
                response = {"status": "error", "error_msg": response}
            else:
                status = {"interlock": {"status": "ok", "version": 2.0}}
                response = {**status, **response}
            file_to_open = json.dumps(response)
            self.send_response(response_code)
            self.send_header('Content-Type', 'application/json')
        else:
            try:
                print(self.path[1:])
                file_to_open = open(self.path[1:]).read()
                self.send_response(200)
            except Exception as e:
                print(e)
                file_to_open = 'File not found'
                self.send_response(404)
        self.end_headers()
        if file_to_open is not None:
            self.wfile.write(bytes(file_to_open, 'utf-8'))

if __name__ == '__main__':
    httpd = HTTPServer((interlock.server_ip, interlock.server_port), Serv)
    httpd.serve_forever()
