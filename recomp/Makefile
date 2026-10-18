# Static recompilation of Enter the Realm: the BASIC programs (basic/, each
# from $(SS)/tools/bas2c.py, on the BASIC runtime $(SS)/runtime/basic_runtime.c),
# the machine code and modules (gen/, from SuperSpider's analyse and gen via
# ../tools/images.py) and game.c, linked with libroger (the RISC OS runtime).
ROGER   ?= $(HOME)/stuff/libroger
SS      ?= $(HOME)/stuff/superspider
CC      ?= gcc
CFLAGS  ?= -O2 -g -w -fno-strict-aliasing $(if $(TRACE),-DRECOMP_TRACE)
GEN     := $(wildcard gen/*/code*.c) $(wildcard gen/*/entries.c)
BAS     := $(wildcard basic/*.c)
OBJ     := $(GEN:.c=.o) $(BAS:.c=.o) basic_runtime.o game.o
LIBS    := $(shell pkg-config --libs sdl3) -lm -lpthread
INC     := -I$(ROGER)/include

enterrealm: $(OBJ) $(ROGER)/libroger.a
	$(CC) $(CFLAGS) -o $@ $(OBJ) $(ROGER)/libroger.a $(LIBS)

$(ROGER)/libroger.a: FORCE
	$(MAKE) -C $(ROGER) libroger.a

gen/%.o: gen/%.c $(ROGER)/include/roger_cpu.h
	$(CC) $(CFLAGS) $(INC) -c -o $@ $<

%.o: %.c $(SS)/runtime/basic_runtime.h $(ROGER)/include/roger.h
	$(CC) $(CFLAGS) $(INC) -I$(SS)/runtime -c -o $@ $<

basic_runtime.o: $(SS)/runtime/basic_runtime.c $(SS)/runtime/basic_runtime.h $(ROGER)/include/roger.h
	$(CC) $(CFLAGS) $(INC) -I$(SS)/runtime -c -o $@ $<

game.o: gen/images.inc basic/programs.inc

# make regen: analyse and translate the machine code; make basic: the BASIC
regen:
	python3 -I ../tools/images.py analyse gen
basic:
	python3 -I ../tools/images.py basic

# make listings: the BASIC programs as text, in ../basic, to read
listings:
	mkdir -p ../basic
	cd ../game && for f in $$(find . -type f -name '*,fffffb*'); do \
	    n=$$(echo $$f | sed 's|^\./||; s|,.*||; s|!||g; s|/|.|g'); \
	    python3 -I $(SS)/tools/detok.py "$$f" > ../basic/$$n.bas; done

LOG ?= untranslated.log
roots:
	python3 -I ../tools/images.py roots $(LOG)

clean:
	rm -f gen/*/*.o basic/*.o *.o enterrealm

.PHONY: FORCE regen basic listings roots clean
