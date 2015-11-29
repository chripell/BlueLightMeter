
#include "RFduinoBLE.h"
#include "Wire.h"
#include "variant.h"

#include "packet_format.h"

extern "C" {
  void setup(void);
  void loop(void);
}

#define TSL_ADDR 0x39

#define CONNECTED (1<<0)
#define NEW_CONFIG (1<<1)

static volatile uint8_t status = NEW_CONFIG;
static struct blm_update update = {
 ver: 0x11,
};

void setup() {
  update.conf.mode = T_402MS;
#ifdef ADEBUG
  Serial.begin(9600);
#endif
  Wire.begin();
  RFduinoBLE.advertisementData = "BlueLightMeter";
  RFduinoBLE.advertisementInterval = 500;
  RFduinoBLE.begin();
}

void RFduinoBLE_onConnect()
{
  status |= CONNECTED;
}

void RFduinoBLE_onDisconnect()
{
  status &= ~CONNECTED;
}

void RFduinoBLE_onReceive(char *data, int len)
{
  memcpy(&update.conf, data, sizeof(struct blm_config));
  status |= NEW_CONFIG;
}

static uint8_t tsl_read(uint8_t addr, uint8_t reg) {
  uint8_t ret = 0xff;
  
  Wire.beginTransmission(addr);
  Wire.write(byte(reg | 0x80));
  Wire.endTransmission(false);
  Wire.requestFrom(addr, byte(1));
  if (Wire.available() > 0)
    ret = Wire.read();
  return ret;
}

static void tsl_write(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(byte(reg | 0x80));
  Wire.write(byte(val));
  Wire.endTransmission();
}

void loop() {
  if (status & CONNECTED) {
    uint8_t conf = 0;

    // power on
    tsl_write(TSL_ADDR, 0, 3);
    status |= NEW_CONFIG;
#ifdef ADEBUG
    Serial.println("Power ON");
#endif
    while (status & CONNECTED) {
      unsigned short wait_time;
      
      if (status & NEW_CONFIG) {
#ifdef ADEBUG
	Serial.println("Reconfig");
#endif
	status &= ~NEW_CONFIG;
	conf = update.conf.mode;
#ifdef ADEBUG
	Serial.println(conf);
#endif
	tsl_write(TSL_ADDR, 1, conf);
	if ((conf & 0x3) == T_13_7MS)
	  wait_time = 14;
	else if ((conf & 0x3) == T_101MS)
	  wait_time = 101;
	else if ((conf & 0x3) == T_402MS)
	  wait_time = 402;
	else
	  wait_time = update.conf.time_ms_lsb + update.conf.time_ms_msb * 256;
#ifdef ADEBUG
	Serial.println(wait_time);
#endif
      }
      if ((conf & 0x3) == T_MANUAL)
	tsl_write(TSL_ADDR, 1, conf | (1<<3));
      RFduino_ULPDelay(wait_time);
      if ((conf & 0x3) == T_MANUAL)
	tsl_write(TSL_ADDR, 1, conf);
      update.ch0_lsb = tsl_read(TSL_ADDR, 0xc);
      update.ch0_msb = tsl_read(TSL_ADDR, 0xd);
      update.ch1_lsb = tsl_read(TSL_ADDR, 0xe);
      update.ch1_msb = tsl_read(TSL_ADDR, 0xf);
      RFduinoBLE.send((char *) &update, sizeof(update));
      update.run++;
    }
    // power off
    tsl_write(TSL_ADDR, 0, 0);
#ifdef ADEBUG
    Serial.println("Power OFF");
#endif
  }
  else {
    RFduino_ULPDelay(SECONDS(1));
#ifdef ADEBUG
    Serial.println("IDLE");
#endif
  }

  // get a cpu temperature sample
  // degrees c (-198.00 to +260.00)
  // degrees f (-128.00 to +127.00)
  float temp = RFduino_temperature(CELSIUS);

  // send the sample to the iPhone
  RFduinoBLE.sendFloat(temp);

  //Serial.print("T: ");
  //Serial.print(mode);
  //Serial.print(" ");
  //Serial.println(temp);
}
