#ifndef YACP_H_
#define YACP_H_

#include <stdint.h>

#define DEVICE_ID 1 // TODO: should be EEPROM

#define SSCCP_COMMAND_ID 0x100
#define SSCCP_UPDATE_ID 0x101

#define CAL_UPDATE_SETTING 0
#define CAL_READ_SETTING 1
#define CAL_OVERRIDE_ON 2
#define CAL_OVERRIDE_OFF 3
#define CAL_READ_OVERRIDE 4
#define CAL_READ_MEASUREMENT 5
#define CAL_SAVE_SETTINGS 6
#define CAL_HELLO 7

#define CAL_PASSTHRU 0
#define CAL_OVERRIDDEN 1

// Struct defs

union cal_value
{
  uint8_t u8;
  int8_t i8;
  uint16_t u16;
  int16_t i16;
  float f;
};

typedef struct __attribute__((packed)) cal_override
{
  uint8_t status;
  cal_value value;
} cal_override;

// Functions

void send_can(uint32_t id, uint8_t* buf);
void load_settings();
void save_settings();

void send_measurement(uint16_t measurement_start, uint8_t var_len);
void send_setting(uint16_t setting_start, uint8_t var_len);
void handle_can(uint32_t id, uint8_t* buf);
void send_hello();
#endif
