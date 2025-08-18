# PXOS Master Roadmap

## Core Vision
PXOS is a pixel-native, self-hosting operating system where computation, input, and output occur in a unified pixel space. The primary user environment is `pxweb`, a browser designed to replace traditional web browsers, integrated with an infinite, collaborative map for human and AI-driven development.

## Core Principles
1.  **Pixel-Native**: All computation manifests as pixel operations on a memory-mapped framebuffer.
2.  **Self-Hosting**: The OS can edit, assemble, and run its own code within the pixel environment.
3.  **Unified I/O**: A single `MAILBOX` protocol for human and AI interaction ensures auditability and parity.
4.  **Infinite Map**: A collaborative, sector-based spatial computing surface serves as the address space for sites and applications.
5.  **Secure by Design**: Cryptographic signatures, patch validation, and sandboxing are fundamental to the architecture.

## Phased Development Plan

| Phase | Focus | Status | Key Milestones |
|---|---|---|---|
| **1** | **Core VM & Self-Hosting** | ✅ Complete | - `StrictRunner` VM with a deterministic PXL instruction set.<br>- `MAILBOX` protocol at `0x1900` for atomic input.<br>- `PXEdit`/`PXAsm`/`PXLoad` cartridges enabling the self-hosting loop.<br>- All core tests passing. |
| **2** | **PXWeb Browser MVP** | ⏳ **Current Focus** | - Implement an interactive browser GUI using the provided `pygame` prototype as a base.<br>- Render a basic browser chrome (tabs, omnibox).<br>- Handle keyboard and mouse input via the `MAILBOX`.<br>- Establish the foundation for `pxweb` as the primary user environment. |
| **3** | **Infinite Map Integration** | 📋 Planned | - Connect `pxweb` to the infinite map via a `pxbridge` service.<br>- Render map sectors as a WebGL2 overlay in the browser.<br>- Implement panning, zooming, and basic map interaction. |
| **4**| **AI Collaboration** | 📋 Planned | - Enable AI agents to submit patches to the map and codebase via `pxbridge`.<br>- Implement a patch review and approval queue within `pxweb`.<br>- Extend the `MAILBOX` protocol for direct, secure AI commands. |
| **5** | **Security & Profiles** | 📋 Planned | - Implement sandboxing for web content and cartridges.<br>- Enforce cryptographic signatures for all patches and programs.<br>- Add user profiles with per-site/per-app permissions. |
| **6** | **Production Browser** | 📋 Planned | - Achieve full feature parity with modern browsers (HTML5/CSS3/JS/WebGL2).<br>- Optimize for performance and security to become a viable daily-driver replacement for Chrome/Firefox.<br>- Launch a pixel-native app store for cartridge distribution. |
