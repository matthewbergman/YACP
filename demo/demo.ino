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

  cal.measurements.cal_ver = 1;

  cal.measurements.test_var = 0xAA;


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
  
  if (cal.overrides.output_override.status == CAL_OVERRIDDEN)
  {
    //digitalWrite(cal.settings.output_selector, cal.overrides.output_override.value);
    cal.measurements.output_status = cal.overrides.output_override.value.u8;
  }
  else
  {
    //digitalWrite(cal.settings.output_selector, LOW);
    cal.measurements.output_status = 0;
  }

  if (millis() > startup_counter)
  {
    cal.measurements.counter++;
    startup_counter = millis() + 1000;
  }
}
