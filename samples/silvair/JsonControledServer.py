# -*- coding: utf-8 -*-

"""
Json Controlled Server 3

Sample BACnetIP application with a structure of the server defined from the JSON file.
"""

import asyncio

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


from bacpypes3.basetypes import Polarity
from bacpypes3.basetypes import EventState
from bacpypes3.basetypes import NodeType

from bacpypes3.constructeddata import ArrayOf
from bacpypes3.vendor import VendorInfo


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
    _cov_criteria = COVIncrementCriteria

class LocalAnalogInputObject(_Object, _AnalogInputObject):
    _cov_criteria = COVIncrementCriteria


# dictionary of names to objects
objects = {}

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
                typeObj = _BinaryInputObject
            case "AI":
                typeObj = _AnalogInputObject
            case "SV":
                typeObj = _StructuredViewObject

        # create an object
        obj = typeObj(
            objectName=entry["name"], 
            objectIdentifier=(typeObj.objectType, entry["instance"] )
        )

        # Common properties so far
        if "description" in entry:
            obj.description= entry["description"]

        if "parent" in entry:
            objects[entry["parent"]].subordinateList.append(DeviceObjectReference(objectIdentifier = obj.objectIdentifier))


        if entry["type"] == "AI":
            obj.statusFlags=[0, 0, 0, 0]
            obj.outOfService=False
            obj.eventState=EventState('normal')
            # mandatory for COV
            obj.covIncrement=1.0
            obj.presentValue=0.0
            # set the units, mandatory
            obj.units = entry["unit"]

        if entry["type"] == "BI":
            obj.statusFlags=[0, 0, 0, 0]
            obj.outOfService=False
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
        objects[entry["name"]] = obj


async def main() -> None:
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
