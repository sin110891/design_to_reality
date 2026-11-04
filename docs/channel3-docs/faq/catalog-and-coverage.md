> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Catalog & coverage

### Which countries and currencies are supported?

Channel3 supports locale-aware search across the U.S., UK, Canada, Australia, and much of Europe. Set a default locale on the SDK client or pass `country`, `language`, and `currency` per call — see [Localization](/guides/localization) and [Default locale](/sdk#default-locale).

### Countries

| Code | Market                                                                             |
| ---- | ---------------------------------------------------------------------------------- |
| `US` | United States                                                                      |
| `CA` | Canada                                                                             |
| `GB` | United Kingdom                                                                     |
| `IE` | Ireland                                                                            |
| `AU` | Australia                                                                          |
| `DE` | Germany                                                                            |
| `AT` | Austria                                                                            |
| `FR` | France                                                                             |
| `BE` | Belgium                                                                            |
| `IT` | Italy                                                                              |
| `ES` | Spain                                                                              |
| `NL` | Netherlands                                                                        |
| `SE` | Sweden                                                                             |
| `FI` | Finland                                                                            |
| `PT` | Portugal                                                                           |
| `CZ` | Czech Republic                                                                     |
| `GR` | Greece                                                                             |
| `RO` | Romania                                                                            |
| `EU` | Europe (pan-region; use with `currency: EUR` when you don't need a single country) |

### Currencies

`USD`, `CAD`, `AUD`, `GBP`, `EUR`, `SEK`, `CZK`, `RON`

When you set `country` only, the API infers `currency` (for example `GB` → `GBP`). When all three locale fields are unset, defaults are `en` / `US` / `USD`.

### Languages

`en`, `de`, `fr`, `it`, `es`, `nl`, `sv`, `fi`, `pt`, `cs`, `el`, `ro`

Coverage outside the U.S. is still growing. If you need a market we don't support yet, <a href="mailto:support@trychannel3.com">contact us</a> or ask in [Discord](https://discord.gg/6J6MjctXrH).

### Can I request a brand or retailer be added?

Yes — <a href="mailto:support@trychannel3.com">email us</a> with the brand or retailer and we'll prioritize it.
