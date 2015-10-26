
SRCS=buspirate.c test.c tsl2561sparkfun.c
OBJS=$(subst .c,.o,${SRCS})

CFLAGS=-Wall -g

LDFLAGS=-lm

all: tester depend

tester: ${OBJS}
	${CC} $(LDFLAGS) -o $@ $^

.PHONY: clean
clean:
	rm -f *~ *.o tester depend

depend:
	$(CC) -M ${SRCS} > depend

-include depend
