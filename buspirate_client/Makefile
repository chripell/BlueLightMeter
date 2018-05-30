
SRCS=buspirate.c test.c tsl2561sparkfun.c
OBJS=$(subst .c,.o,${SRCS})

CFLAGS=-Wall -g

LDFLAGS=-lm

all: depend tester libbuspirate.so

tester: ${OBJS}
	${CC} $(LDFLAGS) -o $@ $^

libbuspirate.so: buspirate.c
	${CC} $(LDFLAGS)  -fPIC -c $^
	${LD} -shared  -o $@ buspirate.o

.PHONY: clean
clean:
	rm -f *~ *.o tester depend *.so

depend:
	$(CC) -M ${SRCS} > depend

-include depend
