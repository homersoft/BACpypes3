# -*- coding: utf-8 -*-

"""
Json Controlled Server 3

Sample BACnetIP application with a structure of the server defined from the JSON file.
"""

import asyncio
import requests
import json

from bacpypes3.debugging import ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.ipv4.app import Application

from bacpypes3.object import DeviceObjectReference

from bacpypes3.local.object import Object as _Object
from bacpypes3.object import BinaryInputObject as _BinaryInputObject
from bacpypes3.object import AnalogInputObject as _AnalogInputObject
from bacpypes3.object import StructuredViewObject as _StructuredViewObject
from bacpypes3.local.device import DeviceObject as _DeviceObject
from bacpypes3.local.networkport import NetworkPortObject as _NetworkPortObject
from bacpypes3.local.cov import COVIncrementCriteria
from bacpypes3.local.cov import GenericCriteria


from bacpypes3.basetypes import Polarity
from bacpypes3.basetypes import EventState
from bacpypes3.basetypes import NodeType

from bacpypes3.constructeddata import ArrayOf
from bacpypes3.vendor import VendorInfo

BI_SHIFT = (3 << 22)
AI_SHIFT = (0 << 22)
SV_SHIFT = (29 << 22)

# some debugging
_debug = 0
_log = ModuleLogger(globals())

_vendor_id = 888

custom_vendor_info = VendorInfo(_vendor_id)

class DeviceObject(_DeviceObject):
    vendorIdentifier = _vendor_id

class NetworkPortObject(_NetworkPortObject):
    pass

class BinaryInputObject(_Object, _BinaryInputObject):
    _cov_criteria = GenericCriteria

class AnalogInputObject(_Object, _AnalogInputObject):
    _cov_criteria = COVIncrementCriteria


# dictionary of names to objects
objects = {}

async def update_data(delay):
    global objects

    while True:
        await asyncio.sleep(delay)
        # ask the web service
        try:
            response = requests.get(
                # "http://localhost:8000/samples/Silvair/new_data.json"
                "http://127.0.0.1/bacnet?time=%d" % (delay + 10)
            )

        except Exception as inst:
            print("Connection error: %r" % (type(inst),))
            continue

        if response.status_code != 200:
            print("Error response: %r" % (response.status_code,))
            continue

        # turn the response string into a JSON object
        json_response = response.json()

        for key in json_response:
            # print(key)
            instance = int(key) + BI_SHIFT # TODO fixed as of today
            entry = json_response[key]
            if instance in objects:
                # print(objects[entry["name"]].presentValue)
                if objects[instance].presentValue != entry["Value"]:
                    print("change Group %s -> %r %r"%(key,entry["Value"], entry["OutOfService"]))
                    objects[instance].presentValue=entry["Value"]
                    objects[instance].outOfService=entry["OutOfService"]


def read_json(app):
    #     """Create the objects that hold the result values."""
    if _debug:
        read_json._debug("create_objects %r", app)
    global objects

    # Opening JSON file
    f = open('samples/Silvair/gen.json')
    # f = open('samples/Silvair/data.json')
    data = json.load(f)
    f.close()


    for entry in data['bacnet']:
        if _debug:
            read_json._debug(entry)

        typeObj = None

        match entry["type"]:
            case "BI":
                typeObj = BinaryInputObject
                shift = BI_SHIFT
            case "AI":
                typeObj = AnalogInputObject
                shift = AI_SHIFT
            case "SV":
                typeObj = _StructuredViewObject
                shift = SV_SHIFT

        # create an object
        obj = typeObj(
            objectName=entry["name"], 
            objectIdentifier=(typeObj.objectType, entry["instance"] )
        )

        # Common properties so far
        if "description" in entry:
            obj.description= entry["description"]

        if "parent" in entry:
            # parent is SV
            objects[entry["parent"]+SV_SHIFT].subordinateList.append(DeviceObjectReference(objectIdentifier = obj.objectIdentifier))


        if entry["type"] == "AI":
            obj.statusFlags=[0, 0, 0, 0]
            obj.outOfService=False
            obj.eventState=EventState('normal')
            obj.presentValue=0
            # mandatory for COV
            obj.covIncrement=1.0
            # set the units, mandatory
            obj.units = entry["unit"]

        if entry["type"] == "BI":
            obj.statusFlags=[0, 0, 0, 0]
            obj.outOfService=False
            obj.presentValue=False
            obj.polarity=Polarity('normal')
            obj.eventState=EventState('normal')
        
        if entry["type"] == "SV":
            obj.subordinateList=ArrayOf(DeviceObjectReference)([])
            if "nodetype" in entry:
                obj.nodeType=NodeType(entry["nodetype"])

        # add it to the application
        app.add_object(obj)
        if _debug:
            read_json._debug("    - obj: %r", obj)

        # keep track of the object by name
        objects[entry["instance"] + shift] = obj


async def main() -> None:
    
    asyncio.create_task(update_data(5))
    try:
        app = None
        parser = SimpleArgumentParser()

        # make sure the vendor identifier is the custom one
        args = parser.parse_args()
        args.vendoridentifier = _vendor_id
        if _debug:
            _log.debug("args: %r", args)

        # build an application
        app = Application.from_args(args)
        if _debug:
            _log.debug("app: %r", app)

        read_json(app)

        # like running forever
        await asyncio.Future()

    finally:
        if app:
            app.close()

if __name__ == "__main__":
    asyncio.run(main())
