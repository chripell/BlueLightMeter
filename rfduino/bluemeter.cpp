
#include "RFduinoBLE.h"
#include "variant.h"

extern "C" {
  void setup(void);
  void loop(void);
}

void setup() {
  // Open serial communications and wait for port to open:
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for Leonardo only
  }

  // this is the data we want to appear in the advertisement
  // (if the deviceName and advertisementData are too long to fix into the 31 byte
  // ble advertisement packet, then the advertisementData is truncated first down to
  // a single byte, then it will truncate the deviceName)
  RFduinoBLE.advertisementData = "temp";

  // start the BLE stack
  RFduinoBLE.begin();
}

int mode = 0;

void RFduinoBLE_onConnect()
{
  mode = 1;
}

void RFduinoBLE_onDisconnect()
{
  mode = 2;
}

void RFduinoBLE_onReceive(char *data, int len)
{
  mode = 3;
}


void loop() {
  // sample once per second
  RFduino_ULPDelay( SECONDS(1) );
  //RFduino_ULPDelay( INFINITE );

  // get a cpu temperature sample
  // degrees c (-198.00 to +260.00)
  // degrees f (-128.00 to +127.00)
  float temp = RFduino_temperature(CELSIUS);

  // send the sample to the iPhone
  RFduinoBLE.sendFloat(temp);

  Serial.print("T: ");
  Serial.print(mode);
  Serial.print(" ");
  Serial.println(temp);
}
