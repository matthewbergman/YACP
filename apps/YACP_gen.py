import json
import sys

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

def header_start():
    hfile.write("#ifndef YACP_CAL_H_\n")
    hfile.write("#define YACP_CAL_H_\n\n")
    hfile.write("#include \"yacp.h\"\n\n")
    

def measurements_start():
    hfile.write("typedef struct __attribute__((packed)) cal_measurements\n")
    hfile.write("{\n")

def measurements_var(name,cal_type):
    hfile.write("\t"+types_c[cal_type]+" "+name+";\n")

def measurements_end():
    hfile.write("} cal_measurements;\n\n")
    

def settings_start():
    hfile.write("typedef struct __attribute__((packed)) cal_settings\n")
    hfile.write("{\n")

def settings_var(name,cal_type):
    hfile.write("\t"+types_c[cal_type]+" "+name+";\n")

def settings_end():
    hfile.write("} cal_settings;\n\n")
    

def override_start():
    hfile.write("typedef struct __attribute__((packed)) cal_overrides\n")
    hfile.write("{\n")

def override_var(name):
    hfile.write("\tcal_override "+name+";\n")

def override_end():
    hfile.write("} cal_overrides;\n\n")
    

def header_end():
    hfile.write("typedef struct calibration\n")
    hfile.write("{\n")
    hfile.write("\tcal_measurements measurements;\n")
    hfile.write("\tcal_settings settings;\n")
    hfile.write("\tcal_overrides overrides;\n")
    hfile.write("} calibration;\n\n")
    hfile.write("#endif\n")


if len(sys.argv) != 2:
    print("Usage: YACP_gen.py ./path/to/project-def.json")
    sys.exit(1)
    
def_filename = sys.argv[1]

try:
    hfile = open('cal.h','w')
except:
    print("Failed to open cal.h for writing!")
    sys.exit(1)

try:
    def_file = open(def_filename, 'r')
except:
    print("Failed to open "+def_filename+" for reading!")
    sys.exit(1)

defs = json.load(def_file)



header_start()

measurements_start()
for measurement in defs["measurements"]:
    measurements_var(measurement["name"], measurement["type"])
measurements_end()

settings_start()
for setting in defs["settings"]:
    settings_var(setting["name"], setting["type"])
settings_end()

override_start()
for override in defs["overrides"]:
    override_var(override["name"])
override_end()

header_end()
        
def_file.close()
hfile.close()
