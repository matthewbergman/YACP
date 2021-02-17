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


// YACP Internal Functions
void load_defaults();
void load_settings();
void save_settings();
void handle_can(uint32_t id, uint8_t* buf);

#endif
