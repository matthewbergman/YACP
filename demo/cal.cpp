#include "cal.h"

calibration cal;

void load_defaults()
{
	cal.settings.device_id = 1;
	cal.settings.revision = 3;
	cal.settings.output_selector = 0;
	cal.settings.test3 = 3;
	cal.settings.test1 = 2;
	cal.settings.test2 = 1.5;
}
