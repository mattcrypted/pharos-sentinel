# Risk-gallery fixtures

The Solidity behind Sentinel's **live risk gallery** and on-chain proofs. Each contract is a
deliberately minimal **risk decoy** — engineered to trip one Sentinel signal — deployed to
Pharos Atlantic and then analysed live. Deployed addresses and expected verdicts live in
[`../fixtures.json`](../fixtures.json); [`../gallery.py`](../gallery.py) re-checks every exhibit
against the chain and fails on drift.

> These are test decoys, not production contracts. The `SELFDESTRUCT` / `DELEGATECALL` /
> zero-supply patterns exist precisely so Sentinel has something real to detect.

## What each contract demonstrates

| Contract | Role | Sentinel signal |
|---|---|---|
| `CleanToken` | safe baseline ERC-20 (also the implementation behind the minimal proxy) | none — verdict `safe` |
| `ZeroSupplyToken` | ERC-20 reporting zero supply, single EOA owner | zero-supply trap + EOA owner → `caution` |
| `LogicV1` + `Eip1967Proxy` | EIP-1967 upgradeable proxy, initialized paused with an EOA owner | upgradeable + EOA owner + paused → `caution` |
| `Backdoor` | latent `SELFDESTRUCT` + unguarded `DELEGATECALL` + paused + EOA owner | the dangerous stack → `dangerous` |
| `LogicBenign` + `MutableProxy` | the **live upgrade attack**: benign logic swapped to hostile in one tx | `upgradeable_impl` changes; verdict escalates |
| `Destructible` | the **live pause flip**: latent `SELFDESTRUCT`, then paused via one tx | `safe (25)` → `caution (45)` |

The EIP-1167 **minimal proxy** exhibit is deployed as raw init code pointing at `CleanToken`
(it has no Solidity source of its own — it is the canonical 45-byte minimal-proxy runtime).

## Build

```bash
forge build   # Foundry; metadata stripped (see foundry.toml) for clean opcode-scan fixtures
```

These fixtures are deployed live by the demo driver [`../demo.py`](../demo.py) via Foundry; the testnet
key it signs with stays in gitignored `.wallet` and is never committed. The deployed contracts
(addresses in `../fixtures.json`) are the public, verifiable artifacts.
