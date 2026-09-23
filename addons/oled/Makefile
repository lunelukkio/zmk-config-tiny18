# Copyright (c) 2026 lunelukkio
# SPDX-License-Identifier: MIT

.DEFAULT_GOAL := all
.PHONY: all flash clean
all : tiny18_layer.bin

TARGET:=tiny18_layer
# render.c draws a state from layers.h; ch32fun.mk compiles it with the target.
ADDITIONAL_C_FILES:=render.c

TARGET_MCU?=CH32V003
# The UIAPduino's USB bootloader enumerates as 1209:b803, not minichlink's
# default 1209:b003, so `make flash` has to name it.
FLASH_COMMAND=$(MINICHLINK)/minichlink -c 0x1209b803 -w $< $(WRITE_SECTION) -b
# Keep generated linker scripts in this component, not inside the dependency.
override GENERATED_LD_FILE := tiny18_layer.ld
include ch32fun/ch32fun/ch32fun.mk

tiny18_layer.elf: render.c render.h layers.h funconfig.h

flash : cv_flash
clean : cv_clean
