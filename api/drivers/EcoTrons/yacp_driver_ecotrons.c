/*
 * yacp_driver_ecotrons.c
 * Yet Another Calibration Protocol (YACP)
 * 
 * This is a driver for use with EcoTrons SCU and VCU products.
 *
 * Requirements:
 * 
 * Matthew Bergman 2021
 * 
 * MIT license, all text above must be included in any redistribution.
 * See license.txt at the root of the repository for full license text.
 */

#include "yacp.h"
#include "yacp_api.h"

#include "../can.h"

#include "ser_mem.h"
#include <string.h>

CANMsgElement_t yacp_can_msg;
CANMsgElement_t yacp_can_msg_in;

// EEPROM storage space for the cal
#define YACP_NVM_SIZE 1024
_FNVM_DATA_ uint8 yacp_nvm[YACP_NVM_SIZE];

void ycap_can_recv_callback(CanControllerIdType channel, CANMsgElement_t *messageObj);

void yacp_can_init()
{
	// Option 1) Use a slot for receiving filtered traffic, polling

	// Define the following somewhere pointed at the real slot
	// #define CAN_A_YACP_CMD appCANDirectSlotMsgElementA[x]

	CAN_A_YACP_CMD.messageObj.id 			= YACP_COMMAND_ID;
	CAN_A_YACP_CMD.messageObj.extended 		= 0;
	CAN_A_YACP_CMD.messageObj.length 		= 8;
	CAN_A_YACP_CMD.messageObj.remote 		= 0;
	CAN_A_YACP_CMD.ready 					= 0;
	CAN_A_YACP_CMD.read 					= 0;
	CAN_A_YACP_CMD.write 					= 0;

	// Option 2) Use the CAN RX callback for receiving all traffic
	//F_Abstr_CAN_InstallRxSltCall(ycap_can_recv_callback);

	yacp_can_msg.extended = 0;
	yacp_can_msg.length = 8;
	yacp_can_msg.remote = 0;
}

void yacp_can_send(uint32_t id, uint8_t* buf)
{
	yacp_can_msg.id = id;

	uint8_t i;
	for (i=0; i<8; i++)
		yacp_can_msg.data[i] = buf[i];

	F_Abstr_CAN_Transmit2Queue(CAN_CTRL_A, &yacp_can_msg);
}

void yacp_can_recv()
{
	// Polling style receive, call from the main loop periodically
	if (1 == F_Abstr_CAN_ReceiveDirect(&CAN_A_YACP_CMD, &yacp_can_msg_in))
	{
		handle_can(yacp_can_msg_in.id, yacp_can_msg_in.data);
	}
}

void ycap_can_recv_callback(CanControllerIdType channel, CANMsgElement_t *messageObj)
{
	if (channel == CAN_CTRL_A)
	{
		handle_can(messageObj->id, messageObj->data);
	}
}

// All EEPROM assume a start address of 0. Add an offset as required by your project if there is a specific
// EEPROM region you must use for storing cal.
uint8_t yacp_eeprom_load_byte(uint16_t addr)
{
	if (addr < (YACP_NVM_SIZE-1))
		return yacp_nvm[addr];
	else
		return 0;
}

void yacp_eeprom_store_byte(uint16_t addr, uint8_t val)
{
	if (addr < (YACP_NVM_SIZE-1))
		yacp_nvm[addr] = val;
}

void yacp_eeprom_persist()
{
	Ser_Mem_NVM_RAM2ROM();
}

void yacp_memcpy(void* s1, const void* s2, uint16_t n)
{
	uint16_t i;
	uint8_t* csrc = (uint8_t*)s2;
	uint8_t* cdest = (uint8_t*)s1;

	for (i=0; i<n; i++)
	{
		cdest[n-1-i] = csrc[i];
	}
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
