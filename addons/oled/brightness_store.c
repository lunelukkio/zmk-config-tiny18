/* Copyright (c) 2026 The Tiny18 contributors
 * SPDX-License-Identifier: MIT
 */
#include "ch32fun.h"
#include "brightness.h"
#include "brightness_store.h"

#define STORE_FIRST 0x08003F80UL
#define STORE_SECOND 0x08003FC0UL
#define STORE_MAGIC 0x184C444FUL

static uint32_t sequence;
static uint32_t active_address;

static bool valid(const uint32_t *page) {
    return page[0] == STORE_MAGIC && page[2] <= OLED_MAX_LEVEL &&
           page[3] == (STORE_MAGIC ^ page[1] ^ page[2] ^ 0xFFFFFFFFUL);
}

uint8_t oled_store_load(void) {
    const uint32_t *first = (const uint32_t *)STORE_FIRST;
    const uint32_t *second = (const uint32_t *)STORE_SECOND;
    const bool a = valid(first);
    const bool b = valid(second);
    if (!a && !b) {
        active_address = 0;
        sequence = 0;
        return OLED_MAX_LEVEL;
    }
    active_address = b && (!a || (int32_t)(second[1] - first[1]) > 0)
                         ? STORE_SECOND : STORE_FIRST;
    const uint32_t *selected = (const uint32_t *)active_address;
    sequence = selected[1];
    return (uint8_t)selected[2];
}

/* Flash reads stall while a page is busy. Run the transaction from RAM. */
static void __attribute__((section(".data.ramfunc"), noinline))
program_page(uint32_t address, const uint32_t *words) {
    FLASH->CTLR = CR_PAGE_ER;
    FLASH->ADDR = address;
    FLASH->CTLR = CR_STRT_Set | CR_PAGE_ER;
    while (FLASH->STATR & FLASH_STATR_BSY) {}

    FLASH->CTLR = CR_PAGE_PG;
    FLASH->CTLR = CR_BUF_RST | CR_PAGE_PG;
    FLASH->ADDR = address;
    while (FLASH->STATR & FLASH_STATR_BSY) {}
    volatile uint32_t *target = (volatile uint32_t *)address;
    for (unsigned i = 0; i < 16; i++) {
        target[i] = words[i];
        FLASH->CTLR = CR_PAGE_PG | FLASH_CTLR_BUF_LOAD;
        while (FLASH->STATR & FLASH_STATR_BSY) {}
    }
    FLASH->CTLR = CR_PAGE_PG | CR_STRT_Set;
    while (FLASH->STATR & FLASH_STATR_BSY) {}
    FLASH->CTLR = 0;
}

bool oled_store_save(uint8_t level) {
    if (level > OLED_MAX_LEVEL) {
        return false;
    }
    const uint32_t target = active_address == STORE_FIRST ? STORE_SECOND : STORE_FIRST;
    uint32_t words[16];
    for (unsigned i = 0; i < 16; i++) {
        words[i] = 0xFFFFFFFFUL;
    }
    words[0] = STORE_MAGIC;
    words[1] = sequence + 1;
    words[2] = level;
    words[3] = STORE_MAGIC ^ words[1] ^ words[2] ^ 0xFFFFFFFFUL;

    FLASH->KEYR = FLASH_KEY1;
    FLASH->KEYR = FLASH_KEY2;
    FLASH->MODEKEYR = FLASH_KEY1;
    FLASH->MODEKEYR = FLASH_KEY2;
    if (FLASH->CTLR & 0x8080) {
        return false;
    }
    const uint32_t interrupt_state = __get_MSTATUS();
    __disable_irq();
    program_page(target, words);
    __set_MSTATUS(interrupt_state);
    FLASH->CTLR = FLASH_CTLR_LOCK;
    if (!valid((const uint32_t *)target)) {
        return false;
    }
    active_address = target;
    sequence = words[1];
    return true;
}
