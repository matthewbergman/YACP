#include "yacp.h"
#include "cal.h"

#include <arduino.h> // TODO: remove

#include <string.h>

extern calibration cal;

void send_measurement(uint16_t measurement_start, uint8_t var_len)
{
  uint8_t buf[8];

  buf[0] = CAL_READ_MEASUREMENT | (DEVICE_ID << 4);
  buf[1] = measurement_start;
  buf[2] = measurement_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  memcpy(&buf[4], (uint8_t*)&cal.measurements + measurement_start, var_len);
    
  send_can(SSCCP_UPDATE_ID, buf);
}

void send_setting(uint16_t setting_start, uint8_t var_len)
{
  uint8_t buf[8];

  buf[0] = CAL_READ_SETTING | (DEVICE_ID << 4);
  buf[1] = setting_start;
  buf[2] = setting_start >> 8;
  buf[3] = var_len;

  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;

  memcpy(&buf[4], (uint8_t*)&cal.settings + setting_start, var_len);
    
  send_can(SSCCP_UPDATE_ID, buf);
}

void send_hello()
{
  uint8_t buf[8];

  buf[0] = CAL_HELLO | (DEVICE_ID << 4);
  buf[1] = 0;
  buf[2] = 0;
  buf[3] = 0;
  buf[4] = 0;
  buf[5] = 0;
  buf[6] = 0;
  buf[7] = 0;
    
  send_can(SSCCP_UPDATE_ID, buf);
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

      if (device_id != DEVICE_ID)
        break;

      if (message_type == CAL_UPDATE_SETTING)
      {
        memcpy((uint8_t*)&cal.settings + var_start, &value, var_len);
        send_setting(var_start, var_len);
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

        // TODO: send cal_read_override message
      }
      else if (message_type == CAL_READ_OVERRIDE)
      {
        // TODO: send cal_read_override message
      }
      else if (message_type == CAL_READ_MEASUREMENT)
      {
        send_measurement(var_start, var_len);
      }
      else if (message_type == CAL_SAVE_SETTINGS)
      {
        save_settings();
        // TODO: send save_settings message
      }
      
      break;
  }
}
