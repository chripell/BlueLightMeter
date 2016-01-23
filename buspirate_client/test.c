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

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/select.h>

#include "buspirate.h"
#include "i2c.h"
#include "tsl2561sparkfun.h"

struct accu_s {
  double min;
  double max;
  double med;
  unsigned long n;
};

static void accu_zero(struct accu_s *a) {
  a->min = 1e10;
  a->max = -1.e10;
  a->med = 0.0;
  a->n = 0;
}

static void accu_compute(struct accu_s *a) {
  a->med /= a->n;
}

static void accu_add(struct accu_s *a, double val) {
    a->n += 1;
    a->med += val;
    if (val < a->min) a->min = val;
    if (val > a->max) a->max = val;
}

static int kbhit() {
    struct timeval tv = { 0L, 0L };
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(0, &fds);
    return select(1, &fds, NULL, NULL, &tv);
}

static int test_bp(int argc, char *argv[]) {
  struct buspirate_s *bp;
  int err;

  if (argc != 2) {
    printf("Usage: %s [tty port]\n", argv[0]);
    return 1;
  }
  bp = buspirate_init(argv[1]);
  if ((err = buspirate_error(bp))) {
    printf("ERROR: %d(%s)\n", err, strerror(err));
    return 1;
  }
  puts("OK");
  buspirate_free(bp);
  return 0;
}

static int test_tsl2561(int argc, char *argv[]) {
  struct i2c_s *i2c;
  struct tsl2561_s *tsl;
  int err, auto_mode = 0;
  struct accu_s alux, ach1, ach2;
  struct timespec last;
  
  if (argc != 5 && argc != 4) {
    printf("Usage:\n"
	   " %s [tty port] [addr] [hi gain] [mode]\n"
	   " %s [tty port] [addr] [profile]\n",
	   argv[0], argv[0]);
    return 1;
  }
  if (argc == 4)
    auto_mode = 1;
  i2c = i2c_new(argv[1], I2C_SPEED_400KHZ);
  if ((err = i2c_error(i2c))) {
    printf("ERROR: %d(%s)\n", err, strerror(err));
    return 1;
  }
  tsl = tsl2561_new(i2c, strtoul(argv[2], NULL, 0),
		    auto_mode ? strtoul(argv[3], NULL, 0) : TSL2561_PROFILE_NOAUTO);
  if ((err = i2c_error(i2c))) {
    printf("ERROR: %d\n", err);
  }
  if (!auto_mode)
    tsl2561_set_mode(tsl, strtoul(argv[3], NULL, 0), strtoul(argv[4], NULL, 0));
  printf("Press Enter to stop\n");
  
  accu_zero(&alux);
  accu_zero(&ach1);
  accu_zero(&ach2);
  clock_gettime(CLOCK_MONOTONIC, &last);
  while (!kbhit()) {
    struct timespec now;
    double delta;
    int ch1, ch2;
    double lux;

    lux = tsl2561_lux(tsl, &ch1, &ch2);
    accu_add(&alux, lux);
    accu_add(&ach1, ch1);
    accu_add(&ach2, ch2);
    clock_gettime(CLOCK_MONOTONIC, &now);
    delta = now.tv_sec - last.tv_sec + (now.tv_nsec - last.tv_nsec) / 1e9;
    if (delta > 1.0) {
      accu_compute(&alux);
      accu_compute(&ach1);
      accu_compute(&ach2);
      printf("%15.6f\t%15.6f\t%15.6f\t(%5.0f/%5.0f/%5.0f)\t(%5.0f/%5.0f/%5.0f)",
	     alux.min, alux.med, alux.max,
	     ach1.min, ach1.med, ach1.max,
	     ach2.min, ach2.med, ach2.max);
      if (auto_mode) {
	int hi_gain, mode;
	int cur = tsl2561_pars(tsl, &hi_gain, &mode);

	printf("\t[%d(%d,%d)]", cur, hi_gain, mode);
      }
      printf("\n");
      accu_zero(&alux);
      accu_zero(&ach1);
      accu_zero(&ach2);
      last = now;
    }
  }
  tsl2561_free(tsl);
  i2c_free(i2c);
  return 0;
}

struct cmd_s {
  char *cmd;
  int (*f) (int argc, char *argv[]);
} cmds[] = {
  {"buspirate", test_bp},
  {"tsl2651", test_tsl2561},
  {NULL, NULL},
};

int main(int argc, char *argv[]) {
  struct cmd_s *c = cmds;

  if (argc < 2) {
    printf("Usage: %s [test] [params....]\n", argv[0]);
    return 1;
  }
  
  while(c->cmd) {
    if (!strcmp(c->cmd, argv[1])) {
      return c->f(argc - 1, &argv[1]);
    }
    c++;
  }
  printf("Unknown command. Available:\n");
  c = cmds;
  while(c->cmd)
    printf("%s\n", c++->cmd);
  return 1;
}
