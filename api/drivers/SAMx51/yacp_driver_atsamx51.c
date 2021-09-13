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

/*
 * Hamony 3 setup
 * 
 * NVMControl:
 * Leave as stock.
 * 
 * System -> Device & Project Config -> ATSAMxxxx Device Configuration -> Fuse Settings
 * Disable Generate Fuse Settingss (done in bootloader)
 * 
 * CANx:
 * Set up a filter and FIFO for 0x100
 *  
 */

#include "yacp.h"
#include "yacp_api.h"
#include "canbus.h"

#include <string.h>

// PSZ = 1, SBLK = 1 = 1024 bytes
#define EEPROM_SIZE 1024

/* Define a pointer to access SmartEEPROM as bytes */
uint8_t *SmartEEPROM8       = (uint8_t *)SEEPROM_ADDR;
/* Define a pointer to access SmartEEPROM as words (32-bits) */
uint32_t *SmartEEPROM32     = (uint32_t *)SEEPROM_ADDR;

uint32_t yacp_can_recv_id;
uint8_t yacp_can_recv_len;
uint8_t yacp_can_recv_data[8];
CAN_MSG_RX_FRAME_ATTRIBUTE yacp_can_rx_attr;

void yacp_can_init()
{
}

void yacp_can_send(uint32_t id, uint8_t* buf)
{
    CAN0_MessageTransmit(id, 8, buf, CAN_MODE_NORMAL, CAN_MSG_ATTR_TX_FIFO_DATA_FRAME);
}

void yacp_can_recv()
{
    if (CAN0_MessageReceive(&yacp_can_recv_id, &yacp_can_recv_len, yacp_can_recv_data, NULL, CAN_MSG_ATTR_RX_FIFO0, &yacp_can_rx_attr))
    {
        if (yacp_can_recv_id == YACP_COMMAND_ID)
        {
            yacp_handle_can(yacp_can_recv_id, yacp_can_recv_data);
        }
    }
}

// All EEPROM assume a start address of 0. Add an offset as required by your project if there is a specific
// EEPROM region you must use for storing cal.
uint8_t yacp_eeprom_load_byte(uint16_t addr)
{
    while (NVMCTRL_SmartEEPROM_IsBusy()) {}
    
	return SmartEEPROM8[addr];
}

void yacp_eeprom_store_byte(uint16_t addr, uint8_t val)
{
    while (NVMCTRL_SmartEEPROM_IsBusy()) {}
    
    SmartEEPROM8[addr] = val;
}

void yacp_eeprom_persist()
{
    // NVM writes are handled in the background
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
