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

void can_send(uint32_t id, uint8_t* buf)
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

    handle_can(can_in_msg.id, can_in_msg.buf);
  }
}

uint8_t eeprom_load_byte(uint16_t addr)
{
  uint8_t tmp;
  
  EEPROM.get(addr, tmp);
  
  return tmp;
}

void eeprom_store_byte(uint16_t addr, uint8_t val)
{
  EEPROM.put(addr, val);
}
