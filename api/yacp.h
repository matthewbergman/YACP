/*
 * yacp.h
 * Yet Another Calibration Protocol (YACP)
 * 
 * This is the main definition of the YACP protocol.
 * 
 * Matthew Bergman 2021
 * 
 * MIT license, all text above must be included in any redistribution.
 * See license.txt at the root of the repository for full license text.
 */

#ifndef YACP_H_
#define YACP_H_

#include <stdint.h>

#define YACP_UPDATE_ID 0x101

#define CAL_UPDATE_SETTING 0
#define CAL_READ_SETTING 1
#define CAL_OVERRIDE_ON 2
#define CAL_OVERRIDE_OFF 3
#define CAL_READ_OVERRIDE 4
#define CAL_READ_MEASUREMENT 5
#define CAL_SAVE_SETTINGS 6
#define CAL_HELLO 7
#define CAL_ACK 8

#define EEPROM_CRC_OFFSET 0
#define EEPROM_SETTINGS_OFFSET 4

// YACP Internal Functions
void load_defaults();
void load_settings();
void save_settings();

#endif
