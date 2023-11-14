from multiprocessing.connection import Connection, Listener,Client
import time
from random import random
from threading import Thread,Event
from multiprocessing import shared_memory
import struct
import array
import bpy
import numpy as np
from .image_manager import ImageManager
from .ui import BlenderKritaLinkPanel
import json

class KritaConnection():
    PORT = 6000
    LINK_INSTANCE = None
    STATUS: str
    
    def __init__(self) -> None:
        if KritaConnection.LINK_INSTANCE: return
        KritaConnection.LINK_INSTANCE = self

    def __del__(self):
        if self.CONNECTION:
            self.CONNECTION.send("close")
            self.CONNECTION.close()
    
    def start(self):
        self.__STOP_SIGNAL = Event()
        self.__THREAD = Thread(target=self.krita_listener)
        self.__THREAD.start()
        self.CONNECTION: None|Connection = None
        KritaConnection.STATUS = 'listening'
        
    def update_message(self,message):
        if hasattr(bpy.context,'scene') and hasattr(bpy.context.scene,'test_prop') and bpy.context.scene.test_prop:
            bpy.context.scene.test_prop = message
        else: print("no scene??")
        
    def krita_listener(self):
        """chuj"""
        while not self.__STOP_SIGNAL.isSet():
            KritaConnection.LINK_INSTANCE = self
            address = ('localhost', KritaConnection.PORT)     # family is deduced to be 'AF_INET'
            self.update_message("listening")
            listener = Listener(address, authkey=b'2137')
            conn = listener.accept()
            self.update_message("connected")
            KritaConnection.CONNECTION = conn
            print("connection accepted")
            existing_shm = shared_memory.SharedMemory(name='krita-blender')
            try:
                while True:
                    print("listening for message")
                    self.update_message("connected")
                    msg = conn.recv()
                    self.update_message("message recived")
                    print(msg)
                    if msg == 'close':
                        print(msg)
                        conn.close()
                        self.update_message("closed")
                        break
                    elif msg == 'refresh':
                        t = time.time()
                        print("refresh initiated")
                        self.update_message("got The Image")
                        fp32_array = np.frombuffer(existing_shm.buf, dtype=np.float32)
                        print("refresh initiated")
                        ImageManager.INSTANCE.mirror_image(fp32_array)
                        fp32_array = None
                        print("refresh complete")
                        self.update_message("connected")
                    elif isinstance(msg,object):
                        print("message is object UwU")
                        if "type" in msg and msg["type"] == "GET_IMAGES":
                            data = []
                            for image in bpy.data.images:
                                data.append({
                                    "name": image.name,
                                    "path": bpy.path.abspath(image.filepath),
                                    "size":[image.size[0],image.size[1]]
                                })
                            print(msg)
                            conn.send({
                                "type":"IMAGES_DATA",
                                "data":data,
                            })
                
                existing_shm.close()
                conn.close()
            except Exception as e:
                print("error happened", e)
                if self.CONNECTION != None:
                    self.CONNECTION.send("close")
                    self.CONNECTION.close()
                self.CONNECTION = None
            # existing_shm.close()
            listener.close()
            if self.__STOP_SIGNAL.is_set():
                KritaConnection.STATUS = "listening"
                self.redraw_uis()            
                return