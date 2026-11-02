# CAMO genesis allocation (public record)

The mainnet genesis block (block 0) creates 640,000 CAMO, split into three outputs.
Genesis amounts are public on chain; anyone can check them.

| Output | Amount | Address (CAMO mainnet) |
|---|---|---|
| 0 Founder | 489,600 CAMO | `CdffG2fKbjRKAPaePe7DJU5eja5CvpLtqByQtzegwKawKYifqATBXkFAivzmGyM4meVzGRkF7d6UpRorehPmMqrXHkgGx9D` |
| 1 Marketing | 54,400 CAMO | `Cfbe7EfJzZW4H6Li6bvsmfTvjdQE5gsGvTf1PhS9MvnnEHpQUwgxVvFJd79u6KsgibPht4u2PRyj2fU7awZCoaPc6FaAtK4` |
| 2 Burn (15%) | 96,000 CAMO | `Cdqd3jC3ocP6H1BX4G2Uis8qVYj6ddShVfqGaxkvCE64YEgGgZTt5RjLZ4toVBJ3pae1HJR1AcWQxBmSRi55ePTv4dxHzs8` |

Founder + marketing = 544,000 CAMO = 3.0% of the 18.13M main emission.

- Burn address view key (public): `4846a9442b62be63ac514878acb76bc3ede0468f7f3d3b0710d191fcedf57f09`
  Reproduce: `python3 contrib/camo/tools/make_burn_address.py`
- Founder and marketing view keys: published at launch (Dec 15, 2026).
- The official mining pool's 1% fee is paid to the marketing address.
- Regenerate/verify the genesis tx: `contrib/camo/tools/make_genesis.py` (the one-time tx key is random, so the
  hex differs on each run; what is fixed is the three amounts and the three recipients).
