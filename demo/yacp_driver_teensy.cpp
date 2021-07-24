/*
 * yacp_driver_teensy.cpp
 * Yet Another Calibration Protocol (YACP)
 * 
 * This is a driver for use with Teensy 3.5 or Teensy 3.6 boards and Can0.
 * 
 * Matthew Bergman 2021
 * 
 * MIT license, all text above must be included in any redistribution.
 * See license.txt at the root of the repository for full license text.
 */

#include <FlexCAN.h>
#include <EEPROM.h>

#include "yacp.h"
#include "yacp_api.h"

CAN_message_t can_out_msg;
CAN_message_t can_in_msg;

void yacp_can_send(uint32_t id, uint8_t* buf)
{
  can_out_msg.ext = 0;
  can_out_msg.len = 8;
  can_out_msg.id = id;
  can_out_msg.flags.remote = 0;

  memcpy(&can_out_msg.buf[0], buf, 8);
    
  Can0.write(can_out_msg);
}

void yacp_can_recv()
{
  while (Can0.available()) 
  {
    Can0.read(can_in_msg);

    yacp_handle_can(can_in_msg.id, can_in_msg.buf);
  }
}

uint8_t yacp_eeprom_load_byte(uint16_t addr)
{
  uint8_t tmp;
  
  EEPROM.get(addr, tmp);
  
  return tmp;
}

void yacp_eeprom_store_byte(uint16_t addr, uint8_t val)
{
  EEPROM.put(addr, val);
}

void yacp_eeprom_persist()
{
	// Not needed
}

void yacp_memcpy(void* s1, const void* s2, uint16_t n)
{
	memcpy(s1, s2, n);
}

void yacp_update_setting(uint8_t* dst, uint16_t var_start, uint8_t var_len, uint8_t* buf)
{
	uint32_t value32;
	uint16_t value16;
	uint8_t value8;

    if (var_len == 1)
    {
      value8 = buf[4];
      memcpy(dst + var_start, &value8, var_len);
    }
    else if (var_len == 2)
    {
      value16 = buf[5];
      value16 |= (uint32_t)buf[4] << 8;
      memcpy(dst + var_start, &value16, var_len);
    }
    else if (var_len == 4)
    {
      value32 = buf[7];
      value32 |= (uint32_t)buf[6] << 8;
      value32 |= (uint32_t)buf[5] << 16;
      value32 |= (uint32_t)buf[4] << 24;
      memcpy(dst + var_start, &value32, var_len);
    }
}
