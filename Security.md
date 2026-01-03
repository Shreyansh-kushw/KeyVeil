# Security Policy — KeyVeil

## Overview

KeyVeil is an **offline, single-user desktop password manager** designed for
local storage of credentials using modern, well-established cryptographic
primitives.

The project intentionally avoids cloud services, browser extensions, and
network-based synchronization in order to reduce the attack surface and
simplify the threat model.

This document describes what KeyVeil **does protect against**, what it **does
not protect against**, and the security decisions behind its design.

---

## Threat Model

### Assets Protected

KeyVeil is designed to protect:
- Stored credentials (site name, username, password)
- The encrypted vault file (`vault.enc`)
- The encryption key derived from the user's PIN

### Adversary Assumptions

KeyVeil assumes an adversary who:
- Does **not** know the user's PIN
- May gain read-only access to local files (e.g., copied vault file)
- May attempt offline brute-force attacks on the encrypted vault
- May inspect the source code (open-source assumption)

KeyVeil assumes:
- A reasonably trusted operating system
- No active malware, keyloggers, or runtime memory inspection

KeyVeil does **not** protect against:
- A fully compromised or malicious operating system
- Active keylogging, screen capture, or memory scraping

---

## What KeyVeil Protects Against

### Offline Vault Access

- All vault data is encrypted at rest using **Fernet (AES-128 in GCM mode)**.
- The encryption key is **never stored** on disk.

### Brute-Force Resistance

- Encryption keys are derived from the user PIN using:
  - **PBKDF2-HMAC-SHA256**
  - **≥200,000 iterations**
  - A **random 128-bit salt**
- This significantly increases the cost of offline brute-force attacks.

### Unauthorized Vault Access

- The vault cannot be decrypted without the correct PIN.
- Invalid PIN attempts are detected and handled explicitly.

### Accidental Data Exposure

- No plaintext credentials are written to disk.
- Backups preserve encrypted vaults and salts only.
- Clipboard operations are explicit and user-triggered.

---

## What KeyVeil Does NOT Protect Against

KeyVeil **does not** attempt to protect against the following scenarios:

### Compromised Operating System

- Malware, keyloggers, memory inspection, or a hostile OS can extract secrets.
- KeyVeil assumes the host system is reasonably trusted.

### Live Memory Attacks

- Credentials may exist briefly in memory during use.
- KeyVeil does not implement hardened memory zeroization beyond Python’s
  garbage collection behavior.

### Shoulder Surfing & Physical Access

- Anyone observing the screen or keyboard can capture secrets.
- Physical access to an unlocked session is not mitigated.

### Network-Based Threats

- KeyVeil does not perform network operations for credential handling.
- It provides no protection against phishing or malicious websites.

---

## Cryptographic Design

KeyVeil uses only standard cryptographic primitives provided by
well-maintained libraries.

### Key Derivation
- Algorithm: PBKDF2-HMAC-SHA256
- Iterations: ≥200,000
- Salt: Random, stored locally in `salt.bin`

### Encryption
- Scheme: Fernet (symmetric authenticated encryption)
- Key length: 32 bytes (derived)
- Integrity and confidentiality are both enforced

### Design Notes
- No custom cryptography is implemented.
- All cryptographic operations rely on the `cryptography` Python library.

---

## Backup & Restore Security

- Backups contain only encrypted data (`vault.enc`) and the salt (`salt.bin`).
- Restoring a backup **overwrites existing vault data** after user confirmation.
- Backups do not weaken encryption strength.

---

## Known Limitations

- KeyVeil is not hardened against advanced forensic or runtime attacks.
- It does not implement secure enclave, TPM, or OS-level key isolation.
- It does not support multi-user or multi-device usage.

These limitations are **intentional design trade-offs** to keep the project
simple, auditable, and offline-first.

---

## Reporting Security Issues

This project is feature-complete and not under active development.
However, responsible disclosures are welcome.

If you discover a security issue:
- Open a GitHub issue with a clear description
- Do not include sensitive data in the report

There is no bug bounty program associated with this project.

---

## Final Note

KeyVeil is intended as a **learning-focused, reference implementation** of a
local password manager with a clearly defined and honest security model.

It is **not a replacement** for enterprise-grade or cloud-based password
management solutions.

Users are encouraged to evaluate whether the threat model aligns with their
personal use case.
