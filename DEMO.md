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
| 1 | `python demo.py deploy`   | flags freshly-deployed malicious bytecode | a brand-new contract → **DANGEROUS (70)** |
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

## Last verified run (2026-06-11)

| Feature | Transaction |
|---|---|
| deploy + detect | `0xd75525c724dcb39a5c1e4778ccacbce5b399c1ca0f69364125025a71e5b06802` |
| upgrade attack  | `0x393cbb193bcd5abc941dfca74bb8b9aae9ad158e5829a71a382b477dd18e2b16` |
| pause flip      | `0xe7834917263c453cc693313a29490613243fdac1adf0dbb0276a8db8d03a9270` |
| value gate      | `0x5ab244229ebe802bbd5721b274513cc0872224ee7e7303c9c4932cf5a08dfafe` |
| x402 paid query | `0x5c5fb941ceabf817a438c7ecc32ca1b77b22b22aa32441b38bb499105fb42a9c` |
