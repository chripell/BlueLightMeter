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

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <termios.h>
#include <unistd.h>
#include <poll.h>
#include <time.h>

#include "buspirate.h"
#include "i2c.h"

#define LEN(X) (sizeof(X) - 1)
#define FINGERPRINT "BBIO1"
#define I2C_MODE "I2C1"
#define RETRIES 20

struct buspirate_s {
  int err;
  int fd;
  struct termios old_termios;
  int debug:1;
  int fast:1;
  unsigned char buf;
};

static int open_termios(struct buspirate_s *bp, char *dev) {
  struct termios new_termios;

  bp->err = 0;
  bp->fd = open(dev, O_RDWR | O_NOCTTY);
  if (bp->fd < 0) {
    fprintf(stderr, "error, counldn't open file %s\n", dev);
    return (bp->err = errno);
  }
  if (tcgetattr(bp->fd, &bp->old_termios) != 0) {
    fprintf(stderr, "tcgetattr(fd, &old_termios) failed: %s\n", strerror(errno));
    return (bp->err = errno);
  }
  memset(&new_termios, 0, sizeof(new_termios));
  new_termios.c_iflag = IGNPAR;
  new_termios.c_oflag = 0;
  new_termios.c_cflag = CS8 | CREAD | CLOCAL | HUPCL;
  new_termios.c_lflag = 0;
  new_termios.c_cc[VINTR]    = 0;
  new_termios.c_cc[VQUIT]    = 0;
  new_termios.c_cc[VERASE]   = 0;
  new_termios.c_cc[VKILL]    = 0;
  new_termios.c_cc[VEOF]     = 4;
  new_termios.c_cc[VTIME]    = 0;
  new_termios.c_cc[VMIN]     = 1;
  new_termios.c_cc[VSWTC]    = 0;
  new_termios.c_cc[VSTART]   = 0;
  new_termios.c_cc[VSTOP]    = 0;
  new_termios.c_cc[VSUSP]    = 0;
  new_termios.c_cc[VEOL]     = 0;
  new_termios.c_cc[VREPRINT] = 0;
  new_termios.c_cc[VDISCARD] = 0;
  new_termios.c_cc[VWERASE]  = 0;
  new_termios.c_cc[VLNEXT]   = 0;
  new_termios.c_cc[VEOL2]    = 0;

  if (cfsetispeed(&new_termios, B115200) != 0) {
    fprintf(stderr, "cfsetispeed(&new_termios, B115200) failed: %s\n", strerror(errno));
    return (bp->err = errno);
  }
  if (cfsetospeed(&new_termios, B115200) != 0) {
    fprintf(stderr, "cfsetospeed(&new_termios, B115200) failed: %s\n", strerror(errno));
    return (bp->err = errno);
  }
  if (tcsetattr(bp->fd, TCSANOW, &new_termios) != 0) {
    fprintf(stderr, "tcsetattr(fd, TCSANOW, &new_termios) failed: %s\n", strerror(errno));
    return (bp->err = errno);
  }
  return 0;
}

static int flush_input(struct buspirate_s *bp) {
  if (tcflush(bp->fd, TCIFLUSH))
    return (bp->err = errno);
  return 0;
}

static int read_n(struct buspirate_s * bp, unsigned char *b, int n, int tout_ms) {
  int i = 0, r;
  struct pollfd pfd = {
    .fd = bp->fd,
    .events = POLLIN,
  };

  while (i < n) {
    r = poll(&pfd, 1, tout_ms);
    if (r == 0)
      return (bp->err = ETIMEDOUT);
    else if (r < 0)
      return (bp->err = errno);
    r = read(bp->fd, &b[i], n - i);
    if (r < 0)
      return (bp->err = errno);
    i += r;
  }
  if (bp->debug) {
    printf("RX:");
    for(i = 0; i < n; i++)
      printf(" %02x", b[i]);
    printf("\n");
  }
  return 0;
}

static int write_n(struct buspirate_s * bp, unsigned char *b, int n) {
  int i = 0, r;

  while (i < n) {
    r = write(bp->fd, &b[i], n - i);
    if (r < 0)
      return (bp->err = errno);
    i += r;
  }
  if (bp->debug) {
    printf("TX:");
    for(i = 0; i < n; i++)
      printf(" %02x", b[i]);
    printf("\n");
  }
  return 0;
}

static void sleep_ms(int ms) {
  struct timespec ts = {
    .tv_sec = ms / 1000,
    .tv_nsec = (ms % 1000) * 1000000,
  };
  nanosleep(&ts, NULL);
}

struct buspirate_s *buspirate_init(char *port) {
  int i;
  struct buspirate_s *bp = calloc(1, sizeof(*bp));
  
  if (getenv("BUSPIRATE_DEBUG"))
    bp->debug = 1;
  if (open_termios(bp, port))
    goto error_exit;
  flush_input(bp);
  for(i = 0; i < RETRIES; i++) {
    unsigned char buf[LEN(FINGERPRINT)] = {};

    write_n(bp, (unsigned char *) "\000", 1);
    
    bp->err = 0;
    if (read_n(bp, buf, LEN(FINGERPRINT), 100) == 0) {
      if (!memcmp(buf, FINGERPRINT, LEN(FINGERPRINT)))
	break;
    }
  }
  if (i == RETRIES)
    bp->err = ENOENT;
 error_exit:
  return bp;
}

void buspirate_reset(struct buspirate_s *bp) {
  unsigned char buf[200];

  bp->err = 0;
  write_n(bp, (unsigned char *) "\x0f", 1);
  read_n(bp, buf, 200, 200);
}

void buspirate_free(struct buspirate_s *bp) {
  buspirate_reset(bp);
  flush_input(bp);
  tcsetattr(bp->fd, TCSANOW, &bp->old_termios);
  close(bp->fd);
  free(bp);
}

int buspirate_error(struct buspirate_s *bp) {
  return bp->err;
}

#define I2C_START_BIT 0x02
#define I2C_STOP_BIT 0x03
#define I2C_READ_BYTE 0x04
#define I2C_SEND_ACK 0x06
#define I2C_SEND_NACK 0x07

static unsigned char buspirate_aux(struct buspirate_s *bp, int bit) {
    unsigned char buf = bit;

    write_n(bp, &buf, 1);
    read_n(bp, &buf, 1, 100);
    return buf;
}

void buspirate_cfg_pins(struct buspirate_s *bp, int pins) {
  bp->err = 0;
  buspirate_aux(bp, 0x40 | pins);
}

void buspirate_set_speed(struct buspirate_s *bp, int speed) {
  bp->err = 0;
  buspirate_aux(bp, 0x60 | speed);
}

struct i2c_s *i2c_new(char *type, int speed) {
  struct buspirate_s *bp = buspirate_init(type);
  unsigned char buf[LEN(I2C_MODE)];

  if (bp->err)
    goto exit_i2c_new;
  write_n(bp, (unsigned char *) "\002", 1);
  if (read_n(bp, buf, LEN(I2C_MODE), 100) == 0) {
    if (memcmp(buf, I2C_MODE, LEN(I2C_MODE))) {
      /* Check if we are already in I2C mode */
      flush_input(bp);
      write_n(bp, (unsigned char *) "\001", 1);
      if (read_n(bp, buf, LEN(I2C_MODE), 100) == 0) {
	if (memcmp(buf, I2C_MODE, LEN(I2C_MODE))) {
	  bp->err = EINVAL;
	  goto exit_i2c_new;
	}
      } else {
	bp->err = ETIMEDOUT;
	goto exit_i2c_new;
      }
    }
  }
  else {
    bp->err = ETIMEDOUT;
    goto exit_i2c_new;
  }
  buspirate_cfg_pins(bp, BUSPIRATE_PINCFG_POWER|BUSPIRATE_PINCFG_PULLUPS);
  buspirate_set_speed(bp, speed);
  sleep_ms(200);
  bp->fast = 0;
 exit_i2c_new:
  return (struct i2c_s *) bp;
}

void i2c_free(struct i2c_s *i2c) {
  struct buspirate_s *bp = (struct buspirate_s *) i2c;
  unsigned char buf[LEN(FINGERPRINT)] = {};

  write_n(bp, (unsigned char *) "\000", 1);
  read_n(bp, buf, LEN(FINGERPRINT), 100);
  buspirate_free(bp);
}

int i2c_error(struct i2c_s *i2c) {
  struct buspirate_s *bp = (struct buspirate_s *) i2c;
  return buspirate_error(bp);
}

static void test_nack(struct buspirate_s *bp) {
  if (bp->buf)
    bp->err = ERR_NACK;
}

static void buspirate_bulk(struct buspirate_s *bp, unsigned char *pre,
			   unsigned char *data , int n) {
  unsigned char len = 0x10 | (n - 1 + (pre ? 1 : 0));
  int i;

  write_n(bp, &len, 1);
  test_nack(bp);
  read_n(bp, &bp->buf, 1, 100);
  if (pre) {
    write_n(bp, pre, 1);
    read_n(bp, &bp->buf, 1, 100);
    test_nack(bp);
  }
  if (n > 0) {
    write_n(bp, data, n);
    for(i = 0; i < (len & 0x0f); i++) {
      read_n(bp, &bp->buf, 1, 100);
      test_nack(bp);
    }
  }
}

static void i2c_cmd8(struct buspirate_s *bp, int addr,
		     unsigned char *tx_data, int m,
		     unsigned char *rx_data, int n) {
  unsigned char rx_buf[n + 1];
  unsigned char tx_buf[1 + 2 + 2 + 1 + m];
  int tx_len = 0;

  if (bp->debug) {
    printf("i2c_cmd8 %0x %d %d\n", addr, m, n);
  }
  tx_buf[0] = 8;
  if (tx_data) {
    tx_buf[1] = ((m + 1) >> 8) & 0xff;
    tx_buf[2] = (m + 1) & 0xff;
    memcpy(&tx_buf[6], tx_data, m);
    tx_len = 6 + m;
  } else {
    tx_buf[1] = 0;
    tx_buf[2] = 1;
    tx_len = 6;
  }
  tx_buf[3] = (n >> 8) & 0xff;
  tx_buf[4] = n & 0xff;
  tx_buf[5] = addr;
  if (write_n(bp, tx_buf, tx_len))
    return;
  if (read_n(bp, rx_buf, 1, 100))
    return;
  if (rx_buf[0] != 1) {
    bp->err = ERR_NACK;
    return;
  }
  if (n > 0)  {
    if (read_n(bp, &rx_buf[1], n, 100))
      return;
    if (rx_data)
      memcpy(rx_data, &rx_buf[1], n);
  }
}

void i2c_send(struct i2c_s *i2c, int addr, unsigned char *data, int n) {
  struct buspirate_s *bp = (struct buspirate_s *) i2c;
  unsigned char abuf = (addr << 1);

  bp->err = 0;
  if (bp->fast) {
    i2c_cmd8(bp, addr << 1, data, n, NULL, 0);
    return;
  }
  buspirate_aux(bp, I2C_START_BIT);
  buspirate_bulk(bp, &abuf, data, n);
  buspirate_aux(bp, I2C_STOP_BIT);
}

void i2c_cmd_recv(struct i2c_s *i2c, int addr, unsigned char cmd,
		  unsigned char *data, int n) {
  struct buspirate_s *bp = (struct buspirate_s *) i2c;
  unsigned char abuf = (addr << 1);
  unsigned char cbuf = cmd;
  int i;

  bp->err = 0;
  if (bp->fast) {
    i2c_cmd8(bp, (addr << 1), &cbuf, 1, data, n);
    return;
  }
  buspirate_aux(bp, I2C_START_BIT);
  buspirate_bulk(bp, &abuf, &cbuf, 1);
  buspirate_aux(bp, I2C_START_BIT);
  abuf |= 1;
  buspirate_bulk(bp, &abuf, NULL, 0);
  for (i = 0; i < n; i++) {
    data[i] = buspirate_aux(bp, I2C_READ_BYTE);
    if (i < n - 1)
      buspirate_aux(bp, I2C_SEND_ACK);
  }
  buspirate_aux(bp, I2C_SEND_NACK);
  buspirate_aux(bp, I2C_STOP_BIT);
}

void i2c_recv(struct i2c_s *i2c, int addr,
		  unsigned char *data, int n) {
  struct buspirate_s *bp = (struct buspirate_s *) i2c;
  unsigned char abuf = (addr << 1) | 1;
  int i;

  bp->err = 0;
  if (bp->fast) {
    i2c_cmd8(bp, (addr << 1) | 1, NULL, 0, data, n);
    return;
  }
  buspirate_aux(bp, I2C_START_BIT);
  buspirate_bulk(bp, &abuf, NULL, 0);
  for (i = 0; i < n; i++) {
    data[i] = buspirate_aux(bp, I2C_READ_BYTE);
    if (i < n - 1)
      buspirate_aux(bp, I2C_SEND_ACK);
  }
  buspirate_aux(bp, I2C_SEND_NACK);
  buspirate_aux(bp, I2C_STOP_BIT);
}

void i2c_pin(struct i2c_s *i2c, int aux, int cs) {
  struct buspirate_s *bp = (struct buspirate_s *) i2c;

  buspirate_cfg_pins(bp, BUSPIRATE_PINCFG_POWER|
		     BUSPIRATE_PINCFG_PULLUPS|
		     (aux ? BUSPIRATE_PINCFG_AUX : 0)|
		     (cs ? BUSPIRATE_PINCFG_CS: 0));
}

void i2c_fast(struct i2c_s *i2c, int fast) {
  struct buspirate_s *bp = (struct buspirate_s *) i2c;

  bp->fast = fast > 0;
}
