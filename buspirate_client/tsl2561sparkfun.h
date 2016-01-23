/*
Copyright 2016 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

#ifndef _TSL2561SPARKFUN_H
#define _TSL2561SPARKFUN_H 1

#define TSL2561_13_7MS 0
#define TSL2561_101MS 1
#define TSL2561_402MS 2
#define TSL2561_MANUAL 3

#include "i2c.h"

#define TSL2561_PROFILE_NOAUTO 0
#define TSL2561_PROFILE_ALL 1
#define TSL2561_PROFILE_FAST 2
#define TSL2561_PROFILE_LOGAIN 3

struct tsl2561_s *tsl2561_new(struct i2c_s *i2c, int addr, int profile);
void tsl2561_free(struct tsl2561_s *tsl);
void tsl2561_set_mode(struct tsl2561_s *tsl, int hi_gain, int mode);
void tsl2561_manual_start(struct tsl2561_s *tsl);
void tsl2561_manual_stop(struct tsl2561_s *tsl);
double tsl2561_lux(struct tsl2561_s *tsl, int *pch1, int *pch2);
int tsl2561_pars(struct tsl2561_s *tsl, int *hi_gain, int *mode);

#endif /* _TSL2561SPARKFUN_H */
