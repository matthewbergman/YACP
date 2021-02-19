#ifndef YACP_CAL_H_
#define YACP_CAL_H_

#include "yacp_api.h"

#define CAL_REVISION 4

typedef struct __attribute__((packed)) cal_measurements
{
	uint8_t var_u8;
	uint16_t var_u16;
	uint32_t var_u32;
	int8_t var_i8;
	int16_t var_i16;
	int32_t var_i32;
	float var_f;
	uint8_t counter;
} cal_measurements;

typedef struct __attribute__((packed)) cal_settings
{
	uint8_t device_id;
	uint8_t revision;
	uint8_t setting_u8;
	uint16_t setting_u16;
	uint32_t setting_u32;
	int8_t setting_i8;
	int16_t setting_i16;
	int32_t setting_i32;
	float setting_f;
} cal_settings;

typedef struct __attribute__((packed)) cal_overrides
{
	cal_override override_u8;
	cal_override override_u16;
	cal_override override_u32;
	cal_override override_i8;
	cal_override overridei_16;
	cal_override override_i32;
	cal_override override_f;
} cal_overrides;

typedef struct calibration
{
	cal_measurements measurements;
	cal_settings settings;
	cal_overrides overrides;
} calibration;

#endif
