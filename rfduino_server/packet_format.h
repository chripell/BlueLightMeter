/*
Copyright 2016 Google Inc. All rights reserved.

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

#ifndef _PACKET_FORMAT_H_
#define _PACKET_FORMAT_H_ 1

#define HIGAIN (1<<4)
#define T_13_7MS 0
#define T_101MS 1
#define T_402MS 2
#define T_MANUAL 3

struct blm_config {
  uint8_t mode;
  uint8_t time_ms_lsb;
  uint8_t time_ms_msb;
} __attribute__((packed));

struct blm_update {
  uint8_t ver;
  uint8_t run;
  uint8_t ch0_lsb;
  uint8_t ch0_msb;
  uint8_t ch1_lsb;
  uint8_t ch1_msb;
  struct blm_config conf;
} __attribute__((packed));

#endif	/* _PACKET_FORMAT_H_ */
