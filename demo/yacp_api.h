#ifndef YACP_API_H_
#define YACP_API_H_

#include <stdint.h>

#define CAL_PASSTHRU 0
#define CAL_OVERRIDDEN 1

// Struct defs

typedef union cal_value
{
  uint8_t u8;
  int8_t i8;
  uint16_t u16;
  int16_t i16;
  float f;
} cal_value;

typedef struct __attribute__((packed)) cal_override
{
  uint8_t status;
  cal_value value;
} cal_override;

// Driver Functions
void can_send(uint32_t id, uint8_t* buf);
void yacp_can_recv();
uint8_t eeprom_load_byte(uint16_t addr);
void eeprom_store_byte(uint16_t addr, uint8_t val);

// YACP API
void yacp_init();

#endif
