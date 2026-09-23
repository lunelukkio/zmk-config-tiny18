// Copyright (c) 2026 lunelukkio
// SPDX-License-Identifier: MIT

#ifndef _FUNCONFIG_H
#define _FUNCONFIG_H

// This display is USB powered and receives a single UART byte on PD6.
//
// Run from the 24 MHz HSI without the PLL, and let main() divide the AHB
// clock by 3. FUNCONF_SYSTEM_CORE_CLOCK is the HCLK after that division:
// ch32fun only uses it for the flash latency (0 wait states under 25 MHz),
// the SysTick delay constants and the UART divisor, all of which want the
// 8 MHz figure.
#define FUNCONF_USE_PLL 0
#define FUNCONF_SYSTEM_CORE_CLOCK 8000000

#endif
