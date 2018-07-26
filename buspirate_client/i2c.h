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

#ifndef _I2C_H_
#define _I2C_H_ 1

struct i2c_s;

#define I2C_SPEED_400KHZ 0x03
#define I2C_SPEED_100KHZ 0x02
#define I2C_SPEED_50KHZ 0x01
#define I2C_SPEED_5KHZ 0x00

#define I2C_USE_CS 0x10  
#define I2C_USE_AUX 0x20
#define I2C_PIN_LOW 0x00
#define I2C_PIN_HIGH 0x01
#define I2C_PIN_HIZ 0x02
#define I2C_PIN_READ 0x03

#define ERR_NACK 100

struct i2c_s *i2c_new(char *type, int speed);
void i2c_free(struct i2c_s *i2c);
int i2c_error(struct i2c_s *i2c);
void i2c_send(struct i2c_s *i2c, int addr, unsigned char *data, int n);
void i2c_cmd_recv(struct i2c_s *i2c, int addr, unsigned char cmd,
		  unsigned char *data, int n);
void i2c_pin(struct i2c_s *i2c, int aux, int cs);
void i2c_fast(struct i2c_s *i2c, int fast);
#endif
