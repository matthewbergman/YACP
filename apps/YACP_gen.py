import csv

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

def measurements_var(role,name,cal_type):
    hfile.write(types_c[cal_type]+" "+name+";\n")

def measurements_end():
    hfile.write("} cal_measurements;\n\n")
    

def settings_start():
    hfile.write("typedef struct __attribute__((packed)) cal_settings\n")
    hfile.write("{\n")

def settings_var(role,name,cal_type):
    hfile.write(types_c[cal_type]+" "+name+";\n")

def settings_end():
    hfile.write("} cal_settings;\n\n")
    

def override_start():
    hfile.write("typedef struct __attribute__((packed)) cal_overrides\n")
    hfile.write("{\n")

def override_var(role,name,cal_type):
    hfile.write("cal_override "+name+";\n")

def override_end():
    hfile.write("} cal_overrides;\n\n")
    

def header_end():
    hfile.write("typedef struct calibration\n")
    hfile.write("{\n")
    hfile.write("  cal_measurements measurements;\n")
    hfile.write("  cal_settings settings;\n")
    hfile.write("  cal_overrides overrides;\n")
    hfile.write("} calibration;\n\n")
    hfile.write("#endif\n")




hfile = open('cal.h','w')

header_start()

measurements = []
settings = []
overrides = []
with open('vsccp.csv', newline='\n') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    first = True
    for row in reader:
        if first:
            first = False
            continue
        
        role = row[0]

        if role.strip().lower() == "measurement":
            measurements.append(row)
        elif role.strip().lower() == "setting":
            settings.append(row)
        elif role.strip().lower() == "override":
            overrides.append(row)

measurements_start()
for row in measurements:
    name = row[1]
    cal_type = row[2]
    default_value = row[3]
    value = row[4]
    measurements_var(role,name,cal_type)
measurements_end()

settings_start()
for row in settings:
    name = row[1]
    cal_type = row[2]
    default_value = row[3]
    value = row[4]
    settings_var(role,name,cal_type)
settings_end()

override_start()
for row in overrides:
    name = row[1]
    cal_type = row[2]
    default_value = row[3]
    value = row[4]
    settings_var(role,name,cal_type)
override_end()

header_end()
        
csvfile.close()
hfile.close()
