/*
 * yacp_funs.c
 * Yet Another Calibration Protocol (YACP)
 * 
 * This is the main implemenation of the YACP protocol.
 * 
 * Matthew Bergman 2021
 * 
 * MIT license, all text above must be included in any redistribution.
 * See license.txt at the root of the repository for full license text.
 */

#include "cal.h"
#include "yacp.h"

#include <string.h>

// Vars
extern calibration cal;

uint8_t yacp_product_firmware_version;
uint8_t yacp_product_id;
bool yacp_eeprom_version_mismatch_f;
bool yacp_eeprom_crc_mismatch_f;


// Internal function declarations
void yacp_send_measurement(uint16_t measurement_start, uint8_t var_len);
void yacp_send_setting(uint16_t setting_start, uint8_t var_len);
void yacp_send_override(uint8_t message_type, uint16_t override_start, uint8_t var_len);
void yacp_send_hello();
void yacp_send_ack();
uint32_t yacp_eeprom_crc();

// API Functions
void yacp_init()
{
  /* First load the default values defined in the cal.c generated code.
   * Then attempt to load the stored settings from EEEPROM. 
   */
  yacp_load_defaults();
  yacp_load_settings();
}

void yacp_load_settings()
{  
  // Load the stored settings CRC value from EEPROM
  uint32_t stored_checksum = 0;
  stored_checksum |= (uint32_t)yacp_eeprom_load_byte(EEPROM_CRC_OFFSET);
  stored_checksum |= (uint32_t)yacp_eeprom_load_byte(EEPROM_CRC_OFFSET + 1) << 8;
  stored_checksum |= (uint32_t)yacp_eeprom_load_byte(EEPROM_CRC_OFFSET + 2) << 16;
  stored_checksum |= (uint32_t)yacp_eeprom_load_byte(EEPROM_CRC_OFFSET + 3) << 24;

  // Generate a CRC of the stored settings in EEPROM
  uint32_t calculated_checksum = yacp_eeprom_crc();

  // Make sure the data in EEPROM has not changed since
  // the CRC was stored during the last call to save_settings().
  if (stored_checksum != calculated_checksum)
  {
    // EEPROM has changed, raise the crc mismatch flag!
    yacp_eeprom_crc_mismatch_f = true;

    // DO NOT load the settings from EEPROM, use the default values instead.
    return;
  }

  // The EEPROM CRC is valid, load the settings into the cal settings struct.
  uint8_t* cal_ptr = (uint8_t*)&cal.settings;
  size_t i;
  for (i=0; i<sizeof(cal.settings); i++)
  {
    cal_ptr[i] = yacp_eeprom_load_byte(i + EEPROM_SETTINGS_OFFSET);
  }

  // Verify tha the revision compiled into cal.h matches what is stored in
  // the settings in EEPROM. This assures that the struct matches the data
  // offsets and sizes of the data in EEPROM.
  if (CAL_REVISION != cal.settings.revision)
  {
    // The stored revision number in EEPROM does not match the cal.h revision.
    yacp_eeprom_version_mismatch_f = true;

    // Clear out the settings struct of the incorrect EEPROM data
    memset(&cal.settings, 0, sizeof(cal.settings));
    
	// Load the defaults from the generated code and save to EEPROM
    yacp_load_defaults();
    yacp_save_settings();

    // A new cal will need to be pushed and saved using the GUI.
  }
}

void yacp_save_settings()
{
  // Save the cal settings struct to EEPROM, byte for byte.
  uint8_t* cal_ptr = (uint8_t*)&cal.settings;
  size_t i;
  for (i=0; i<sizeof(cal.settings); i++)
    yacp_eeprom_store_byte(i + EEPROM_SETTINGS_OFFSET, cal_ptr[i]);

  // Calculate the CRC of the EEPROM data just saved
  uint32_t crc = yacp_eeprom_crc();

  // Save the CRC value to EEPROM for validation on next startup
  yacp_eeprom_store_byte(EEPROM_CRC_OFFSET, crc);
  yacp_eeprom_store_byte(EEPROM_CRC_OFFSET + 1, crc >> 8);
  yacp_eeprom_store_byte(EEPROM_CRC_OFFSET + 2, crc >> 16);
  yacp_eeprom_store_byte(EEPROM_CRC_OFFSET + 3, crc >> 24);

  yacp_eeprom_persist();
}

// Internal Functions
void yacp_send_measurement(uint16_t measurement_start, uint8_t var_len)
{
  uint8_t buf[8];

  // Send a measurement value back to the requestor
  buf[0] = CAL_READ_MEASUREMENT | (cal.settings.device_id << 4);
  buf[1] = measurement_start;
  buf[2] = measurement_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  yacp_memcpy(&buf[4], (uint8_t*)&cal.measurements + measurement_start, var_len);
    
  yacp_can_send(YACP_UPDATE_ID, buf);
}

void yacp_send_setting(uint16_t setting_start, uint8_t var_len)
{
  uint8_t buf[8];

  // Send a setting value back to the requestor
  buf[0] = CAL_READ_SETTING | (cal.settings.device_id << 4);
  buf[1] = setting_start;
  buf[2] = setting_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  yacp_memcpy(&buf[4], (uint8_t*)&cal.settings + setting_start, var_len);
    
  yacp_can_send(YACP_UPDATE_ID, buf);
}

void yacp_send_override(uint8_t message_type, uint16_t override_start, uint8_t var_len)
{
  uint8_t buf[8];

  // Send a override value and status back to the requestor
  buf[0] = message_type | (cal.settings.device_id << 4);
  buf[1] = override_start;
  buf[2] = override_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  yacp_memcpy(&buf[4], (uint8_t*)&cal.overrides + override_start + 1, var_len);
    
  yacp_can_send(YACP_UPDATE_ID, buf);
}

void yacp_send_hello()
{
  uint8_t buf[8];

  // Respond to a HELLO message with our device ID
  buf[0] = CAL_HELLO | (cal.settings.device_id << 4);
  buf[1] = 0;
  buf[2] = 0;
  buf[3] = 0;

  buf[4] = yacp_product_firmware_version;
  buf[5] = yacp_product_id;
  buf[6] = CAL_REVISION;
  buf[7] = CAL_PROTOCOL_VERSION;
    
  yacp_can_send(YACP_UPDATE_ID, buf);
}

void yacp_send_ack()
{
  uint8_t buf[8];

  // Send an ack after a successful command response
  buf[0] = CAL_ACK | (cal.settings.device_id << 4);
  buf[1] = 0;
  buf[2] = 0;
  buf[3] = 0;
  buf[4] = 1; // 1: success, 0: failure
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;
    
  yacp_can_send(YACP_UPDATE_ID, buf);
}

void yacp_handle_can(uint32_t id, uint8_t* buf)
{
  uint8_t device_id;
  uint8_t message_type;
  uint16_t var_start;
  uint8_t var_len;

  switch (id)
  {
    case YACP_COMMAND_ID:
      device_id = buf[0] >> 4;
      message_type = buf[0] & 0x0F;
      var_start = buf[1];
      var_start |= (uint16_t)buf[2] << 8;
      var_len = buf[3];

      if (message_type == CAL_HELLO)
      {
        yacp_send_hello();
      }

      if (device_id != cal.settings.device_id)
        break;

      if (message_type == CAL_UPDATE_SETTING)
      {
    	yacp_can_send(0x200+var_start, buf);

    	yacp_can_send(0x300+var_start, (uint8_t*)&cal.settings);

    	//memcpy(((uint8_t*)&cal.settings) + var_start, &value, var_len);
    	yacp_update_setting((uint8_t*)&cal.settings, var_start, var_len, buf);

    	yacp_can_send(0x400+var_start, (uint8_t*)&cal.settings);

        yacp_send_ack();
      }
      else if (message_type == CAL_READ_SETTING)
      {
        yacp_send_setting(var_start, var_len);
      }
      else if (message_type == CAL_OVERRIDE_ON || message_type == CAL_OVERRIDE_OFF)
      {
        if (message_type == CAL_OVERRIDE_ON)
          *((uint8_t*)&cal.overrides + var_start) = CAL_OVERRIDDEN;
        else
          *((uint8_t*)&cal.overrides + var_start) = CAL_PASSTHRU;
          
        //memcpy((uint8_t*)&cal.overrides + var_start + 1, &value, 4);
        yacp_update_setting((uint8_t*)&cal.overrides, var_start+1, 4, buf);

        yacp_send_ack();
      }
      else if (message_type == CAL_READ_OVERRIDE)
      {
        if (*((uint8_t*)&cal.overrides + var_start) == CAL_PASSTHRU)
          yacp_send_override(CAL_OVERRIDE_OFF, var_start, var_len);
        else
          yacp_send_override(CAL_OVERRIDE_ON, var_start, var_len);
      }
      else if (message_type == CAL_READ_MEASUREMENT)
      {
        yacp_send_measurement(var_start, var_len);
      }
      else if (message_type == CAL_SAVE_SETTINGS)
      {
        yacp_save_settings();
        
        yacp_send_ack();
      }
      
      break;
  }
}

uint32_t yacp_eeprom_crc() 
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
  
  uint16_t index;
  for (index = 0; index < sizeof(cal.settings); ++index)
  {
    val = yacp_eeprom_load_byte(index + EEPROM_SETTINGS_OFFSET);
    
    crc = crc_table[(crc ^ val) & 0x0f] ^ (crc >> 4);
    crc = crc_table[(crc ^ (val >> 4)) & 0x0f] ^ (crc >> 4);
    crc = ~crc;
  }

  return crc;
}
