/*
 * Copyright (c) 2026 lunelukkio
 * SPDX-License-Identifier: MIT
 *
 * Display Tiny18's active keymap layer and held modifiers on a transparent
 * SSD1309 OLED.
 *
 * SPI wiring follows docs/oled-setup.md. The input is a 9600 baud,
 * 8N1 UART byte on PD6:
 * Tiny18's right-half D1 sends a three-byte layer/left/right modifier frame
 * (0x90/0xA0/0xB0) and one-byte activity/OLED controls (0x80-0x84).
 * The display stays USB powered; only
 * D1->PD6 (through 1k ohm) and GND are shared with the keyboard.
 *
 * render.c turns a decoded state into the frame; the labels come from layers.h,
 * generated from the keymap by docs/tools/make_oled_layers.py in the tiny18
 * repository.
 *
 * Power. The panel is the largest consumer, so it is switched off after
 * IDLE_BLANK_MS without a valid byte and back on by the next one, the same
 * one hour the keyboard waits before its own deep sleep. The MCU runs from
 * the 24 MHz HSI divided to 8 MHz (funconfig.h and the top of main) and
 * sleeps in WFI between interrupts: the USART wakes it for a byte, SysTick
 * every TICK_MS to count idle time. Datasheet figures at 5 V: 48 MHz run
 * 7.4 to 8.8 mA, 8 MHz sleep 1.0 mA. What remains cannot be cut in
 * software: the module's AP3012 boost has its shutdown pin tied to VCC
 * (2.5 mA even with the panel off), plus its LDO and the board's own
 * overhead, about 4.3 mA together. Standby would save one more milliamp
 * but loses the byte that wakes it, so sleep is used instead.
 */

#define SSD1306_128X64
// HCLK is 8 MHz, so /2 gives a 4 MHz SPI clock, under the SSD1309's 10 MHz.
#define SSD1306_BAUD_RATE_PRESCALER SPI_BaudRatePrescaler_2
#define SSD1306_CUSTOM_INIT_ARRAY 1

#include "ch32fun.h"
#include "ssd1306_spi.h"
#include "ssd1306.h"
#include "render.h"
#include "brightness.h"
#include "brightness_store.h"
#include "../../include/tiny18_oled_uart.h"

#define LAYER_UART_BAUD 9600
#define TINY18_INITIAL_STATE 2

// SysTick runs at HCLK/8 = 1 MHz and raises an interrupt every TICK_MS, so
// idle time is counted while the core sleeps, and a byte that lands between
// the flag check and the wfi below is still picked up within one tick.
#define TICK_MS 10
#define TICKS_PER_TICK Ticks_from_Ms(TICK_MS)

// Time without a valid byte is idle time.
#define IDLE_BLANK_MS (60 * 60 * 1000)
#define IDLE_BLANK_TICKS (IDLE_BLANK_MS / TICK_MS)

static const uint8_t init_bytes[] = {
    0xAE,
    0xA8, 0x3F,
    0xD3, 0x00,
    0xD5, 0x80,
    0xD9, 0x22,
    0xDA, 0x12,
    0xDB, 0x40,
    0x20, 0x00,
    0xA1,
    0xC8,
    0xA4,
    0xA6,
};

// Written by the interrupt handlers, read by main.
static volatile uint8_t rx_bytes[32];
static volatile uint8_t rx_head;
static volatile uint8_t rx_tail;
static volatile uint32_t idle_ticks;
static volatile uint32_t elapsed_ticks;
static void uart_rx_init(void) {
    RCC->APB2PCENR |= RCC_APB2Periph_GPIOD | RCC_APB2Periph_USART1;

    // PD6 is USART1 RX with the internal pull-down. The keyboard's TX holds
    // the line high while connected. With the wire unplugged, or the keyboard
    // asleep with its pin released, the line rests low; whatever the receiver
    // makes of that fails its stop bit and the framing-error check in the
    // handler drops it. A pull-up is avoided on purpose: it would push 5 V
    // through the 1 kOhm resistor into an unpowered XIAO pin.
    GPIOD->CFGLR &= ~(0xFU << (4 * 6));
    GPIOD->CFGLR |= GPIO_CNF_IN_PUPD << (4 * 6);
    GPIOD->OUTDR &= ~(1U << 6);

    USART1->CTLR1 = USART_CTLR1_RE | USART_CTLR1_RXNEIE;
    USART1->CTLR2 = USART_StopBits_1;
    USART1->CTLR3 = USART_HardwareFlowControl_None;
    USART1->BRR = (FUNCONF_SYSTEM_CORE_CLOCK + LAYER_UART_BAUD / 2) / LAYER_UART_BAUD;
    USART1->CTLR1 |= CTLR1_UE_Set;
    NVIC_EnableIRQ(USART1_IRQn);
}

void USART1_IRQHandler(void) __attribute__((interrupt));
void USART1_IRQHandler(void) {
    // Reading STATR and then DATAR clears RXNE and the error flags.
    const uint16_t status = USART1->STATR;
    const uint8_t received = USART1->DATAR;
    if (status & (USART_FLAG_FE | USART_FLAG_NE | USART_FLAG_ORE)) {
        return;
    }
    const uint8_t next = (rx_head + 1) & 31;
    if (next == rx_tail) {
        return;
    }
    rx_bytes[rx_head] = received;
    rx_head = next;
}

static void tick_init(void) {
    // Keep the HCLK/8 source and no auto-reload so Delay_Ms keeps working;
    // the handler advances CMP itself, as ch32fun's systick_irq example does.
    SysTick->CMP = SysTick->CNT + TICKS_PER_TICK;
    SysTick->SR = 0;
    SysTick->CTLR = SYSTICK_CTLR_STE | SYSTICK_CTLR_STIE;
    NVIC_EnableIRQ(SysTick_IRQn);
}

void SysTick_Handler(void) __attribute__((interrupt));
void SysTick_Handler(void) {
    SysTick->CMP += TICKS_PER_TICK;
    SysTick->SR = 0;
    elapsed_ticks++;
    if (idle_ticks < IDLE_BLANK_TICKS) {
        idle_ticks++;
    }
}

static void show_state(tiny18_display_state_t state) {
    tiny18_render(ssd1306_buffer, state);
    ssd1306_refresh();
}

int main(void) {
    SystemInit();
    // SystemInit leaves the 24 MHz HSI as SYSCLK with the AHB undivided; /3
    // makes HCLK the 8 MHz that FUNCONF_SYSTEM_CORE_CLOCK already assumes.
    // Nothing that keeps time runs before this line.
    RCC->CFGR0 = (RCC->CFGR0 & ~RCC_HPRE) | RCC_HPRE_DIV3;
    Delay_Ms(100);

    const uint8_t saved_level = oled_store_load();
    oled_brightness_t brightness;
    oled_brightness_init(&brightness, saved_level);
    // A saved 0% wakes at full brightness without writing flash on startup.
    uint8_t persisted_level = brightness.level;
    uint32_t changed_at = 0;
    bool save_failed = false;

    ssd1306_spi_init();
    ssd1306_init();
    for (unsigned index = 0; index < sizeof(init_bytes); index++) {
        ssd1306_cmd(init_bytes[index]);
    }
    ssd1306_cmd(0x81);
    ssd1306_cmd(oled_brightness_contrast(brightness.level));

    ssd1306_setbuf(1);
    ssd1306_refresh();
    ssd1306_cmd(0xAF);
    Delay_Ms(500);

    uart_rx_init();
    // Match Tiny18's startup mode even if this receiver misses the boot byte.
    tiny18_display_state_t displayed_state = {.layer = TINY18_INITIAL_STATE};
    uint8_t pending_layer = 0;
    uint8_t pending_left = 0;
    uint8_t pending_part = 0;
    uint32_t pending_at = 0;
    bool panel_on = true;
    show_state(displayed_state);
    tick_init();

    while (1) {
        while (rx_tail != rx_head) {
            const uint8_t received = rx_bytes[rx_tail];
            rx_tail = (rx_tail + 1) & 31;
            const uint8_t old_level = brightness.level;
            if ((received & 0xF0) == TINY18_STATE_HEADER &&
                (received & 0x0F) <= TINY18_STATE_MAX_LAYER) {
                pending_layer = received & 0x0F;
                pending_part = 1;
                pending_at = elapsed_ticks;
                continue;
            }
            if (pending_part == 1 && (received & 0xF0) == TINY18_STATE_LEFT) {
                pending_left = received & 0x0F;
                pending_part = 2;
                continue;
            }
            if (pending_part == 2 && (received & 0xF0) == TINY18_STATE_RIGHT) {
                pending_part = 0;
                tiny18_display_state_t next = {
                    .layer = pending_layer,
                    .left_mods = pending_left,
                    .right_mods = received & 0x0F,
                };
                idle_ticks = 0;
                oled_brightness_wake(&brightness);
                if (next.layer != displayed_state.layer ||
                    next.left_mods != displayed_state.left_mods ||
                    next.right_mods != displayed_state.right_mods) {
                    displayed_state = next;
                    show_state(next);
                }
            } else if (received == TINY18_OLED_ACTIVITY ||
                       received == TINY18_OLED_DOWN ||
                       received == TINY18_OLED_UP ||
                       received == TINY18_OLED_BOOT) {
                pending_part = 0;
                idle_ticks = 0;
                oled_brightness_command(&brightness, received);
            } else {
                pending_part = 0;
                continue;
            }
            if (brightness.level != old_level) {
                changed_at = elapsed_ticks;
                save_failed = false;
                if (brightness.level != 0) {
                    ssd1306_cmd(0x81);
                    ssd1306_cmd(oled_brightness_contrast(brightness.level));
                }
            }
            const bool visible = oled_brightness_visible(&brightness);
            if (visible != panel_on) {
                ssd1306_cmd(visible ? SSD1306_DISPLAYON : SSD1306_DISPLAYOFF);
                panel_on = visible;
            }
        }
        if (pending_part != 0 && (uint32_t)(elapsed_ticks - pending_at) >= 2) {
            pending_part = 0;
        }
        if (!brightness.idle_off && idle_ticks >= IDLE_BLANK_TICKS) {
            oled_brightness_idle(&brightness);
            if (panel_on) {
                ssd1306_cmd(SSD1306_DISPLAYOFF);
                panel_on = false;
            }
        }
        if (!save_failed && brightness.level != persisted_level &&
            (uint32_t)(elapsed_ticks - changed_at) >= 100) {
            const uint8_t saving = brightness.level;
            if (oled_store_save(saving)) {
                persisted_level = saving;
            } else {
                save_failed = true;
            }
            changed_at = elapsed_ticks;
        }
        if (rx_tail == rx_head) {
            __WFI();
        }
    }
}
