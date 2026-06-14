# Live demo runbook

Five Sentinel features, five real Pharos Atlantic transactions, one command each. Drive them in front
of an audience with [`demo.py`](demo.py) — every step narrates itself and prints an explorer link you
can open on screen.

## Setup (once)

```bash
cd ~/pharos-sentinel
source .venv/bin/activate
python -c "import pharos_atlantic as p; print('chain_ok:', p.chain_ok())"   # expect True
```

The on-chain steps sign with the throwaway testnet key in `.wallet` (gitignored, testnet-only). The
Skill itself never signs — only this demo consumer does.

## The five proofs

| # | Command | Feature it proves | What the room sees |
|---|---|---|---|
| 0 | `python demo.py gallery`  | detection across the risk spectrum (read-only) | 6 live contracts → a safe→caution→dangerous ladder |
| 1 | `python demo.py deploy`   | flags freshly-deployed malicious bytecode | a brand-new contract → **DANGEROUS (30)** |
| 2 | `python demo.py upgrade`  | catches a live upgrade-rug | same proxy address: **safe → caution** after the implementation swap |
| 3 | `python demo.py pause`    | tracks live operational state | same contract: **safe → caution** the moment it's paused |
| 4 | `python demo.py transfer` | the gate moves real value | `safe` target → **0.0005 PHRS actually sent**; `dangerous` → no tx |
| 5 | `python demo.py x402`     | pay-per-query monetization over x402 | pay a micro-fee → verdict; replay the payment → **rejected** |

`python demo.py all` runs proofs 1–5 back-to-back and prints a five-transaction summary at the end.

## Suggested patter

- **deploy** — "I just deployed a contract with a self-destruct and an open delegatecall. Before anyone
  touches it, Sentinel reads it cold and calls it *dangerous* — no allowlist, no indexer, just the chain."
- **upgrade** — "Here's the rug Sentinel warns about. The proxy looks fine; the owner swaps the logic in
  one transaction — and Sentinel's verdict on the *same address* jumps to caution. It reads state at call time."
- **pause** — "Same idea, operational: the owner pauses it mid-flight and Sentinel sees it immediately."
- **transfer** — "This is the gate with teeth. Safe target: value actually moves. Dangerous target: no
  transaction is ever signed."
- **x402** — "And it's monetizable: pay a micro-fee over x402, get the verdict; replay the payment, denied."

## Tips for a smooth run

- The RPC layer retries on transient throttling, but if you're on flaky Wi-Fi, run features one at a time
  rather than `all`.
- Every run deploys **fresh** contracts and sends **fresh** transactions, so addresses and hashes differ
  each time — that's the proof it's live, not a recording. Keep `https://atlantic.pharosscan.xyz` open.
- Each on-chain feature costs a fraction of a PHRS in gas; `all` is well under 0.05 PHRS.

## Last verified run (2026-06-13)

Run via Foundry `cast` (the engine's execution model), end to end:

| Feature | Transaction |
|---|---|
| deploy + detect | `0xae7251648e6a62048ba916a68e76f05c770fc5eb3f6a8ded31a62db81de16c6e` |
| upgrade attack  | `0x3b7ffb8724876df7b153fd950a8a1525cc99612a46b33c1356585fa96951c4d0` |
| pause flip      | `0xdb08129581fe6f06fd3e69c70ad2e3b8e8739d090fa407c94f85affd07be1cf0` |
| value gate      | `0x251dd2d6c5aeef2f477963c79b37044d3a334d189a8aa872c638dbde27ed597d` |
| x402 paid query | `0x2120e375006fe8ca46042e3f3bc096d4eb26dfc13c453435572135f1079c0535` |
