/*
 * YACP Demo for Teensy
 * Yet Another Calibration Protocol
 * 
 * This project demonstrates the main features of the YACP library.
 * 
 * For use with Teensy 3.5 or Teensy 3.6 using Can0.
 * 
 * Matthew Bergman 2021
 * 
 * MIT license, all text above must be included in any redistribution.
 * See license.txt at the root of the repository for full license text.
 */

#include <FlexCAN.h>

// Include the calibration struct definitions generated by the YACP tools.
#include "cal.h"

// The calibration struct is declared in cal.c
extern calibration cal;

// Local vars
unsigned long startup_counter;

void setup() 
{
  // Start the CAN and Serial devices
  Can0.begin(500000);
  Serial.begin(115200);

  // Load default settings and saved settings from EEPROM
  // into the cal structs
  yacp_init();

  // Measurements can be set anywhere in the project code
  cal.measurements.var_u8 = 254;
  cal.measurements.var_u16 = 65535;
  cal.measurements.var_u32 = 75000;
  cal.measurements.var_i8 = -1;
  cal.measurements.var_i16 = -300;
  cal.measurements.var_i32 = -75000;
  cal.measurements.var_f = 0.12345;

  startup_counter = millis() + 1000;
}

void loop() 
{
  // Periodically check for new YACP CAN messages
  yacp_can_recv();

  // Each override has a status of overridden or passthrough. 
  // If the status is set to overriden then use the value set in the override,
  // otherwise use your application logic. 
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
  }
}
