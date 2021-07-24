/*
 * yacp_driver_s32k144.cpp
 * Yet Another Calibration Protocol (YACP)
 * 
 * This is a driver for use with S32k1xx microcontrollers with the RTM v3.0.0 API.
 *
 * Requirements:
 * FlexCAN
 * FlexRAM EEEProm emulation
 * 
 * Matthew Bergman 2021
 * 
 * MIT license, all text above must be included in any redistribution.
 * See license.txt at the root of the repository for full license text.
 */

#include "yacp.h"
#include "yacp_api.h"

// Include the appropriate FlexNVM and FlexCAN headers for your project
#include "Flash1.h"
#include "canCom1.h"

// Define a TX and RX mailbox depending on which are available in your project
#define YACP_RX_MAILBOX (4UL)
#define YACP_TX_MAILBOX (5UL)

// It is assumed you have initialized this struct elsewhere, adjust the name as needed
extern flash_ssd_config_t flashSSDConfig;

/* Define receive buffer */
flexcan_msgbuff_t canMsgBuff;

flexcan_data_info_t dataInfo =
{
		.data_length = 8U,
		.msg_id_type = FLEXCAN_MSG_ID_STD,
		.enable_brs  = false,
		.fd_enable   = false,
		.fd_padding  = 0U
};

// All CAN functions assume INST_CANCOM1, change as needed
void yacp_can_init()
{
	/* Configure RX message buffer with index RX_MSG_ID and RX_MAILBOX */
	FLEXCAN_DRV_ConfigRxMb(INST_CANCOM1, YACP_RX_MAILBOX, &dataInfo, YACP_COMMAND_ID);

	/* Start receiving data in RX_MAILBOX. */
	FLEXCAN_DRV_Receive(INST_CANCOM1, YACP_RX_MAILBOX, &canMsgBuff);
}

void yacp_can_send(uint32_t id, uint8_t* buf)
{
	/* Configure TX message buffer with index TX_MSG_ID and TX_MAILBOX*/
	FLEXCAN_DRV_ConfigTxMb(INST_CANCOM1, YACP_TX_MAILBOX, &dataInfo, id);

	/* Execute send non-blocking */
	FLEXCAN_DRV_Send(INST_CANCOM1, YACP_TX_MAILBOX, &dataInfo, id, buf);
}

void yacp_can_recv()
{
	/* Wait until the previous FlexCAN receive is completed and then process message */
	if (FLEXCAN_DRV_GetTransferStatus(INST_CANCOM1, YACP_RX_MAILBOX) == STATUS_SUCCESS)
	{
		if (canMsgBuff.msgId == YACP_COMMAND_ID)
		{
			handle_can(canMsgBuff.msgId, canMsgBuff.data);
		}

		/* Start receiving data in RX_MAILBOX. */
		FLEXCAN_DRV_Receive(INST_CANCOM1, YACP_RX_MAILBOX, &canMsgBuff);
	}
}

// All EEPROM assume a start address of 0. Add an offset as required by your project if there is a specific
// EEPROM region you must use for storing cal.
uint8_t yacp_eeprom_load_byte(uint16_t addr)
{
	uint8_t* p_eeprom = (uint8_t*)flashSSDConfig.EERAMBase;
	return p_eeprom[addr];
}

void yacp_eeprom_store_byte(uint16_t addr, uint8_t val)
{
	uint8_t tmp = val;

	if (flashSSDConfig.EEESize != 0u)
	{
		FLASH_DRV_EEEWrite(&flashSSDConfig, flashSSDConfig.EERAMBase + addr, 1, &tmp);
	}
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
