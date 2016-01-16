
ifndef RFDUINO
$(error RFDUINO is not set. Set to the directory wher RFDUINO BSP is, probably $$HOME/.arduino15/packages/RFduino/hardware/RFduino/2.3.1/)
endif

ifndef RFDUINO_PORT
$(error RFDUINO_PORT is not set. Set to the serial port for RFDUINO, probably /dev/ttyUSB0)
endif

CCPREFIX=${RFDUINO}/../../../tools/arm-none-eabi-gcc/4.8.3-2014q1/bin/
CXX=${CCPREFIX}arm-none-eabi-g++
CC=${CCPREFIX}arm-none-eabi-gcc
OBJCOPY=${CCPREFIX}arm-none-eabi-objcopy

VPATH=${RFDUINO}/cores/arduino:${RFDUINO}/variants/RFduino:${RFDUINO}/libraries/RFduinoBLE:${RFDUINO}/libraries/Wire

CFLAGS=-g -Os -w -ffunction-sections -fdata-sections -fno-rtti -fno-exceptions \
	-fno-builtin -mcpu=cortex-m0 -DF_CPU=16000000 -DARDUINO=10605 -mthumb \
	-D__RFduino__ -I${RFDUINO}/cores/arduino -I${RFDUINO}/variants/RFduino \
	-I${RFDUINO}/system/RFduino -I${RFDUINO}/system/RFduino/include \
	-I${RFDUINO}/system/CMSIS/CMSIS/Include -Wall \
	-I${RFDUINO}/libraries/RFduinoBLE \
	-I${RFDUINO}/libraries/Wire
ifdef DEBUG
CFLAGS+=-DADEBUG
endif
CXXFLAGS=${CFLAGS}

CORE_SRCS=hooks.c itoa.c Memory.c syscalls.c WInterrupts.c wiring_analog.c wiring.c \
	wiring_digital.c wiring_shift.c main.cpp Print.cpp RingBuffer.cpp Stream.cpp \
	Tone.cpp UARTClass.cpp wiring_pulse.cpp WMath.cpp WString.cpp variant.cpp \
	RFduinoBLE.cpp Wire.cpp

CORE_OBJS=$(subst .c,.o,$(subst .cpp,.o,${CORE_SRCS}))

OBJS=$(subst .c,.o,$(subst .cpp,.o,${SRCS}))

.PHONY: build
build: out.hex

out.hex: ${CORE_OBJS} ${OBJS}
	${CXX} -Wl,--gc-sections --specs=nano.specs -mcpu=cortex-m0 -mthumb -D__RFduino__ \
	-T${RFDUINO}/variants/RFduino/linker_scripts/gcc/RFduino.ld \
	-Wl,-Map,out.map -Wl,--cref -o out.elf -Wl,--warn-common \
	-Wl,--warn-section-align -Wl,--start-group ${CORE_OBJS} ${OBJS} \
	${RFDUINO}/variants/RFduino/libRFduinoSystem.a \
	${RFDUINO}/variants/RFduino/libRFduino.a \
	${RFDUINO}/variants/RFduino/libRFduinoBLE.a \
	${RFDUINO}/variants/RFduino/libRFduinoGZLL.a \
	-Wl,--end-group 
	${OBJCOPY} -O ihex out.elf out.hex

.PHONY: download
download: out.hex
	${RFDUINO}/../../../tools/RFDLoader/1.5/RFDLoader_linux ${RFDUINO_PORT} out.hex

.PHONY: clean
clean:
	rm -f *.o *~ *.d out.elf out.hex out.map

