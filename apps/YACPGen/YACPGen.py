"""
YACPGen.py
Yet Another Calibration Protocol (YACP)

This code generates cal.c and cal.h files from the project-def.json YACP def file.

Usage: YACP_gen.py ./path/to/project-def.json

Matthew Bergman 2021

MIT license, all text above must be included in any redistribution.
See license.txt at the root of the repository for full license text.
"""

from version import VERSION

import json
import sys
import re

lengths = {}
lengths["uint8"] = 1
lengths["int8"] = 1
lengths["uint16"] = 2
lengths["int16"] = 2
lengths["uint32"] = 4
lengths["int32"] = 4
lengths["float"] = 4

types_c = {}
types_c["uint8"] = "uint8_t"
types_c["int8"] = "int8_t"
types_c["uint16"] = "uint16_t"
types_c["int16"] = "int16_t"
types_c["uint32"] = "uint32_t"
types_c["int32"] = "int32_t"
types_c["float"] = "float"

re_spaces = re.compile('([\W]+)')
def name_to_identifier(name):
    return re_spaces.sub('_', name.strip()).upper()

def header_start(rev):
    hfile.write("/* THIS IS GENERATED CODE FROM THE YACP PROJECT. DO NOT MODIFY! */\n\n")
    hfile.write("#ifndef YACP_CAL_H_\n")
    hfile.write("#define YACP_CAL_H_\n\n")
    hfile.write("#include \"yacp_api.h\"\n\n")
    hfile.write("#define CAL_REVISION "+rev+"\n\n")

def measurements_start():
    hfile.write("#pragma pack(push)\n")
    hfile.write("#pragma pack(1)\n")
    hfile.write("typedef struct cal_measurements\n")
    hfile.write("{\n")

def measurements_var(name,cal_type,unit):
    if unit != "":
        unit = " // "+unit
    hfile.write("\t"+types_c[cal_type]+" "+name+";"+unit+"\n")

def measurements_end():
    hfile.write("} cal_measurements;\n\n")
    

def settings_start():
    hfile.write("#pragma pack(1)\n")
    hfile.write("typedef struct cal_settings\n")
    hfile.write("{\n")

def settings_var(name,cal_type,unit):
    if unit != "":
        unit = " // "+unit
    hfile.write("\t"+types_c[cal_type]+" "+name+";"+unit+"\n")

def settings_end():
    hfile.write("} cal_settings;\n\n")
    

def override_start():
    hfile.write("#pragma pack(1)\n")
    hfile.write("typedef struct cal_overrides\n")
    hfile.write("{\n")

def override_var(name,unit):
    if unit != "":
        unit = " // "+unit
    hfile.write("\tcal_override "+name+";"+unit+"\n")

def override_end():
    hfile.write("} cal_overrides;\n")
    hfile.write("#pragma pack(pop)\n\n")
    

def header_end():
    hfile.write("typedef struct calibration\n")
    hfile.write("{\n")
    hfile.write("\tcal_measurements measurements;\n")
    hfile.write("\tcal_settings settings;\n")
    hfile.write("\tcal_overrides overrides;\n")
    hfile.write("} calibration;\n\n")
    hfile.write("#endif\n")

def impl_start():
    cfile.write("/* THIS IS GENERATED CODE FROM THE YACP PROJECT. DO NOT MODIFY! */\n\n")
    cfile.write("#include \"cal.h\"\n\n")
    cfile.write("calibration cal;\n\n")
    cfile.write("void yacp_load_defaults()\n")
    cfile.write("{\n")

def impl_var(var,val):
    cfile.write("\tcal.settings."+var+" = "+val+";\n")

def impl_end():
    cfile.write("}\n")


def choice_enum(name, val):
    hfile.write("#define "+name+" "+val+"\n")

if len(sys.argv) != 2:
    print("YACPgen "+VERSION+" Usage: YACPgen.exe ./path/to/project-def.json")
    sys.exit(1)
    
def_filename = sys.argv[1]

try:
    def_file = open(def_filename, 'r')
except:
    print("Failed to open "+def_filename+" for reading!")
    sys.exit(1)

defs = json.load(def_file)

def_file.close()

found_required_settings = 0
rev = 0
for setting in defs["settings"]:
    if setting["name"] == "device_id":
        found_required_settings += 1
    if setting["name"] == "revision":
        found_required_settings += 1
        rev = setting["default"]
        
if found_required_settings != 2:
    print("The settings section must include 'device_id' and 'revision'.")
    sys.exit(1)


try:
    hfile = open('cal.h','w')
except:
    print("Failed to open cal.h for writing!")
    sys.exit(1)
    

header_start(rev)

written = False
for measurement in defs["measurements"]:
    if "values" in measurement.keys():
        for value in measurement["values"]:
            name = name_to_identifier(measurement["name"]+"_VALUE_"+value["name"])
            choice_enum(name, value["value"])
            written = True
if written:
    hfile.write("\n")

written = False
for setting in defs["settings"]:
    if "choices" in setting.keys():
        for choice in setting["choices"]:
            name = name_to_identifier(setting["name"]+"_CHOICE_"+choice["name"])
            choice_enum(name, choice["value"])
            written = True
if written:
    hfile.write("\n")

measurements_start()
for measurement in defs["measurements"]:
    unit = ""
    if "unit" in measurement.keys():
        unit = measurement["unit"]
    measurements_var(measurement["name"], measurement["type"], unit)
measurements_end()

settings_start()
for setting in defs["settings"]:
    unit = ""
    if "unit" in setting.keys():
        unit = setting["unit"]
    settings_var(setting["name"], setting["type"], unit)
settings_end()

override_start()
for override in defs["overrides"]:
    unit = ""
    if "unit" in override.keys():
        unit = override["unit"]
    override_var(override["name"], unit)
override_end()

header_end()
        
hfile.close()

try:
    cfile = open('cal.c','w')
except:
    print("Failed to open cal.c for writing!")
    sys.exit(1)

impl_start()
for setting in defs["settings"]:
    impl_var(setting["name"], setting["default"])
impl_end()

cfile.close()
    
