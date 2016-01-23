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

#ifndef _BUSPIRATE_H_
#define _BUSPIRATE_H_ 1

#define	BUSPIRATE_PINCFG_POWER 0x8
#define	BUSPIRATE_PINCFG_PULLUPS 0x4
#define	BUSPIRATE_PINCFG_AUX 0x2
#define	BUSPIRATE_PINCFG_CS 0x1

struct buspirate_s;

struct buspirate_s *buspirate_init(char *port);
void buspirate_free(struct buspirate_s *bp);
int buspirate_error(struct buspirate_s *bp);
void buspirate_cfg_pins(struct buspirate_s *bp, int pins);
void buspirate_set_speed(struct buspirate_s *bp, int speed);
void buspirate_reset(struct buspirate_s *bp);

#endif /* _BUSPIRATE_H_ */
