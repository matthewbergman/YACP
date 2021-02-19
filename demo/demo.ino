#include <stdint.h>
#include <FlexCAN.h>

#include "cal.h"

extern calibration cal;

// Vars
unsigned long startup_counter;

void setup() 
{
  Can0.begin(500000);
  
  Serial.begin(115200);
  delay(500);
  
  yacp_init();

  cal.measurements.var_u8 = 254;
  cal.measurements.var_u16 = 65535;
  cal.measurements.var_u32 = 75000;
  cal.measurements.var_i8 = -1;
  cal.measurements.var_i16 = -300;
  cal.measurements.var_i32 = -75000;
  cal.measurements.var_f = 0.12345;

  Serial.println(cal.overrides.override_i32.value.i32);
  Serial.println(cal.overrides.override_f.value.f);


  Serial.println("Struct sizes");
  
  Serial.print("calibration: ");
  Serial.println(sizeof(calibration));

  Serial.print("measurements: ");
  Serial.println(sizeof(cal_measurements));

  Serial.print("cal_settings: ");
  Serial.println(sizeof(cal_settings));

  Serial.print("cal_overrides: ");
  Serial.println(sizeof(cal_overrides));

  startup_counter = millis() + 1000;
}

void loop() 
{
  yacp_can_recv();

  if (cal.overrides.override_i32.status == CAL_OVERRIDDEN)
    cal.measurements.var_i32 = cal.overrides.override_i32.value.i32;
  else
    cal.measurements.var_i32 = -75000;

  if (cal.overrides.override_f.status == CAL_OVERRIDDEN)
    cal.measurements.var_f = cal.overrides.override_f.value.f;
  else
    cal.measurements.var_f = 0.12345;

  if (millis() > startup_counter)
  {
    cal.measurements.counter++;
    startup_counter = millis() + 1000;

    Serial.print(cal.overrides.override_f.status);
    Serial.print(" ");
    Serial.println(cal.overrides.override_f.value.f);
  }
}
