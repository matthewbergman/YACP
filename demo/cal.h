#ifndef YACP_CAL_H_
#define YACP_CAL_H_

#include "yacp.h"

// Struct defs

typedef struct __attribute__((packed)) cal_measurements
{
  uint16_t test_var; // 2
  uint8_t cal_ver; // 3
  uint32_t test_var2; // 7
  uint8_t output_status; // 8
  uint16_t counter; // 10
} cal_measurements;

typedef struct __attribute__((packed)) cal_settings
{
  uint8_t output_selector; // 1
  uint32_t test3; // 5
  uint8_t test1; // 6
  uint16_t test2; // 8
} cal_settings;

typedef struct __attribute__((packed)) cal_overrides
{
  cal_override output_override;   // 5
  cal_override output_override2;  // 10
  cal_override output_override3;  // 15
  cal_override output_override4;  // 20
} cal_overrides;

typedef struct calibration
{
  cal_measurements measurements;
  cal_settings settings;
  cal_overrides overrides;
} calibration;

#endif
