#ifndef _BUSPIRATE_H_
#define _BUSPIRATE_H_ 1

#define	BUSPIRATE_PINCFG_POWER 0x8
#define	BUSPIRATE_PINCFG_PULLUPS 0x4
#define	BUSPIRATE_PINCFG_AUX 0x2
#define	BUSPIRATE_PINCFG_CS 0x1

struct buspirate_s;

struct buspirate_s *buspirate_init(char *port);
void buspirate_free(struct buspirate_s *bp);
int buspirate_error(struct buspirate_s *bp);
void buspirate_cfg_pins(struct buspirate_s *bp, int pins);
void buspirate_set_speed(struct buspirate_s *bp, int speed);
void buspirate_reset(struct buspirate_s *bp);

#endif /* _BUSPIRATE_H_ */
