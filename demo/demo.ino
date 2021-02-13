#include <FlexCAN.h>
#include <EEPROM.h>

#include "yacp.h"
#include "cal.h"
#include <stdint.h>

// Vars
calibration cal;
CAN_message_t can_out_msg;
CAN_message_t can_in_msg;

void send_can(uint32_t id, uint8_t* buf)
{
  can_out_msg.ext = 0;
  can_out_msg.len = 8;
  can_out_msg.id = id;

  memcpy(&can_out_msg.buf[0], buf, 8);
    
  Can0.write(can_out_msg);
}

void recvCAN()
{
  while (Can0.available()) 
  {
    Can0.read(can_in_msg);

    handle_can(can_in_msg.id, can_in_msg.buf);
  }
}

uint32_t eeprom_crc() 
{
  // CRC calc by Christopher Andrews.
  const uint32_t crc_table[16] = 
  {
    0x00000000, 0x1db71064, 0x3b6e20c8, 0x26d930ac,
    0x76dc4190, 0x6b6b51f4, 0x4db26158, 0x5005713c,
    0xedb88320, 0xf00f9344, 0xd6d6a3e8, 0xcb61b38c,
    0x9b64c2b0, 0x86d3d2d4, 0xa00ae278, 0xbdbdf21c
  };
  uint32_t crc = ~0L;
  
  for (int index = 4; index < sizeof(cal); ++index) 
  {
    crc = crc_table[(crc ^ EEPROM[index]) & 0x0f] ^ (crc >> 4);
    crc = crc_table[(crc ^ (EEPROM[index] >> 4)) & 0x0f] ^ (crc >> 4);
    crc = ~crc;
  }

  return crc;
}

void load_settings()
{
  uint32_t stored_checksum;
  uint32_t calculated_checksum = eeprom_crc();
  
  EEPROM.get(0, stored_checksum);
  // TODO: add device ID

  if (stored_checksum != calculated_checksum)
  {
    Serial.print("CRC Failed: stored ");
    Serial.print(stored_checksum);
    Serial.print(" actual ");
    Serial.println(calculated_checksum);
    
    return;
  }

  Serial.print("EEPROM CRC: ");
  Serial.println(calculated_checksum);
  
  EEPROM.get(4, cal);
}

void save_settings()
{
  EEPROM.put(4, cal);
  EEPROM.put(0, eeprom_crc());
}

unsigned long startup_counter;

void setup() 
{
  Can0.begin(500000);
  
  Serial.begin(115200);
  delay(500);
  
  load_settings();

  cal.settings.output_selector = 1;
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
  recvCAN();
  
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
