#ifndef _I2C_H_
#define _I2C_H_ 1

struct i2c_s;

#define I2C_SPEED_400KHZ 0x03
#define I2C_SPEED_100KHZ 0x02
#define I2C_SPEED_50KHZ 0x01
#define I2C_SPEED_5KHZ 0x00

#define ERR_NACK 100

struct i2c_s *i2c_new(char *type, int speed);
void i2c_free(struct i2c_s *i2c);
int i2c_error(struct i2c_s *i2c);
void i2c_send(struct i2c_s *i2c, int addr, unsigned char *data, int n);
void i2c_cmd_recv(struct i2c_s *i2c, int addr, unsigned char cmd,
		  unsigned char *data, int n);
#endif
