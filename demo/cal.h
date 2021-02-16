#ifndef YACP_CAL_H_
#define YACP_CAL_H_

#include "yacp.h"

typedef struct __attribute__((packed)) cal_measurements
{
	uint16_t test_var;
	uint8_t cal_ver;
	uint32_t test_var2;
	uint8_t output_status;
	uint16_t counter;
} cal_measurements;

typedef struct __attribute__((packed)) cal_settings
{
	uint8_t build_number;
	uint8_t output_selector;
	uint32_t test3;
	uint8_t test1;
	uint16_t test2;
} cal_settings;

typedef struct __attribute__((packed)) cal_overrides
{
	cal_override output_override;
	cal_override output_override2;
	cal_override output_override3;
	cal_override output_override4;
} cal_overrides;

typedef struct calibration
{
	cal_measurements measurements;
	cal_settings settings;
	cal_overrides overrides;
} calibration;

#endif
