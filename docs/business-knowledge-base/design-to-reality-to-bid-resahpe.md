# Design to Reality to Bid Reshape

## The reshape, simply

**What it does:** takes a room and what someone wants, and gives back a design they can actually buy and build — with a price attached.

**How:** same engine you have. One extra output. The image gets broken into labelled regions (ceiling, floor, joinery), each region maps to real products and work packages, and those add up to a price range plus a list of what still needs checking on site.

**Why reshape:** pretty pictures are now free everywhere. And on your own mission — a render someone can't afford or can't get built democratises nothing. **The price and the buildability *are* the democratisation.** That's not a retreat from your goal, it's the part that makes it real.

## Your critiques

**MyBuilder and trades platforms.** They're not doing this. MyBuilder, Checkatrade, Rated People are lead-generation marketplaces — they introduce a homeowner to a builder, and then a *human* prices the job. No scope, no estimate, no structure. They're potential distribution channels, not competitors.

The real competitors are HBXL, Buildertrend, Houzz Pro, Countfire, and every estimator's spreadsheet. Their shared weakness: you must already know the scope before the tool helps.

But here's the sharper version of your point, and it's correct: **a homeowner who just wants a price can ask three builders for free.** So the consumer-facing pricing product is weak. The buyer has to be the firm — they pay in hours, not cash, and hours are what you save.

**"I could build this in days with Claude."** Yes. You could build the demo in days. That's now true of almost every AI product, and it's the right thing to be suspicious of.

The honest answer: **there is no technology moat here.** What's slow to copy is the rate data, the per-firm memory, the omission statistics, being embedded in someone's Monday-morning workflow, and being trusted enough that a director signs their name to your number. Generating a price is easy. Generating a price someone will *sign* is not — that needs accuracy proven against real outcomes, which you can't prompt into existence.

Most successful vertical software has no tech moat. It has distribution, workflow depth, and switching cost. If you need a technology moat to feel safe, this isn't the business.

## Why I haven't mentioned foundation models

Because at your stage it's nearly always the wrong move.

You have 45 labelled images. Meaningful fine-tuning needs thousands to tens of thousands. Base models are also improving faster than you could train — you'd spend six months catching up to where GPT or Gemini lands for free. And a real training run costs more than the round you'd raise.

More importantly, **the model isn't your bottleneck.** Gemini already generates good interiors. What's missing is structured knowledge — the ontology, the rates, the buildability rules — and that belongs in retrieval and deterministic code, not in model weights. Baking it into weights also makes it un-auditable, which is fatal when money is attached.

Where small-model training *will* pay off later: a reranker for your retrieval (hundreds of examples, cheap), and a classifier that maps messy text into your ontology. Both are small, both are worth doing once you have the data. Neither is a foundation model.

Also worth knowing: investors are actively wary of pre-seed teams training their own models. It reads as capital-inefficient unless the model *is* the product.

## Why they'd use it

They currently spend 8–20 unpaid hours per quote, and most quotes lose. The pitch is: get to a client-ready priced proposal in under two hours, re-price a change in minutes instead of a day, and get told what you forgot before it becomes a variation.

## Who

The buyer is whoever eats the unpaid hours: the owner-director of a 5–30 person design-and-build firm, or their estimator. Secondary: kitchen and bathroom showroom managers, where the value is conversion rather than time.

Not homeowners. They can get three quotes free.

## Why they wouldn't build it in-house

Most can't — a 12-person building firm has no engineers, and their next hire is an estimator, not a dev team.

The ones who *could* still can't build the useful part. A single firm only has its own history, which is already in its estimator's head. The value comes from benchmark rates and omission statistics **across** firms — that's structurally unavailable to any one of them.

Honest caveat: large national contractors will build it. That's exactly why you sell to the 5–30 person segment.

## "A price someone will sign"

Literally: a director puts their name on a number that becomes a contract. If it's wrong, they absorb the loss or end up in a dispute with a client.

So a generated number is worthless unless they trust it enough to send. Trust comes from showing the workings, flagging unknowns instead of hiding them, and eventually a track record of matching final accounts. Anyone can produce a number in an afternoon. Producing one a professional will stake their margin on takes real outcome data.

## UX flow

1. **Start job** — upload room photos, type or record the brief, drop in any mood board.
2. **Directions** — three visual options come back, with regions auto-detected (ceiling, floor, joinery).
3. **Confirm** — user picks a direction and corrects any mis-detected regions. Every correction is logged.
4. **Scope and price** — work packages, real products, and a price split into confirmed / provisional / contingency, plus a site-verification checklist and flagged likely omissions.
5. **Adjust** — edit any rate or line; the total recalculates instantly.
6. **Export** — client-ready proposal (visual + scope + range) and an internal estimate, versioned and signed off.
7. **Close the loop** — mark won or lost, enter the final account later. That's what improves accuracy.

## What to take from the four-company analysis

**Spacemaker is the one to steal from.** Its lesson — professionals want trade-offs, not more options — is exactly your pricing engine made visible. Instead of three pretty rooms, three rows:

| Direction | Taste fit | Cost | Complexity | Lead time |
|---|---|---|---|---|
| A | 92% | ££££ | high | 12 wks |
| B | 84% | ££ | low | 4 wks |
| C | 95% | £££ | medium | 8 wks |

That single table converts your product from "which do you like" to "which can you afford and build." It's also the clearest demo you could put in front of an investor.

**xFigura — take the light version.** A persistent project record where concepts, comments, and approvals live. Not because you want to be Figma, but because that's where decision history accumulates, and decision history is your data.

**Natural — later, but borrow the shape.** Its permission model (spend limits, approval thresholds, audit trail) is the right template for procurement approvals when you get there.

**LightReel — skip.** Trend intelligence is a distraction before revenue.

## Where scope and price come from

Five steps. Only the first involves AI.

**1. Design direction → regions.** The chosen concept has labelled regions: floor, ceiling, walls, joinery, lighting.

**2. Regions → work packages (rules, not AI).** You hold one fixed library of maybe 200 work packages covering residential refurb. "New engineered oak floor" *always* triggers the same set. This is a lookup, so it's identical every time.

**3. Packages → quantities.** Each package has a unit — m², linear metre, per item. The user types room dimensions once, or the system estimates with a range and adds it to the verification list. Nothing is silently invented.

**4. Quantities × rates.** Rates resolve in priority order: this firm's own rate → cross-firm benchmark → published or live supplier price. Each line is tagged with which tier it used.

**5. Assembly.** Waste, overhead, margin, contingency sized by how much of the job is still uncertain.

Worked example, a 16m² floor:

| Line | Qty | Rate | Source | Total |
|---|---|---|---|---|
| Strip out existing | 16 m² | £12 | benchmark | £192 |
| Prep substrate | 16 m² | £18 | benchmark | £288 |
| Supply oak | 16 m² | £85 | live supplier | £1,360 |
| Install | 16 m² | £32 | **their own rate** | £512 |
| Trims | 16 lm | £14 | their own rate | £224 |
| Make good decoration | 16 lm | £9 | benchmark | £144 |

Lines on their own rates are "confirmed." Lines on benchmarks are "provisional." That's literally where the split in the output comes from.

## How adjust works

Three levels, all instant.

**Line level.** Change a rate, quantity, or delete a line. Total recalculates immediately.

**Assumption level.** Change something global — ceiling height 2.4m → 2.7m, or budget band medium → high. It cascades: quantities shift, product tiers shift, price shifts.

**Design level.** Swap direction B for C, or change one region (oak → tile). Only affected packages regenerate; everything else stays put. This is why a revision takes minutes instead of a day.

**The important bit:** every edit is remembered *for that firm*. If they override plastering from £22 to £28/m² three times, the fourth job defaults to £28. Over a few months most of their lines move from "benchmark" to "their own rate," and the quote gets progressively more accurate without anyone configuring anything.

That's not a feature you build separately. It's just logging edits and using them as defaults.

## Your integration concern

You're right to be worried — bespoke work per customer is what turns a software company into a consultancy. Here's why it doesn't happen if you structure it as three layers.

**Shared (identical for everyone, ~90% of the system):** the work-package library, quantity rules, dependencies, product catalogue, the generation engine. Never customised, ever.

**Configured (a settings form, no engineering):** their rate card, margin %, preferred suppliers, standard exclusions, their logo. Seeded automatically by uploading 20 past quotes.

**Learned (automatic):** their corrections become their defaults.

So onboarding is: upload some old quotes, fill in a form, start using it. No code written per customer. No API into their accounting system at launch — you export PDF and CSV, which every firm already handles. Integrations like Xero or Buildertrend come later, built once for everyone.

**The honest risk:** if the firms you sell to do wildly different work, your shared library won't cover enough and you'll be tempted to bolt on custom packages for each one. That's the failure mode. The defence is the narrow wedge — kitchens, bathrooms, living spaces, residential refurb only. The narrowness isn't just positioning, it's what keeps the product a product.

**The test to watch:** if customer #10 needs engineering work that customer #1 didn't, you're drifting into consultancy. Track it explicitly from the first pilot.

## Why price instead of getting bids

Two reasons.

**You can't get a bid without a scope.** That's the actual bottleneck. A builder won't quote from a photo and a vibe — they need to know what work is involved. Producing that definition is the thing you're selling; bidding is what happens afterwards.

**Your customer *is* the bidder.** You chose to sell to design-and-build firms. They aren't seeking quotes, they're producing them. "Get people to bid" only applies to the homeowner model, which fails because homeowners get three free quotes anyway.

Worth noting: you're not replacing bidding, you're learning from it. Every quote your customers issue is a real price from an accountable party. That's your corpus.

## Where the prices come from

Three sources, and only one of them is hard.

**Materials — already solved.** Live supplier prices via your Channel3 integration plus published merchant pricing (Howdens, Travis Perkins, Topps). Materials are roughly 40–50% of a refurb. No cold start here at all.

**Labour — buy the seed data.** This is the honest answer people usually dodge. The UK construction industry has commercial price books that already contain labour constants and rates: SPON's Architects' and Builders' Price Book, BCIS (published by RICS), Laxton's. They cost a few hundred to low thousands per year. You license one, and you have a defensible day-one baseline.

Check the licence terms before building on it — using rates to *inform* an estimate is normally fine, redistributing raw rate tables usually isn't.

**Their own history — the real asset.** Backfilled quotes and final accounts, then every correction they make. This progressively overrides the purchased baseline.

## Regional variation

Also already solved commercially. BCIS publishes **location factors** by postcode area — roughly 1.15 for inner London, ~0.92 for the North East, against a UK mean of 1.0. It's a single multiplier applied to labour.

You don't derive regional pricing. You buy the index and apply it.

## The 200 work packages concern

You're right that 200 is too many for day one. Two things fix it.

**Don't invent the taxonomy — subset an existing one.** RICS already publishes standard work breakdown structures (NRM1/NRM2, and Uniclass for classification). Estimators already think in these categories. Adopting a subset means your exports are interoperable with how they already work, and you skip the research entirely.

**Start with one room type.** A kitchen refurb is 25–40 packages. A bathroom is 20–30. That's a few days with Lloyd and a price book, not a research programme. Add room types as you add customers.

## How the calculation actually works

The key design decision: **store labour as hours per unit, not £ per unit.**

```
Bad:  plastering = £22/m²        (mixes rate and productivity)
Good: plastering = 0.6 hrs/m²    × firm's hourly rate
```

That way a firm configures one number — their hourly rate — and every labour line in the system updates. Their whole config becomes a handful of values instead of hundreds.

Per line:

```
material = qty × unit_price × (1 + waste_factor)
labour   = qty × hours_per_unit × hourly_rate × regional_factor
line     = material + labour
```

Project level:

```
subtotal      = Σ lines
preliminaries = subtotal × prelim_%        (skips, welfare, access, protection)
overhead      = (subtotal + prelims) × overhead_%
margin        = × margin_%
contingency   = derived from uncertainty, not a flat %
```

The range comes from per-line confidence rather than a guessed ±20%:

```
tier 1  own rate + measured quantity      → ±5%
tier 2  benchmark rate + measured qty     → ±15%
tier 3  price book + estimated qty        → ±30%

low  = Σ (line × (1 − uncertainty))
high = Σ (line × (1 + uncertainty))
```

This gives you the honest headline output, and a genuinely nice product mechanic: **the range visibly narrows over months** as their own rates replace price-book defaults. The customer watches the tool get more accurate, which is exactly the retention story you want and the compounding story an investor wants.

## Do you need a partner?

Not to build it — but you have a real team gap.

**Buy, don't partner:** a price book licence (SPON's or BCIS) is a purchase, a few hundred to low thousands a year. No relationship needed.

**The gap:** Lloyd is an architect. Architects design; they don't price. Labour constants, preliminaries, how firms actually structure a quote, what commonly gets missed — that's quantity surveyor and estimator knowledge, and neither of you has it.

Fix it cheaply before building anything: hire a freelance residential estimator for 5–10 days (roughly £400–600/day) to validate your work-package list and rate structure. Or give an experienced estimator 0.25–0.5% as an advisor. Do this *before* the taxonomy work, not after.

## What the business does

Takes a room, a brief, and a set of photos. Returns three design directions, each with a scope of works, real products, and a priced range — plus a list of what still needs checking on site.

The firm adjusts it, sends it to their client, and the system remembers their corrections so the next one is more accurate.

## How costing works, in one paragraph

Regions map to work packages by rule. Each package has a quantity unit and a labour constant in hours. Materials come from live supplier prices; labour is hours × the firm's own rate × a regional factor from BCIS. Lines priced on the firm's own rates are "confirmed"; lines still on price-book defaults are "provisional." The range width is derived from that mix, so it narrows automatically as the firm uses the tool.

## What they're actually paying for

Not images, and not really software. Three things:

**Hours back.** 8–20 unpaid hours per quote drops to under 2. At a £45/hr blended cost that's £300–800 per quote, and they produce 5–20 quotes a month.

**Margin protection.** One caught omission on a £150k job is worth more than a year's subscription.

**Speed to the client.** Answering in two days instead of two weeks wins work.

## How you get them to pay

Sell a **paid pilot, not a subscription**. £1,500 for eight weeks across five real projects, half up front. Frame it as a workflow study, not a product demo — that's how Lloyd's network will actually engage.

Better still, price per project (£250–400) at first. It matches how they already think — they price per job, not per month — and it removes the "another monthly bill" objection entirely.

## Proving the saving

You must capture the baseline *before* they touch the tool. This is the step most founders skip and then can never recover.

**Before:** take three recent quotes and reconstruct actual hours from timesheets and memory. Record revision rounds and time from enquiry to issued quote.

**After:** the same measurements across five quotes using the tool.

**Report four numbers:** hours per quote, revision rounds, percentage of generated scope retained unedited, and omissions caught with pound values attached. Get it signed as a case study.

If hours drop 40% and you caught two real omissions with money attached, you have something an investor and the next customer both believe.

## Proving the saving — the actual protocol

The principle in one sentence: **if you don't record how long their current process takes before they touch your tool, you can never claim you saved them anything.**

**Step 1 — Baseline session (90 minutes, before any access)**

Sit with them and walk backwards through their **last three completed quotes**. For each one, fill in a single sheet:

- Date the enquiry arrived, date the quote was sent (from their email trail — this is reliable)
- Who worked on it, their role, and roughly how many hours each spent
- Split those hours five ways: understanding the brief, finding references, producing visuals, pricing and takeoff, writing the document
- Number of times a revised version went back to the client
- Won or lost, and the project value
- Anything missed that later became a variation, and what it cost them

Three quotes, not ten — that's the most anyone reconstructs accurately in one sitting. Hours will be estimates. That's fine, as long as the "after" measurement is estimated the same way by the same people.

**Step 2 — Agree the endpoint in writing**

Before and after must measure the same thing. Write down: *"A quote is complete when it has been sent to the client."* Skip this and the comparison is worthless because everyone silently measures to a different finish line.

**Step 3 — Pilot: five real projects over 6–8 weeks**

Log identical fields. Don't rely on them to remember — own the spreadsheet yourself and chase it weekly. At least one project should be a live opportunity they haven't won yet, and one should be a job needing revisions.

**Step 4 — The four numbers**

| Number | How you calculate it |
|---|---|
| Hours per quote | Total staff hours, enquiry to sent. Before vs after. |
| Revision rounds | Count of revised versions issued to the client. |
| Scope retention | Of the lines your tool generated, what % went out unedited. E.g. 42 generated, 27 untouched = 64%. |
| Omissions caught | Lines your completeness check flagged that they'd missed, and the £ value of those lines. |

Scope retention is the one to watch hardest — it tells you whether the output is genuinely usable or just plausible. Omissions caught is the one that sells, because it comes with a pound sign.

**Step 5 — Get it signed while they're happy**

One page: their logo, the four numbers, a two-line quote from the director, a signature. Ask on the final day of the pilot, not three months later when the enthusiasm has faded.

## Tailoring per segment

The four numbers don't fit every segment equally. Adjust:

**Design-and-build (PepperBuild, Kraman, Eleventh Element)** — the cleanest case. They have real estimating hours and real variation pain. Lead with hours saved and omissions caught. With Kraman specifically, open on variations: their whole positioning is that they don't move the price, so a scope gap costs *them*, not the client.

**K&B showrooms (Leonide, KV, Dezign)** — they already quote fast, sometimes same-day, so time saved is a weaker story. Measure **throughput and conversion instead**: quotes produced per designer per week, and showroom appointment → deposit conversion rate. Their value metric is sales, not hours.

**Interior design studios (Amy Drean, Kando, House of Norica)** — they don't price construction work, so drop the labour-rate side. Measure concept hours, revision rounds, and time from brief to client sign-off. Amy Drean is worth approaching first specifically because costing early is already their stated method, meaning they'll have the data and understand the pitch immediately.

**Architecture practices (Studio 29, Folly)** — their pain isn't quoting, it's unpaid feasibility work and clients being shocked by cost at tender. Measure feasibility hours and the percentage of projects where tender came back over the client's budget. Reducing that second number is worth a lot to them.

## UK market size

Bottom-up, and treat these as estimates worth validating against ONS and Companies House:

| Segment | Approx. UK firms |
|---|---|
| Residential design-and-build (5–30 staff) | ~10,000 |
| Kitchen & bathroom showrooms | ~6,000 |
| Interior design studios | ~5,000 |
| Small residential architecture practices | ~3,000 |
| **Total** | **~24,000** |

At £6,000 average annual contract, **UK TAM ≈ £145m ARR**.

**SAM** — the narrow wedge you can actually serve (premium residential design-and-build plus K&B, England, aesthetic fit): roughly 3,000–5,000 firms, or **£18–30m ARR**.

## Target companies

Below are real UK firms found by search, then a concrete measurement protocol. Verify size and style fit before approaching — and remember Lloyd's network will out-convert cold outreach every time.

**Residential design-and-build**

- [PepperBuild](https://pepperbuild.com/) — owner-led boutique London contractor, refurbishments, deliberately small
- [KRAMAN Ltd](https://kraman.co.uk/) — Leytonstone, FMB accredited, runs 3–5 concurrent projects, one PM per job. Their site says *"We quote what we will charge, and we charge what we quoted"* — variations are clearly a sore point, which is your hook
- [Eleventh Element](https://eleventhelement.co.uk/) — architect-led design and build, South East London, small family firm

**Kitchen & bathroom showrooms**

- [Leonide Interiors](https://www.leonideinteriors.co.uk/) — Chesterfield, award-winning, design/supply/install
- [The KV Showroom](https://www.thekvshowroom.co.uk/) — Cambridge, sells design as a standalone service
- [Dezign Studio](https://dezignstudio.co.uk/) — Ilford, luxury bathrooms and German/British kitchens

**Interior design studios**

- [Amy Drean Interiors](https://www.amydreaninteriors.com/) — best fit on this list. London period homes, and their own copy says *"every fixture costed before site began"*. Costing is already their differentiator
- [Kando Studio](https://kandostudio.com/) — West London, £25k minimum project budget, full service including contractor coordination
- [House of Norica](https://www.houseofnorica.com/) — South London, high-end residential

**Small residential architecture practices**

- [Studio 29 Architects](https://www.studio29architects.co.uk/) — London, architecture and interiors combined, founder-run since 2013
- [Folly Architects](https://follyarchitects.com/) — Harrow, RIBA chartered, extensions and full refurbishments
- [RIBA Find an Architect](https://www.riba.org/explore/find-an-architect/) — the directory itself, 4,000+ chartered practices, filterable by location and residential specialism

These process breakdowns are inferred from each firm's public site plus typical practice in their segment — treat them as hypotheses to confirm in the first call, not facts.

## KRAMAN Ltd — residential design-and-build

Whole-house refurbs, £100–500k, 3–5 concurrent projects, one PM each.

| Stage | Today | Hrs | With the tool | Hrs |
|---|---|---|---|---|
| Enquiry call | Qualify, book visit | 0.5 | Unchanged | 0.5 |
| Site visit | Measure, photos, notes | 2.5 | Photos become the input, not just a memory aid | 2.5 |
| **Scope definition** | Writes out every item of work from notes | **4** | Photos + brief → named work packages, they review | **0.5** |
| **Pricing** | Quantities, rate lookup, chase subbie quotes | **6** | Quantities pre-filled, rates from their own history | **1.5** |
| Write-up | Format the document | 2.5 | Generated, they edit | 0.5 |
| **Revisions (×2)** | Re-price by hand each time | **6** | Recalculates on the spot | **0.5** |

**18–22 hrs → 5–6 hrs**, and calendar time drops from 2–3 weeks to under a week because they can issue a provisional range immediately instead of waiting on subcontractor prices.

**Money:** ~14 hrs saved × £45/hr = £630 per quote. At 8 quotes a month that's £5,000/month of director and PM time back. Most of those quotes lose, so it's pure recovered capacity.

**The hook:** their own site says *"we charge what we quoted."* That's admirable and it means every missed line comes straight out of their margin — they can't pass it on. One caught omission on a £200k job pays for a year.

## Leonide Interiors — kitchen & bathroom showroom

Design, supply, install. Average kitchen probably £15–25k.

| Stage | Today | Hrs | With the tool | Hrs |
|---|---|---|---|---|
| Showroom appointment | Discuss, browse displays | 1.5 | **Three costed directions generated in the room** | 1.5 |
| Home survey | Measure up | 2 | Unchanged | 2 |
| **CAD design** | Build in Winner/ArtiCAD from scratch | **5** | Starts from chosen direction | **2** |
| **Quote build** | Pull product codes, price lists, add install | **3** | Auto-populated from live supplier prices | **1** |
| Presentation | Second appointment | 1.5 | Often merged into the first | 1.5 |
| **Revisions** | Swap quartz→laminate means back into CAD | **3** | Instant re-price | **0.5** |

**16 hrs → 8.5 hrs per lead.**

**Money — but measure conversion, not hours.** Their real loss is 16 unpaid design hours on leads that walk to Wren. Showing a costed concept *during* the first appointment captures the decision at peak interest. Conversion 30% → 38% on a £18k average at 35% margin is roughly **£6,000/month extra gross profit** — an order of magnitude more than the time saving.

**The hook:** "How many hours does a designer spend on someone who never comes back?"

## Amy Drean Interiors — interior design studio

Renovation-led, London period homes, small number of clients per year.

| Stage | Today | Hrs | With the tool | Hrs |
|---|---|---|---|---|
| Discovery + survey | Period property, lots of unknowns | 4 | Unchanged | 4 |
| **Concept development** | Mood boards, sourcing, availability checks | **20** | Retrieval over curated references, region by region | **8** |
| Presentation | Client meeting | 2 | Unchanged | 2 |
| **Revisions (×2)** | Re-source and re-cost by hand | **12** | Change one material, schedule updates | **3** |
| **FF&E + costing schedule** | Every fixture priced manually | **10** | Auto-populated, live supplier pricing | **2.5** |

**48 hrs → 19.5 hrs per project.**

**Money:** ~28 hrs × £60/hr = **£1,700 per project**. At 8 projects a year that's £13,600 against a £6k subscription — and more usefully, it lets them take two extra clients without hiring.

**The hook:** they already advertise *"every fixture costed before site began."* They're doing your product by hand and selling it as their differentiator. You're not persuading them the value exists, only that it can cost them less to deliver. Warmest lead on the list.

## Folly Architects — small residential practice

Extensions, loft conversions, full refurbs. Harrow, RIBA chartered.

Their pain is different — they don't quote construction, so hours-per-quote isn't the pitch.

| Stage | Today | Hrs | With the tool |
|---|---|---|---|
| Free consultation | Unpaid, 1 hr + travel | 1.5 | Unchanged |
| **Feasibility** | Sketch options, vague cost guidance | **8** | **Each option carries a costed range** |
| Planning drawings | Paid, RIBA 1–2 | — | Unchanged |
| Building regs | Paid | — | Unchanged |
| **Tender** | 3 builders, 4-week wait, prices land 40% over budget | — | **No surprise — budget was tested at feasibility** |

The failure mode is stage 5. Client budgeted £120k, tenders come back at £180k, the job dies — and the practice has already done three stages of work it may never bill.

**Money — this is revenue creation, not cost saving:**
- Turn the free feasibility into a chargeable **"feasibility and budget study"** at £750–1,500. Ten a year = **£10k of new revenue from work they currently give away.**
- Avoid one dead project a year: a £150k job at 8% fee = **£12k of fee protected.**

**The hook:** "How many of your projects stall because the tender comes back over budget?" Every residential architect has a recent example and it will still annoy them.

## The pattern

Three of these four buy on **hours**; the showroom buys on **conversion** and the architect buys on **new billable revenue**. Same product, three different first slides. Start with Amy Drean — she's already sold on the value and just needs a cheaper way to deliver it.

## Realistic trajectory

| | Customers | ARR | What it takes |
|---|---|---|---|
| Year 1 | 10–25 | £60k–150k | Founder-led sales, paid pilots |
| Year 2 | 60–120 | £350k–700k | First salesperson, repeatable onboarding |
| Year 3 | 200–400 | £1.2m–2.5m | Small sales team, second room type range |

Those are decent outcomes and probably the honest ceiling of the SMB path.

## What that means

A £2–5m ARR business by year four or five. Genuinely good, likely fundable by angels, and it may not need VC at all.

It is **not** obviously venture scale — which is the same conclusion we reached earlier from a different direction. The routes to venture scale are transaction revenue on materials, or moving up to volume buyers (developers, build-to-rent, national K&B groups) where one contract replaces fifty small ones.

Worth deciding which of those you're aiming at now, because the first ten customers you pick determine which one stays available to you.
