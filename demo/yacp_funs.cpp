#include "cal.h"
#include "yacp.h"

#include <arduino.h> // TODO: remove

#include <string.h>

extern calibration cal;

// Internal functions

void send_measurement(uint16_t measurement_start, uint8_t var_len);
void send_setting(uint16_t setting_start, uint8_t var_len);
void send_override(uint8_t message_type, uint16_t override_start, uint8_t var_len);
void send_hello();
void send_ack();
uint32_t eeprom_crc();

// Functions

void send_measurement(uint16_t measurement_start, uint8_t var_len)
{
  uint8_t buf[8];

  buf[0] = CAL_READ_MEASUREMENT | (cal.settings.device_id << 4);
  buf[1] = measurement_start;
  buf[2] = measurement_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  memcpy(&buf[4], (uint8_t*)&cal.measurements + measurement_start, var_len);
    
  can_send(SSCCP_UPDATE_ID, buf);
}

void send_setting(uint16_t setting_start, uint8_t var_len)
{
  uint8_t buf[8];

  buf[0] = CAL_READ_SETTING | (cal.settings.device_id << 4);
  buf[1] = setting_start;
  buf[2] = setting_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  memcpy(&buf[4], (uint8_t*)&cal.settings + setting_start, var_len);
    
 can_send(SSCCP_UPDATE_ID, buf);
}

void send_override(uint8_t message_type, uint16_t override_start, uint8_t var_len)
{
  uint8_t buf[8];

  buf[0] = message_type | (cal.settings.device_id << 4);
  buf[1] = override_start;
  buf[2] = override_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  memcpy(&buf[4], (uint8_t*)&cal.overrides + override_start + 1, var_len);
    
 can_send(SSCCP_UPDATE_ID, buf);
}

void send_hello()
{
  uint8_t buf[8];

  buf[0] = CAL_HELLO | (cal.settings.device_id << 4);
  buf[1] = 0;
  buf[2] = 0;
  buf[3] = 0;
  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;
    
  can_send(SSCCP_UPDATE_ID, buf);
}

void send_ack()
{
  uint8_t buf[8];

  buf[0] = CAL_ACK | (cal.settings.device_id << 4);
  buf[1] = 0;
  buf[2] = 0;
  buf[3] = 0;
  buf[4] = 1;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;
    
  can_send(SSCCP_UPDATE_ID, buf);
}

void handle_can(uint32_t id, uint8_t* buf)
{
  uint8_t device_id;
  uint8_t message_type;
  uint16_t var_start;
  uint8_t var_len;
  uint32_t value;

  switch (id)
  {
    case SSCCP_COMMAND_ID:
      device_id = buf[0] >> 4;
      message_type = buf[0] & 0x0F;
      var_start = buf[1];
      var_start |= (uint16_t)buf[2] << 8;
      var_len = buf[3];
      value = buf[4];
      value |= (uint32_t)buf[5] << 8;
      value |= (uint32_t)buf[6] << 16;
      value |= (uint32_t)buf[7] << 24;

      Serial.print("type: ");
      Serial.print(message_type);
      Serial.print(" start: ");
      Serial.print(var_start);
      Serial.print(" len: ");
      Serial.println(var_len);

      if (message_type == CAL_HELLO)
      {
        send_hello();
      }

      if (device_id != cal.settings.device_id)
        break;

      if (message_type == CAL_UPDATE_SETTING)
      {
        memcpy((uint8_t*)&cal.settings + var_start, &value, var_len);
        send_ack();
      }
      else if (message_type == CAL_READ_SETTING)
      {
        send_setting(var_start, var_len);
      }
      else if (message_type == CAL_OVERRIDE_ON || message_type == CAL_OVERRIDE_OFF)
      {
        if (message_type == CAL_OVERRIDE_ON)
          *((uint8_t*)&cal.overrides + var_start) = CAL_OVERRIDDEN;
        else
          *((uint8_t*)&cal.overrides + var_start) = CAL_PASSTHRU;
          
        memcpy((uint8_t*)&cal.overrides + var_start + 1, &value, 4);

        send_ack();
      }
      else if (message_type == CAL_READ_OVERRIDE)
      {
        if (*((uint8_t*)&cal.overrides + var_start) == CAL_PASSTHRU)
          send_override(CAL_OVERRIDE_OFF, var_start, var_len);
        else
          send_override(CAL_OVERRIDE_ON, var_start, var_len);
      }
      else if (message_type == CAL_READ_MEASUREMENT)
      {
        send_measurement(var_start, var_len);
      }
      else if (message_type == CAL_SAVE_SETTINGS)
      {
        save_settings();
        
        send_ack();
      }
      
      break;
  }
}

void yacp_init()
{
  load_defaults();
  load_settings();
}

void load_settings()
{  
  uint32_t stored_checksum = 0;
  stored_checksum |= (uint32_t)eeprom_load_byte(0);
  stored_checksum |= (uint32_t)eeprom_load_byte(1) << 8;
  stored_checksum |= (uint32_t)eeprom_load_byte(2) << 16;
  stored_checksum |= (uint32_t)eeprom_load_byte(3) << 24;
  
  uint32_t calculated_checksum = eeprom_crc();

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

  uint8_t* cal_ptr = (uint8_t*)&cal.settings;
  for (size_t i=0; i<sizeof(cal); i++)
  {
    cal_ptr[i] = eeprom_load_byte(i + 4);
  }

  if (CAL_REVISION != cal.settings.revision)
  {
    Serial.print("REV ");
    Serial.print(cal.settings.revision);
    Serial.print(" expected ");
    Serial.println(CAL_REVISION);

    memset(&cal.settings, 0, sizeof(cal.settings));
    load_defaults();
    save_settings();
  }
}

void save_settings()
{
  uint8_t* cal_ptr = (uint8_t*)&cal.settings;
  for (size_t i=0; i<sizeof(cal.settings); i++)
  {
    eeprom_store_byte(i + 4, cal_ptr[i]);
  }

  uint32_t crc = eeprom_crc();

  eeprom_store_byte(0, crc);
  eeprom_store_byte(1, crc >> 8);
  eeprom_store_byte(2, crc >> 16);
  eeprom_store_byte(3, crc >> 24);
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
  uint8_t val;
  
  for (uint16_t index = 0; index < sizeof(cal.settings); ++index) 
  {
    // TODO: make a define for cal EEPROM address start
    val = eeprom_load_byte(index + 4); // Add 4 to skip over the CRC value in the start of EEPROM

    Serial.println(val);
    
    crc = crc_table[(crc ^ val) & 0x0f] ^ (crc >> 4);
    crc = crc_table[(crc ^ (val >> 4)) & 0x0f] ^ (crc >> 4);
    crc = ~crc;
  }

  return crc;
}
