
#include <time.h>
#include <stdlib.h>
#include <math.h>
#include <unistd.h>
#include <stdio.h>

#include "tsl2561sparkfun.h"
#include "i2c.h"

struct tsl2561_s {
  struct i2c_s *i2c;
  int addr:8;
  unsigned int hi_gain:1;
  unsigned int mode:2;
  struct timespec tick;
  unsigned int profile:8;
  unsigned int cur:3;
  struct timespec modified;
};

#define DEFAULT_MIN 100
#define DEFAULT_MAX 5000

struct tsl2561_parameters_s {
  unsigned int hi_gain:1;
  unsigned int mode:2;
};

struct tsl2561_profile_s {
  int min;
  int max;
  struct tsl2561_parameters_s pars[6];
  int n;
} profiles[] = {
  {},
  {DEFAULT_MIN, DEFAULT_MAX, {{0,0},{0,1},{1,0},{0,2},{1,1},{1,2}}, 6}, /* TSL2561_PROFILE_ALL */
  {DEFAULT_MIN, DEFAULT_MAX, {{0,0},{1,0},{1,1},{1,2}}, 4}, /* TSL2561_PROFILE_FAST */
  {DEFAULT_MIN, DEFAULT_MAX, {{0,0},{0,1},{0,2},{1,2}}, 4}, /* TSL2561_PROFILE_LOGAIN */
};

static unsigned char tsl2561_read_reg(struct tsl2561_s *tsl, int reg) {
  unsigned char ret;
  
  i2c_cmd_recv(tsl->i2c, tsl->addr, 0x80 | reg, &ret, 1);
  //printf("R %02x = %02x\n", reg, ret);
  return ret;
}

static void tsl2561_write_reg(struct tsl2561_s *tsl, int reg, unsigned char val) {
  unsigned char data[] = { 0x80 | reg, val};
  
  //printf("W %02x = %02x\n", reg, val);
  i2c_send(tsl->i2c, tsl->addr, data, 2);
}

struct tsl2561_s *tsl2561_new(struct i2c_s *i2c, int addr, int profile) {
  struct tsl2561_s *tsl = calloc(1, sizeof(*tsl));

  tsl->i2c = i2c;
  tsl->addr = addr;
  tsl->profile = profile;
  usleep(200000);
  tsl2561_write_reg(tsl, 0, 0x3);
  if (profile) {
    tsl->cur = 0;
    clock_gettime(CLOCK_MONOTONIC, &tsl->modified);
    tsl2561_set_mode(tsl, profiles[tsl->profile].pars[tsl->cur].hi_gain,
		     profiles[tsl->profile].pars[tsl->cur].mode);
  }
  return tsl;
}

void tsl2561_free(struct tsl2561_s *tsl) {
  tsl2561_write_reg(tsl, 0, 0);
  free(tsl);
}

void tsl2561_set_mode(struct tsl2561_s *tsl, int hi_gain, int mode) {
  tsl->mode = mode;
  tsl->hi_gain = hi_gain;
  tsl2561_write_reg(tsl, 0x01, (tsl->hi_gain << 4) | tsl->mode);
}

void tsl2561_manual_start(struct tsl2561_s *tsl) {
  tsl->mode = TSL2561_MANUAL;
  tsl2561_write_reg(tsl, 0x01, (tsl->hi_gain << 4) | tsl->mode | (1 << 3));
  clock_gettime(CLOCK_MONOTONIC, &tsl->tick);
}

void tsl2561_manual_stop(struct tsl2561_s *tsl) {
  struct timespec now;
  
  tsl2561_write_reg(tsl, 0x01, (tsl->hi_gain << 4) | tsl->mode);
  clock_gettime(CLOCK_MONOTONIC, &now);
  tsl->tick.tv_sec = now.tv_sec - tsl->tick.tv_sec;
  tsl->tick.tv_nsec = now.tv_nsec - tsl->tick.tv_nsec;
  while (tsl->tick.tv_nsec < 0) {
    tsl->tick.tv_nsec += 1000000000;
    tsl->tick.tv_sec -= 1;
  }
}

double tsl2561_lux(struct tsl2561_s *tsl, int *pch0, int *pch1) {
  double ratio, d0, d1, ms, lux = 0.0;
  int ch0 = tsl2561_read_reg(tsl, 0xc) + tsl2561_read_reg(tsl, 0xd) * 256;
  int ch1 = tsl2561_read_reg(tsl, 0xe) + tsl2561_read_reg(tsl, 0xf) * 256;
  struct timespec now;
  unsigned long delta;
  
  if (pch0) *pch0 = ch0;
  if (pch1) *pch1 = ch1;

  switch(tsl->mode) {
  case TSL2561_13_7MS:
    ms = 13.7;
    break;
  case TSL2561_101MS:
    ms = 101.0;
    break;
  case TSL2561_402MS:
    ms = 402.0;
    break;
  default:
    ms = tsl->tick.tv_sec * 1000.0 + tsl->tick.tv_nsec / 1000000.0;
  }
  
  // Determine if either sensor saturated (0xFFFF)
  // If so, abandon ship (calculation will not be accurate)
  if ((ch0 == 0xFFFF) || (ch1 == 0xFFFF)) {
    lux = -1.0;
    goto done_lux;
  }
  if ((ch0 == 0) || (ch1 == 0)) {
    lux = 0.0;
    goto done_lux;
  }
  // Convert from unsigned integer to floating point
  d0 = ch0; d1 = ch1;
  // We will need the ratio for subsequent calculations
  ratio = d1 / d0;
  // Normalize for integration time
  d0 *= (402.0/ms);
  d1 *= (402.0/ms);
  // Normalize for gain
  if (!tsl->hi_gain) {
    d0 *= 16;
    d1 *= 16;
  }
  // Determine lux per datasheet equations:
  if (ratio < 0.5) {
    lux = 0.0304 * d0 - 0.062 * d0 * pow(ratio,1.4);
    goto done_lux;
  }
  if (ratio < 0.61) {
    lux = 0.0224 * d0 - 0.031 * d1;
    goto done_lux;
  }
  if (ratio < 0.80) {
    lux = 0.0128 * d0 - 0.0153 * d1;
    goto done_lux;
  }
  if (ratio < 1.30) {
    lux = 0.00146 * d0 - 0.00112 * d1;
    goto done_lux;
  }
  lux = 0.0;

 done_lux:
  /* always wait a second to allow to settle to new parameters. */
  clock_gettime(CLOCK_MONOTONIC, &now);
  delta = (now.tv_sec - tsl->modified.tv_sec) * 1000 +
    (now.tv_nsec - tsl->modified.tv_nsec) / 1000000;
  if (tsl->profile && delta > 1000 ) {
    struct tsl2561_profile_s *p = &profiles[tsl->profile];
    int changed;
      
    if ((ch0 < p->min || ch1 < p->min) && tsl->cur < (p->n - 1)) {
      tsl->cur += 1;
      changed = 1;
    }
    else if ((ch0 > p->max || ch1 > p->max) && tsl->cur > 0) {
      tsl->cur -= 1;
      changed = 1;
    }
    if (changed) {
      tsl2561_set_mode(tsl, p->pars[tsl->cur].hi_gain, p->pars[tsl->cur].mode);
      tsl->modified = now;
    }
  }
  return lux;
}

int tsl2561_pars(struct tsl2561_s *tsl, int *hi_gain, int *mode) {
  struct tsl2561_profile_s *p = &profiles[tsl->profile];

  if (hi_gain)
    *hi_gain = p->pars[tsl->cur].hi_gain;
  if (mode)
    *mode = p->pars[tsl->cur].mode;
  return tsl->cur;
}
  
