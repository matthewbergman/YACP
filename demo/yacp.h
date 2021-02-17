#ifndef YACP_H_
#define YACP_H_

#include <stdint.h>

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
#define CAL_ACK 8

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

// Drivers
void can_start();
void can_send(uint32_t id, uint8_t* buf);
void can_recv();
uint8_t eeprom_load_byte(uint16_t addr);
void eeprom_store_byte(uint16_t addr, uint8_t val);

// Internal
void load_settings();
void save_settings();
void handle_can(uint32_t id, uint8_t* buf);

#endif
