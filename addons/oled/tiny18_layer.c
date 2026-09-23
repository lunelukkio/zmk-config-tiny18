/*
 * Copyright (c) 2026 lunelukkio
 * SPDX-License-Identifier: MIT
 *
 * Display Tiny18's active keymap layer and held modifiers on a transparent
 * SSD1309 OLED.
 *
 * SPI wiring follows docs/oled-setup.md. The input is a 9600 baud,
 * 8N1 UART byte on PD6:
 * Tiny18's right-half D1 sends the highest active layer in bits 0-2 and one
 * bit each for Shift, Ctrl, Alt and GUI in bits 3-6, at boot, whenever that
 * state changes and on every key press, so a display plugged in later
 * catches up on the first keystroke. Bit 7 is never set, so a byte with it
 * set is noise. The display stays USB powered; only D1->PD6 (through 1k ohm)
 * and GND are shared with the keyboard.
 *
 * render.c turns a state byte into the frame; the labels come from layers.h,
 * generated from the keymap by docs/tools/make_oled_layers.py in the tiny18
 * repository.
 *
 * Power. The panel is the largest consumer, so it is switched off after
 * IDLE_BLANK_MS without a valid byte and back on by the next one, the same
 * 30 minutes the keyboard waits before its own deep sleep. The MCU runs from
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

#define LAYER_UART_BAUD 9600
#define TINY18_INITIAL_STATE 2

// SysTick runs at HCLK/8 = 1 MHz and raises an interrupt every TICK_MS, so
// idle time is counted while the core sleeps, and a byte that lands between
// the flag check and the wfi below is still picked up within one tick.
#define TICK_MS 10
#define TICKS_PER_TICK Ticks_from_Ms(TICK_MS)

// The keyboard sends a byte on every key press, so time without a valid byte
// is idle time, counted the same way the keyboard counts it.
#define IDLE_BLANK_MS (30 * 60 * 1000)
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
    0x81, 0x7F,
    0xA4,
    0xA6,
};

// Written by the interrupt handlers, read by main.
static volatile uint8_t pending_state;
static volatile uint8_t pending_valid;
static volatile uint32_t idle_ticks;

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
    if (received & TINY18_STATE_INVALID) {
        return;
    }
    // Only a byte that passed both checks counts as activity.
    pending_state = received;
    pending_valid = 1;
    idle_ticks = 0;
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
    if (idle_ticks < IDLE_BLANK_TICKS) {
        idle_ticks++;
    }
}

static void show_state(uint8_t state) {
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

    ssd1306_spi_init();
    ssd1306_init();
    for (unsigned index = 0; index < sizeof(init_bytes); index++) {
        ssd1306_cmd(init_bytes[index]);
    }

    ssd1306_setbuf(1);
    ssd1306_refresh();
    ssd1306_cmd(0xAF);
    Delay_Ms(500);

    uart_rx_init();
    // Match Tiny18's startup mode even if this receiver misses the boot byte.
    uint8_t displayed_state = TINY18_INITIAL_STATE;
    uint8_t blanked = 0;
    show_state(displayed_state);
    tick_init();

    while (1) {
        __WFI();
        if (pending_valid) {
            // Clear the flag before taking the state: a byte that arrives in
            // between is then seen again on the next pass instead of lost.
            pending_valid = 0;
            const uint8_t state = pending_state;
            if (blanked) {
                // The panel keeps its GDDRAM while off, so DISPLAYON alone
                // brings back the last frame.
                ssd1306_cmd(SSD1306_DISPLAYON);
                blanked = 0;
            }
            if (state != displayed_state) {
                displayed_state = state;
                show_state(state);
            }
        }
        if (!blanked && idle_ticks >= IDLE_BLANK_TICKS) {
            ssd1306_cmd(SSD1306_DISPLAYOFF);
            blanked = 1;
        }
    }
}
