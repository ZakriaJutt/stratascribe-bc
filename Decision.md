# Decision — StrataScribe BC

**Question this file answers:** can a BC strata management brokerage justify paying for StrataScribe BC, and should the founder spend money finding out?

**Decisive pilot question for the whole repository:** can a BC brokerage save measurable time across two authorized meetings *after* a manager corrects motions, votes and bylaw citations?

Status: planning document. Nobody has interviewed a customer. Willingness to pay is unproven.

## How numbers are labelled (used in all ten files)

| Tag | Meaning |
|---|---|
| `[C]` | Stated in the chat (the earlier discussion, received through the decision brief). A price, an offer or a research note, not evidence. The tag covers two layers. **The chat's own answer** said only this: the problem; the buyer (managing broker); audio upload to BC-format minutes plus cited bylaw answers; 17 days; CAD 149 / 349 / 799; gross margin 83%; break-even 5 (35 with salary); the four prospect sources; two free meetings then a 60-day pilot at CAD 299; funnel 150 → about 15 → 7–8 → 2; and the stop rule. **Everything else tagged `[C]`** (for example "3 managers", the qualification rule, building allowances, the weekly plan, objections, competitor notes) comes from the research record the chat's answer was built on. Items that record itself marked "secondary" are called unverified wherever they are used. |
| `[A-chat]` | An **assumption** whose value was stated in the chat. Every unit-economics input is of this kind. |
| `[A]` | An **assumption or proposal** made by the author of these documents. Not decided in chat. |
| `[S: name]` | Taken from a named source that the author opened on 2026-11-10. The source list is in [Sources and assumptions](#12-sources-and-assumptions). |
| `[D]` | Derived by arithmetic from tagged inputs shown beside it. |

"Not decided in chat" means the earlier discussion left the point open. Where that happens this file makes a labelled proposal or states the missing input.

Engineering parameters in the other files (timeouts, retry counts, sizes, retention days, hour estimates, interface dimensions) are all author proposals. Each of those files says so once at the top instead of tagging every value; anything in them that comes from the chat or a source is tagged individually.

## 1. Proposed decision

**Proposal `[A]`: fund the validation phase only (Phase 0 in [execution-plan.md](execution-plan.md)), with a hard cash cap, and do not start building the application until the stop rule in [section 9](#9-stop-rule-checked-against-conversions-sample-size-and-sales-cycle) has been evaluated.**

Reasons, each expanded below:

1. The chat's own funnel and break-even figures cannot both hold inside British Columbia. At the assumed rates, 5 paying accounts needs about 572 distinct brokerages contacted and the chat's 35 needs about 4,000 `[D]`, while the chat's research describes the BC pool as "a few hundred brokerages" `[C]`. See [section 8](#8-funnel-recomputed-from-distinct-reachable-prospects).
2. The BC privacy regulator's guidance says recordings of strata council or general meetings are "likely not authorized by PIPA" unless the strata corporation has passed a bylaw allowing them `[S: OIPC-2022]`. The chat treated recording refusal as a stop condition but assumed a notice script would be enough. This makes "authorized meeting" a qualification question, not a formality.
3. The product's value claim is time saved **after** correction. That can be measured by hand on two meetings per brokerage before any application exists.

The research verdict in the chat was "pursue" with medium evidence confidence `[C]`. This proposal narrows it to "pursue validation; gate the build".

## 2. Who pays, who uses, what is billed

Four things are easy to confuse. They are different records in [schema.md](schema.md) and are kept apart everywhere.

| Term | Definition | Example (synthetic) |
|---|---|---|
| **Paying brokerage** (= one paying account) | One legal entity licensed as a brokerage for strata management services, holding one subscription and receiving one invoice. The tenant boundary. | Harbourline Strata Services Ltd. |
| **Strata manager** (daily user) | A licensed individual employed by the brokerage who attends meetings and writes minutes. A user seat. Seats are not billed. | Priya Nair, Daniel Okafor |
| **Building** (= one strata corporation) | The brokerage's client: "The Owners, Strata Plan …". Owns its bylaws, minutes and recordings. The access boundary inside a brokerage. | Strata Plan ZZS 9001 "Alder Court" |
| **Meeting** | One council meeting, AGM or SGM of one building on one date. The unit of work and of measurement. Not billed. | ZZS 9001 council meeting, 2027-02-09 |

- **One paying account** = one brokerage legal entity with an active subscription or a paid pilot. Branch offices of the same legal entity are the same account `[A]`.
- **One billable unit** = one **active building-month**: a strata corporation with a workspace enabled during the billing month `[A]`. Units are sold in bundles: Starter covers 10 buildings, Pro 30, Business 100, then CAD 15 per additional building per month `[C]`. Meetings and seats are not metered; a fair-use ceiling is not decided in chat.
- **Buyer and budget owner:** the managing broker or director of strata operations `[C]`. The managing broker is also the person the regulator holds responsible for supervision and for the brokerage's records `[S: RESR]`.
- **Not a customer in the MVP:** the strata corporation and its council. They are the source of the personal information and of the authority to record, but they do not pay or log in. The self-managed council plan at CAD 39 per month `[C]` is the chat's pivot option, not part of this pilot.

## 3. Launch market, problem, workaround

| Item | Statement | Label |
|---|---|---|
| Launch market | Licensed strata management brokerages in Metro Vancouver and Victoria | `[C]` |
| Ideal customer | Brokerages with 3–40 strata managers | `[C]` |
| Daily user | Strata manager carrying several buildings, attending evening meetings | `[C]` |
| Current workaround | Handwritten or laptop notes at the meeting, typed into a Word template later; bylaw questions answered from memory or by searching PDFs; some paste text into general chatbots without controls | `[C]`, not measured |
| Buyer's claimed benefit | 12 buildings, about 8 meetings a month, 1.5 hours saved per meeting = 12 hours × CAD 45 = CAD 540 per manager per month | `[A-chat]` (8 × 1.5 × 45 = 540 `[D]`); a modelled assumption, never measured |
| Legal deadline the workflow serves | Under the Standard Bylaws the council must give owners council-meeting minutes within 2 weeks, approved or not. Applies where the strata has not amended that bylaw. | `[S: SPA-SB]` s. 19 |
| Legal content of minutes | The strata corporation must keep minutes of general and council meetings "including the results of any votes" | `[S: SPA]` s. 35(1)(a) |

## 4. Competitor gap, supporting evidence, counterargument

**Vendor-advertised features (read on vendor pages; none is a measured customer outcome):**

| Alternative | What its own page says | Price | Label |
|---|---|---|---|
| Otter.ai | Automated summaries with action items. Per-conversation limits: Basic 30 min, Pro 90 min, Business 4 h. No data-residency statement on the pricing page. | USD: Basic free; Pro 16.99/user/month (8.33 billed annually); Business 30 list (19.99 billed annually) | `[S: Otter]` |
| Fireflies.ai | AI summary, upload of audio files, per-seat plans. | Prices did not render in the page retrieved: **unverified, no source consulted** | `[S: Fireflies]` (features only) |
| Condo Control | Portal with plans by unit band; "Capstan AI" listed under add-ons. No mention of British Columbia or the Strata Property Act on the pricing page. | Not published; custom quote | `[S: CondoControl]` |
| OpenStrata | BC portal for councils: documents, bylaws, minutes, requests, room booking. No AI mentioned. | Not published | `[S: OpenStrata]` |
| StrataPress | Strata websites for self-managed stratas, "about CAD 10 to 15 per unit per year" | **Unverified, no source consulted** (page returned 404 today, as it did for the chat's research) | `[C]` secondary |
| ChatGPT and similar | Not checked today | **Unverified, no source consulted** | — |

**Gap claimed in the chat `[C]`:** no tool found produces BC-format minutes with motions, movers, seconders and vote counts, or answers bylaw questions with citations to the strata's own registered bylaws and the Act. "Not found" is a search result, not proof of absence.

A concrete, sourced difference: a 2-hour meeting `[A-chat]` exceeds Otter Pro's 90-minute per-conversation limit `[S: Otter]`, so the cheapest comparable Otter plan is Business. Compared like for like, for 3 managers, at the scenario rate 1 USD = 1.38 CAD `[A-chat]` (USD→CAD, a scenario assumption, not a sourced rate):

| Billing period | Otter Business, 3 seats | StrataScribe Pro | Ratio |
|---|---|---|---|
| Monthly billing | 3 × USD 30 = USD 90 = CAD 124.20 `[D]` | CAD 349 `[C]` | 349 ÷ 124.20 = **2.81×** `[D]` |
| Annual billing, per month | 3 × USD 19.99 = USD 59.97 = CAD 82.76 `[D]` | 349 × 0.85 = CAD 296.65 (15% annual discount `[C]`) `[D]` | 296.65 ÷ 82.76 = **3.58×** `[D]` |

Otter's page also showed promotional prices on the day; list prices are used. The price premium of roughly three times must be earned by the correction-time difference, which is exactly the pilot question.

**Strongest supporting evidence**

- Global News, 21 March 2023: about 30,000 strata properties in BC, an estimated 1.5 million or more residents, a brokerage president saying the industry runs at about half capacity, and CHOA's executive director saying "200 or 300 managers" would not fill the gaps `[S: GlobalNews]`. This supports a shortage. It does not show that minutes are the binding constraint or that anyone will pay.
- BCFSA's 2026–27 priorities are reported to mention a shortage of licensed professionals and fee-related operating constraints in strata management: **unverified, no source consulted** (search summary only; BCFSA pages returned HTTP 403).

**Strongest counterarguments**

1. **Recording may not be lawful without a bylaw.** OIPC guidance (May 2022): unless the strata corporation passes a bylaw allowing meetings to be recorded, recordings of council or general meetings "are likely not authorized by PIPA" `[S: OIPC-2022]`. A bylaw amendment needs a resolution passed by a 3/4 vote at a general meeting (for an all-residential strata; mixed-use stratas need more) and has no effect until filed in the land title office `[S: SPA]` s. 128. A brokerage cannot fix this for a building inside a 60-day pilot.
2. **"ChatGPT is enough."** The chat itself named this as the idea's weakness, unproven until about 10 manager conversations `[C]`.
3. **Correction may eat the saving.** Poor audio, cross-talk and wrong speaker attribution `[C]` mean the manager may spend as long correcting as writing. Only the after-correction number counts.
4. **The pool is small.** See [section 8](#8-funnel-recomputed-from-distinct-reachable-prospects).
5. **Brokerages are fee constrained and conservative** `[C]`; a new vendor handling owner recordings must pass the managing broker's own confidentiality duty `[S: RESR]` s. 30(e).

## 5. Offer, channel, pilot

| Item | Value | Label |
|---|---|---|
| Free test | Minutes produced free for two real meetings | `[C]` |
| Paid pilot | 60 days, 3 managers, CAD 299 total | `[C]` |
| What the paid pilot delivers before the application exists | A **hand-run service**: for 60 days starting on the date of the first pilot meeting after the invoice is paid, up to 3 managers send authorized recordings or dictated notes; the founder returns a draft of the minutes in BC form by the next business morning, answers bylaw questions by quoting the clause within 1 business day, and reports time saved weekly. Cap: about 12 meetings per brokerage per month. If the application is released during the 60 days, the pilot moves onto it. | `[A]`; the chat did not say how the pilot is delivered or when it starts. Tasks T-0.4.1 and T-0.4.3 in [execution-plan.md](execution-plan.md). |
| When a pilot counts as "paid" | Pilot agreement signed **and** CAD 299 invoice paid. The same event is used by the stop rule, metric M-3, the funnel and the cash table. | `[A]` |
| Pilot success measure | Minutes sent within 3 business days for every meeting | `[C]` |
| Added pilot measure | Net time saved per meeting after correction, see [PRD.md](PRD.md#success-metrics) | `[A]` |
| Tier prices | Starter CAD 149, Pro CAD 349, Business CAD 799 per month | `[C]` |
| Building allowance | 10, 30, 100 buildings; CAD 15 per extra building per month | `[C]` |
| Annual discount | 15% | `[C]` |
| Primary channel | Direct outreach to managing brokers, with the free two-meeting test | `[C]` |
| Backup channel | CHOA, PAMA and CCI Vancouver seminars and newsletters | `[C]` |
| Prospect sources | BCFSA licence search, PAMA, CHOA business members, CCI Vancouver lists; VISOA for self-managed councils (relevant only to the pivot, not used in this pilot) | `[C]` |
| Qualification | Manages 10 or more strata corporations; managers write their own minutes; brokerage permits recording with notice | `[C]` |
| Added qualification | At least two upcoming meetings at buildings whose **filed bylaws authorize recording**, or the brokerage accepts the dictated-notes mode | `[A]`, follows from `[S: OIPC-2022]` |
| Sample inputs needed | Per building: registered bylaws and rules; per meeting: evidence of recording authority, the audio (or the manager's dictated notes), the attendance and vote counts the manager noted; per manager: stopwatch-timed baseline for two meetings written the usual way. The brokerage's own minutes template is **optional**: the pilot uses one standard BC format, and in the hand-run phase the manager pastes the draft into their own template. | `[A]` |
| Sales cycle | 30 days | `[A-chat]` |
| Stop rule | Stop or pivot to self-managed councils if fewer than 2 brokerages pay for a pilot after 150 contacts and 8 demos, or if brokerages refuse recording as policy | `[C]` |

Go-to-market details carried from the chat, unchanged and untested:

| Item | Value | Label |
|---|---|---|
| Buying triggers | A manager resigns; AGM season; owner complaints about late minutes; new buildings without new staff | `[C]` |
| Lead cost | About CAD 80 per 100 prospects (public registries free, one month of LinkedIn Sales Navigator) | `[A-chat]` |
| First-month budget | CAD 700: GPU and hosting 200, Sales Navigator 130, PAMA or CHOA event fee 250, travel 120; 70 founder hours | `[C]` |
| Weekly plan | Week 1: list 150, contact 60, target 6 replies. Week 2: free tests for 5 brokerages, 3 demos. Week 3: contact 90 more, 5 demos, 2 pilot agreements. Week 4: 2 paying brokerages and 1 reference | `[C]` targets |
| Roadmap gates | Week 1: at least 6 of 11 interviewees say minutes take more than 1 hour. Week 2: 2 brokerages agree to a paid pilot. Week 3: managers rate 4 of 5 drafts as needing under 20 minutes of edits. Week 4: 2 paying brokerages and at least CAD 500 in monthly revenue | `[C]` |
| First 1 / 3 / 10 customers | In-person offer to 15 Metro Vancouver brokerages; then the first brokerage's turnaround numbers and a named reference for Victoria and the Fraser Valley; then a PAMA or CHOA education session | `[C]` |
| Referral | One month free per referred brokerage | `[C]`; cost not in the model |
| Partners | PAMA, CHOA, CCI Vancouver, strata lawyers who publish bylaw guidance, BC strata bookkeeping firms | `[C]` |
| Objection: "We cannot rely on AI for legal questions" | It quotes the clause and refuses when it finds none; the manager decides | `[C]`; built as MH-10 |
| Objection: "Councils will not agree to recording" | A notice script; or dictated notes | `[C]`; the notice-script answer is weakened by `[S: OIPC-2022]` |
| Objection: "Condo Control has AI" | That requires their whole portal | `[C]`; their page lists Capstan AI as an add-on `[S: CondoControl]` |
| Switching cost | Upload each building's bylaws once and the minutes template | `[C]` |
| Price bounds in the chat's pricing record | Minimum CAD 39 (council plan), maximum CAD 999, "launch price" CAD 249 | `[C]` |
| Build estimate | 17 days | `[C]` |
| Discovery questions | Five questions for managers and managing brokers | `[C]`; reproduced in full under T-0.1.2 in [execution-plan.md](execution-plan.md#milestone-01--market-and-recording-authority-evidence) |
| Scale path | Alberta and Ontario condo law content; selling through portal vendors as an add-on; the roughly two thirds of BC stratas reported as small and self-managed, with a low-price council plan | `[C]`; deliberately out of this pilot. The "two thirds" figure is unsourced. |
| MVP items in the chat that this plan leaves out | "Upload **or record**" (this plan accepts uploads only); Microsoft 365 or Google Drive export (this plan exports a file); Microsoft Entra or Google sign-in (deferred); magic-link sign-in for councils (no council users) | `[C]` suggestions; departures made by the author `[A]`, listed as non-goals in [PRD.md](PRD.md#non-goals) |
| Suggested hosting in the chat | AWS ca-central-1 with a GPU spot instance or a Canadian inference host; a low-cost hosted LLM | `[C]` suggestion; see decisions AD-3 to AD-5 in [TRD.md](TRD.md#9-architecture-decisions) for why the plan starts elsewhere |

**Dictated-notes mode.** The chat's answer to "councils will not agree to recording" was that managers can dictate notes after the meeting and get the same draft `[C]`. This file treats it as a second, separately measured arm: it avoids recording attendees, but it is a different product test, and whether it can satisfy the stop rule on its own is **not decided in chat**.

## 6. Reconciling tier prices, pilot price and assumed revenue per account

All figures CAD per month unless stated.

1. **Assumed revenue per account: 249** `[A-chat]`. It equals no tier price. The chat's pricing record also lists a "launch price" of CAD 249 `[C]` without saying which plan or allowance it buys; the two figures are probably the same number, but the chat never says so. It is reproduced exactly by a mix of **50% Starter and 50% Pro, no Business, no overage**: 0.5 × 149 + 0.5 × 349 = 74.50 + 174.50 = **249.00** `[D]`. The chat did not state this mix; it is the author's reconciliation `[A]`.
2. **That mix conflicts with the qualification rule.** A qualified brokerage manages 10 or more buildings `[C]`, and three managers at 12 buildings each `[A-chat]` is 36 buildings. Fully onboarded, that is Pro plus 6 extra buildings: 349 + 6 × 15 = **439** `[D]`. So 249 only holds if half the accounts load 10 or fewer buildings (one manager's subset). It is a partial-adoption assumption. Not reconciled further: the true mix is a missing input.
3. **Pilot price: 299 for 60 days** `[C]` = 149.50 per month `[D]`, essentially Starter list price (2 × 149 = 298) for a Pro-sized scope (3 managers). The pilot is therefore a discount on scope, not on price.
4. **Cost side consistency.** The variable cost assumes 20 two-hour meetings per account per month `[A-chat]`. At 8 meetings per manager `[A-chat]` that is 2.5 managers, about 30 buildings: a Pro-sized account. Revenue is assumed at a Starter/Pro blend while cost is assumed at Pro volume. This is conservative on margin for Starter accounts and is left as stated.

## 7. Unit economics

### 7.1 Inputs (all assumptions)

| Cost type | Input | Value (CAD) | Label |
|---|---|---|---|
| Revenue | Revenue per account per month | 249.00 | `[A-chat]` |
| **Variable** | AI (transcription + LLM) | 12.00 | `[A-chat]` |
| **Variable** | Hosting | 6.00 | `[A-chat]` |
| **Variable** | Storage | 2.00 | `[A-chat]` |
| **Variable** | Support (20 minutes per account) | 15.00 | `[A-chat]` |
| **Variable** | Payment processing: 2.9% + 0.30 | 0.029 × 249 + 0.30 = 7.52 | `[A-chat]` rate, `[D]` |
| **Monthly fixed** | Fixed cost excluding founder | 800.00 | `[A-chat]`; composition not decided in chat |
| **Monthly fixed** | Founder compensation | 6,000.00 | `[A-chat]` |
| **Initial acquisition** | The chat's CAC | 600.00 | `[A-chat]`. The chat does not say whether "one customer" is a signed pilot or a retained subscriber. |
| **Initial acquisition** | Acquisition spend per outreach wave of 150 contacts | 1,125.00 | `[D]` = 600 × 1.875 expected pilots: the chat's 600 read as the cost of one signed pilot `[A]` |
| **Initial acquisition** | **CAC as used in this file: spend per converted subscriber** | 1,125 ÷ (1.875 × 0.70) = **857.14** | `[D]` with 70% pilot conversion `[A]` |
| **Churn replacement** | Monthly churn | 2% | `[A-chat]` |
| **Startup** | One-time validation costs not in the chat's line items: lawyer's review of the recording-authority pack, agreement drafting, recording synthetic fixtures | 1,000.00 | `[A]` placeholder; the lawyer's fee has not been quoted |
| **Startup** | Development: 130 hours valued at CAD 100 per hour | 13,000.00 imputed | `[A-chat]`. Not cash if the founder builds it. In "with founder" figures the CAD 6,000 per month already pays for this labour, so the 13,000 is **not** added again. The author's own task estimate is 180–280 hours ([execution-plan.md](execution-plan.md#effort-summary)), which at the same rate is CAD 18,000–28,000 `[D]`. Not reconciled with the 130-hour figure. |

**One CAC unit.** From here on "CAC" means **acquisition spend divided by converted subscribers**: CAD 857.14 in the base case. It is used for payback, churn replacement, both break-evens and the ramp. The chat's own results, which treat 600 as the cost of a subscriber, are shown beside them and marked as the chat's.

AI cost check: 20 meetings × 2 hours = 40 audio hours × CAD 0.20 = CAD 8.00 for transcription `[A-chat]`, `[D]`, leaving CAD 4.00 of the 12.00 for the LLM `[D]`. A pilot of 3 managers at 8 meetings each is 24 meetings, slightly above the 20 assumed: 24 × 2 × 0.20 = CAD 9.60 `[D]`.

### 7.2 Gross profit and payback

- Variable cost per account = 12 + 6 + 2 + 15 + 7.52 = **42.52** `[D]`
- Gross profit per account = 249.00 − 42.52 = **206.48** per month; 206.48 ÷ 249 = **82.9%** `[D]` (the chat's "83%" `[C]`)
- Acquisition payback = 857.14 ÷ 206.48 = **4.15 months** `[D]`. The chat's figure: 600 ÷ 206.48 = 2.91 months `[D]` from `[A-chat]`.
- Lifetime gross profit = 206.48 ÷ 0.02 = **CAD 10,324** `[D]`. This assumes churn stays at 2% forever; it is a formula output, not a forecast.

### 7.3 Churn-replacement cost and break-even

- Churn-replacement cost per account per month = 0.02 × 857.14 = **17.14** `[D]` (the chat's: 0.02 × 600 = 12.00)
- Contribution after replacing churn = 206.48 − 17.14 = **189.34** `[D]` (the chat's: 194.48)

| Break-even | This file (CAC 857.14 per subscriber) | The chat's figures (CAC 600) |
|---|---|---|
| Without founder, with churn replacement | 800 ÷ 189.34 = 4.23 → **5 accounts** `[D]` | 800 ÷ 194.48 = 4.11 → 5 `[D]`, matches chat |
| With founder, with churn replacement | 6,800 ÷ 189.34 = 35.91 → **36 accounts** `[D]` | 6,800 ÷ 194.48 = 34.97 → 35 `[D]`, matches chat |
| Without founder, ignoring churn replacement | 800 ÷ 206.48 = 3.87 → 4 accounts `[D]` | same |
| With founder, ignoring churn replacement | 6,800 ÷ 206.48 = 32.93 → 33 accounts `[D]` | same |

At 36 accounts, steady-state churn replacement is 36 × 0.02 = 0.72 accounts per month × 857.14 = CAD 617 per month `[D]`.

### 7.4 Acquisition cost including founder time

The CAD 857.14 figure is cash-like. The chat's first-month plan is CAD 700 of spend and 70 founder hours `[C]` for an expected 1.875 pilots ([section 8](#8-funnel-recomputed-from-distinct-reachable-prospects)).

- Founder hour = 6,000 ÷ 160 hours = CAD 37.50 `[D]`, with 160 working hours per month `[A]`
- Founder time per outreach wave = 70 × 37.50 = CAD 2,625 `[D]`
- Loaded cost per signed pilot = (700 + 2,625) ÷ 1.875 = **CAD 1,773** `[D]`
- Loaded CAC per converted subscriber at 70% conversion `[A]` = 1,773 ÷ 0.70 = **CAD 2,533** `[D]`; payback 2,533 ÷ 206.48 = **12.3 months** `[D]`
- With this plan's own validation effort of 99–150 hours instead of 70 ([execution-plan.md](execution-plan.md#effort-summary)): (700 + 99 × 37.50) ÷ 1.875 = CAD 2,353 to (700 + 150 × 37.50) ÷ 1.875 = CAD 3,373 per pilot; CAD 3,362 to 4,819 per subscriber `[D]`.
- Cash only, from the chat's CAD 700 budget: 700 ÷ 1.875 = CAD 373 per pilot `[D]`, below the modelled 600.

### 7.5 Pilot economics

- Pilot payment fee = 0.029 × 299 + 0.30 = 8.97 `[D]`
- Pilot variable cost for 60 days = 2 × (12 + 6 + 2 + 15) + 8.97 = 70.00 + 8.97 = 78.97 `[D]`
- Pilot gross profit = 299 − 78.97 = **220.03 for 60 days** `[D]`. One pilot does not repay its own acquisition cost.
- The first pilots are delivered by hand ([section 5](#5-offer-channel-pilot)). The founder's time for that, 24–40 hours per pilot brokerage `[A]` (task T-0.4.3), is not in the variable cost above; at CAD 37.50 per hour it is CAD 900–1,500 per pilot `[D]`, far more than the CAD 299 received. It is carried by founder compensation in the "with founder" columns and is free only in the "no founder" columns.

### 7.6 Cash required during the acquisition ramp

Model rules, so the tables can be rebuilt in a spreadsheet:

1. An outreach **wave** contacts 150 distinct brokerages in one month. Wave spend of CAD 1,125 is booked in that month.
2. Pilots start the month after the wave (30-day sales cycle `[A-chat]`). "Start" means the pilot agreement is signed and the CAD 299 invoice paid; the pilot is delivered by hand until the application exists (T-0.4.1, T-0.4.3). Each pilot pays CAD 299 once, in its start month, and is active for that month and the next.
3. A share of pilots convert (70% base `[A]`, 50% downside `[A]`). They are first billed the monthly revenue **two months after the pilot's start month** (a pilot starting in month 2 is first billed as a subscriber in month 4). Until the application is released they are still served by hand; the model does not add that labour to variable cost.
4. Subscribers billed in month *m* = subscribers of month *m−1* × (1 − churn) + conversions arriving in month *m*.
5. Variable cost = CAD 35.00 per active pilot per month + the pilot payment fee (0.029 × 299 + 0.30, unrounded) per pilot start + variable cost per subscriber.
6. Startup cost CAD 1,000 in month 1. Fixed cost CAD 800 every month. Founder CAD 6,000 every month in the "with founder" columns.
7. Fractions of accounts are expected values, not real customers.
8. The pool is exhausted when the scenario's distinct prospects have been contacted. No churn replacement is bought after that.

**Which cost line sits in which bucket (no line is counted twice).** The chat has two budgets for the same first month: CAD 700 `[C]` and CAD 1,000 `[C]`. They are alternatives, not additive. The model's buckets are larger because they are formula quantities, not a budget.

| Cost line | Chat's 700 budget | Chat's 1,000 budget | Bucket in this model | Model amount, month 1 |
|---|---|---|---|---|
| GPU and hosting | 200 | 300 | Fixed | inside the 800 |
| Sales Navigator / tools | 130 | 200 | Acquisition | inside the 1,125 |
| Association event fee | 250 | 300 | Acquisition | inside the 1,125 |
| Travel and miscellaneous | 120 | 200 | Acquisition | inside the 1,125 |
| Lawyer's review, agreement drafting, synthetic fixtures | not in chat | not in chat | Startup | 1,000 `[A]` |
| Insurance, bookkeeping, memberships | not in chat | not in chat | Fixed | rest of the 800 `[A]` |
| **Total** | **700** `[C]` | **1,000** `[C]` | | **2,925** `[D]` |

Why the model's month 1 (2,925) is above the chat's 700 or 1,000: the acquisition bucket is the modelled 1,125, against 500–700 of matching chat lines; the fixed bucket is the modelled 800, against 200–300 of hosting; and the 1,000 startup line is for items the chat did not budget.

**Base case.** The chat's funnel rates; a reachable pool of 300 distinct brokerages `[A]`, contacted in two waves (months 1 and 4); 70% pilot conversion `[A]`; revenue 249, churn 2%.

| Month | Contacts | Pilots starting | Subscribers billed | Revenue | Variable | Acquisition | Startup | Fixed | Net, no founder | Cumulative, no founder | Cumulative, with founder |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 150 | 0 | 0.000 | 0.00 | 0.00 | 1,125 | 1,000 | 800 | −2,925.00 | −2,925.00 | −8,925.00 |
| 2 | 0 | 1.875 | 0.000 | 560.62 | 82.45 | 0 | 0 | 800 | −321.82 | −3,246.82 | −15,246.82 |
| 3 | 0 | 0 | 0.000 | 0.00 | 65.62 | 0 | 0 | 800 | −865.62 | −4,112.45 | −22,112.45 |
| 4 | 150 | 0 | 1.312 | 326.81 | 55.81 | 1,125 | 0 | 800 | −1,654.00 | −5,766.44 | −29,766.44 |
| 5 | 0 | 1.875 | 1.286 | 880.90 | 137.14 | 0 | 0 | 800 | −56.24 | −5,822.68 | −35,822.68 |
| 6 | 0 | 0 | 1.261 | 313.87 | 119.22 | 0 | 0 | 800 | −605.35 | −6,428.03 | −42,428.03 |
| 7 | 0 | 0 | 2.548 | 634.41 | 108.34 | 0 | 0 | 800 | −273.93 | −6,701.96 | −48,701.96 |
| 8 | 0 | 0 | 2.497 | 621.72 | 106.17 | 0 | 0 | 800 | −284.45 | −6,986.41 | −54,986.41 |
| 9 | 0 | 0 | 2.447 | 609.28 | 104.05 | 0 | 0 | 800 | −294.76 | −7,281.18 | −61,281.18 |
| 10 | 0 | 0 | 2.398 | 597.10 | 101.96 | 0 | 0 | 800 | −304.87 | −7,586.04 | −67,586.04 |
| 11 | 0 | 0 | 2.350 | 585.16 | 99.93 | 0 | 0 | 800 | −314.77 | −7,900.81 | −73,900.81 |
| 12 | 0 | 0 | 2.303 | 573.45 | 97.93 | 0 | 0 | 800 | −324.47 | −8,225.29 | −80,225.29 |

All cells `[D]`, computed from unrounded intermediate values and rounded for display. Worked example, month 5: subscribers = 1.3125 × 0.98 = 1.28625; revenue = 1.875 × 299 + 1.28625 × 249 = 560.625 + 320.276 = 880.90; variable = 1.875 × 35 + 1.875 × 8.971 + 1.28625 × 42.521 = 65.625 + 16.821 + 54.693 = 137.14; net = 880.90 − 137.14 − 800 = −56.24.

**Base-case result:** after contacting every brokerage in a 300-brokerage pool, the business has about 2.3 subscribers and CAD 573 of monthly revenue against CAD 800 of fixed cost. It does not reach break-even even without founder pay. Cash required over 12 months: **CAD 8,225 without founder pay, CAD 80,225 with it** `[D]`, and still rising.

**Downside case.** Pool of 150 `[A]` (one wave); reply rate 5% instead of 10% `[A]`; pilot conversion 50% `[A]`; every converted account on Starter at CAD 149 `[C]` price; churn 4% `[A]`; wave spend unchanged at CAD 1,125.

- Pilots per wave = 150 × 0.05 × 0.50 × 0.25 = 0.9375 `[D]`; spend per pilot = 1,125 ÷ 0.9375 = CAD 1,200 `[D]`
- **CAC per converted subscriber** = 1,125 ÷ (0.9375 × 0.50) = **CAD 2,400** `[D]`
- Payment fee = 0.029 × 149 + 0.30 = 4.62; variable = 35 + 4.62 = 39.62; gross profit = 149 − 39.62 = **109.38 (73.4%)** `[D]`
- Payback = 2,400 ÷ 109.38 = **21.9 months** `[D]`
- Contribution after churn replacement = 109.38 − 0.04 × 2,400 = 109.38 − 96.00 = **13.38** `[D]`
- Break-even = 800 ÷ 13.38 = 59.80 → **60 accounts** without founder; 6,800 ÷ 13.38 = 508.26 → **509 accounts** with founder `[D]`. In this case each subscriber barely pays for replacing the ones that leave.

| Month | Pilots starting | Subscribers billed | Revenue | Variable | Acquisition + startup + fixed | Cumulative, no founder | Cumulative, with founder |
|---|---|---|---|---|---|---|---|
| 1 | 0 | 0.000 | 0.00 | 0.00 | 2,925 | −2,925.00 | −8,925.00 |
| 2 | 0.9375 | 0.000 | 280.31 | 41.22 | 800 | −3,485.91 | −15,485.91 |
| 3 | 0 | 0.000 | 0.00 | 32.81 | 800 | −4,318.72 | −22,318.72 |
| 4 | 0 | 0.469 | 69.84 | 18.57 | 800 | −5,067.45 | −29,067.45 |
| 5 | 0 | 0.450 | 67.05 | 17.83 | 800 | −5,818.23 | −35,818.23 |
| 6 | 0 | 0.432 | 64.37 | 17.12 | 800 | −6,570.98 | −42,570.98 |
| 7 | 0 | 0.415 | 61.79 | 16.43 | 800 | −7,325.62 | −49,325.62 |
| 8 | 0 | 0.398 | 59.32 | 15.77 | 800 | −8,082.07 | −56,082.07 |
| 9 | 0 | 0.382 | 56.95 | 15.14 | 800 | −8,840.26 | −62,840.26 |
| 10 | 0 | 0.367 | 54.67 | 14.54 | 800 | −9,600.13 | −69,600.13 |
| 11 | 0 | 0.352 | 52.48 | 13.96 | 800 | −10,361.60 | −76,361.60 |
| 12 | 0 | 0.338 | 50.38 | 13.40 | 800 | −11,124.62 | −83,124.62 |

All cells `[D]`. In the downside the expected number of pilots after 150 contacts is below 1, so the stop rule should fire at about day 60.

**Cost of reaching the stop decision** (months 1–2 of either case):

| View | Amount (CAD) | What it contains |
|---|---|---|
| The chat's first-month budget | 700 `[C]` | Hosting, Sales Navigator, event fee, travel |
| The chat's 30-day roadmap budget | 1,000 `[C]` | The same lines at higher amounts |
| **This file's cap, without founder pay** | 1,000 + 1,125 + 2 × 800 = **3,725** `[D]` | Two months, not one; the modelled acquisition and fixed buckets; and CAD 1,000 for legal review and other items the chat did not budget |
| This file's cap, with founder pay | 3,725 + 2 × 6,000 = **15,725** `[D]` | As above plus two months of founder compensation |

The cap is 3.7 to 5.3 times the chat's budget `[D]` (3,725 ÷ 1,000; 3,725 ÷ 700) because it covers two months instead of one (the 30-day sales cycle cannot finish in the chat's four weeks), uses the modelled CAD 600 per pilot, and adds legal review. **Proposal `[A]`: the founder plans to the chat's CAD 1,000 for month 1 and treats CAD 3,725 as the ceiling by day 60.** Which figure to hold to is the founder's decision and was not decided in chat.

### 7.7 What would have to be true (thresholds, not forecasts)

| Target | Requirement at 70% pilot conversion and a 300-brokerage pool | Compared with the assumed 1.25% |
|---|---|---|
| 5 subscribers (break-even without founder) | 5 ÷ 0.70 = 7.14 pilots ÷ 300 = 2.4% of all brokerages contacted must buy a pilot `[D]` | About double |
| 36 subscribers (break-even with founder) at CAD 249 | 36 ÷ 0.70 = 51.4 pilots ÷ 300 = 17.1% `[D]` (the chat's 35: 50 pilots, 16.7%) | Not credible from cold outreach |
| With founder, if every account paid Business CAD 799 | Fee 23.47; gross profit 799 − 35 − 23.47 = 740.53; 6,800 ÷ (740.53 − 17.14) = 9.40 → 10 accounts → 14.3 pilots → 4.8% `[D]`. Illustrative only: the CAD 35 variable cost is held constant, which understates cost for a 100-building account. | Requires large accounts |

Conclusion `[A]`: founder-paid break-even inside BC needs fewer, larger accounts (Business tier), or revenue beyond BC brokerages (the council plan, other provinces). Both are outside this pilot. The pilot should therefore record building counts per brokerage so the tier mix stops being a guess.

## 8. Funnel recomputed from distinct reachable prospects

**How many licensed BC strata management brokerages exist?** Not established. BCFSA's licensing-statistics pages and licence search returned HTTP 403 to the author's tools on 2026-11-10, so the count is **unverified, no source consulted**. What is on record:

- The chat's research says "a few hundred brokerages in BC" with no source `[C]`.
- A search-result summary (page not opened) attributes to BCFSA year-end 2023 statistics 1,544 brokerages across **all** real estate categories including branch offices, and 1,503 licensees in the strata category. Unverified; all-category and individual counts are not a strata brokerage count.
- A CTV figure of 1,454 licensed strata managers is "secondary" in the chat's research (the article returned 404) `[C]`.

First task of the plan (T-0.1.1): build the list by hand from the BCFSA licence search and record the count. **Evidence needed to close this:** the count of distinct licence numbers in that list.

**Distinctness rule `[A]`:** one prospect = one brokerage legal entity, keyed by its BCFSA brokerage licence number. PAMA, CHOA and CCI Vancouver listings are matched to that key and add contact names, not prospects. Branch offices and multiple managers at one brokerage are one prospect. "150 contacts" `[C]` is read as 150 distinct brokerages.

| Stage | Rate | Base (pool 300 `[A]`) | Downside (pool 150 `[A]`) |
|---|---|---|---|
| Distinct brokerages reachable | — | 300 | 150 |
| Contacted per wave | — | 150 `[C]` | 150 |
| Replies | 10% `[A-chat]`; downside 5% `[A]` | 15 `[D]` | 7.5 `[D]` |
| Demos | 50% of replies `[A-chat]` | 7.5 `[D]` | 3.75 `[D]` |
| Paid pilots (agreement signed and CAD 299 paid) | 25% of demos `[A-chat]` | 1.875 `[D]` | 0.9375 `[D]` |
| Paying subscribers | 70% `[A]`; downside 50% `[A]` | 1.3125 `[D]` | 0.469 `[D]` |
| Whole pool contacted | — | 3.75 pilots, 2.625 subscribers `[D]` | as above |

- Contact-to-pilot rate = 0.10 × 0.50 × 0.25 = **1.25%** `[D]`. Contact-to-subscriber = 1.25% × 0.70 = **0.875%** `[D]`.
- Distinct brokerages needed for 5 subscribers = 5 ÷ 0.00875 = **571.4, so 572** `[D]`. For the chat's 35 subscribers = 35 ÷ 0.00875 = **4,000** `[D]`; for this file's 36 = 4,114.3, so **4,115** `[D]`.
- The chat's "2 customers" `[C]` is 1.875 rounded up, and it counts pilots, not retained subscribers.
- The chat's funnel says "7–8 demos" while the stop rule names 8 demos `[C]`. The expected number is 7.5.

## 9. Stop rule checked against conversions, sample size and sales cycle

### 9.1 The chat's rule, exactly as stated

> **When to stop (owner's chat, translated):** fewer than 2 pilots after 150 contacts and 8 demos, or firms refuse recording. `[C]`

The chat's research record words the same rule in English as: "Stop or pivot to self-managed councils if fewer than 2 brokerages pay for a pilot after 150 contacts and 8 demos, or if brokerages refuse recording as policy." `[C]`

Read plainly: once 150 contacts and 8 demos have happened, **0 or 1 paid pilot means stop or pivot; 2 or more means go on**. Recording refusal by firms also means stop. **This is the rule in force.** Nothing below replaces it unless the founder adopts the proposal in 9.3 in writing.

### 9.2 Checks on the chat's rule

1. **Against expected conversions.** The expected result is 1.875 pilots, already below the threshold of 2.
2. **Against sample size.** With exactly 8 demos and a true close rate of 25%, the chance of 0 or 1 pilot is 0.75⁸ + 8 × 0.25 × 0.75⁷ = 0.1001 + 0.2670 = **36.7%** `[D]`. Treating the whole funnel as uncertain (Poisson, mean 1.875) it is e^−1.875 × (1 + 1.875) = **44.1%** `[D]`. So the rule stops a venture whose assumptions are all true more than one time in three. If the true close rate were half the assumption (12.5%), the venture would still pass 26.4% of the time `[D]`. Eight demos cannot separate these cases.
3. **Against the demo count.** The rule is worded "after … 8 demos", but the expected number of demos from 150 contacts is 7.5. If demos are Poisson with mean 7.5, the chance of fewer than 8 is **52.5%** `[D]`. The chat does not say what happens if 150 contacts produce fewer than 8 demos. Not decided in chat.
4. **Against the sales cycle.** The weekly plan contacts 60 brokerages in week 1 and 90 in week 3 and expects 2 paying brokerages in week 4 `[C]`. With a 30-day cycle `[A-chat]` the week-3 contacts close around day 51. The week-4 gate is inconsistent with the stated cycle.
5. **Against recording authority.** A building without a recording bylaw cannot supply an "authorized meeting" on the pilot's timescale ([section 4](#4-competitor-gap-supporting-evidence-counterargument)).
6. **Against the chat's own revenue gate.** The week-4 gate is "2 paying brokerages and at least CAD 500 in monthly revenue" `[C]`. Two pilots at CAD 299 for 60 days are 2 × 149.50 = **CAD 299 per month** `[D]`. The gate cannot be met by two pilots at the stated pilot price; it would need two brokerages already on a tier (for example 149 + 349 = 498, still under 500 `[D]`). Not reconciled; this file uses the pilot count, not the CAD 500 figure.

### 9.3 Proposed revision `[A]` — a change to the chat's rule, not a restatement

Every row below is the author's proposal. Rows marked "changed" alter what the chat decided.

| Point | Chat's rule `[C]` | Proposal `[A]` | Status |
|---|---|---|---|
| When to evaluate | After 150 contacts and 8 demos; the weekly plan implies week 4 | Day 60 after first contact, or earlier if all 150 are contacted and every open conversation has closed | **Changed** (adds a date) |
| What counts as a paid pilot | "pay for a pilot" | Pilot agreement signed and the CAD 299 invoice paid, for a pilot first delivered by hand ([section 5](#5-offer-channel-pilot)) | Clarified |
| 0 paid pilots | Stop or pivot | Stop or pivot | Same |
| Exactly 1 paid pilot | **Stop or pivot** | **Inconclusive:** deliver that pilot by hand, spend nothing on Phases 1–6, and decide on its measured time saving at the end of its 60 days | **Changed** |
| 2 or more paid pilots | Continue | Continue to Phase 1 | Same |
| Fewer than 8 demos from 150 contacts | Not stated | Not a stop by itself; the pilot count decides. The demo count is reported in the memo. | **Added** |
| Firms refuse recording | Stop (no number given) | Stop the recorded-audio product if 5 or more of the demoed brokerages (or more than half, if fewer than 8 were demoed) either state a no-recording policy or cannot name two upcoming meetings at buildings with a recording bylaw | **Changed** (adds a number) |
| Spend to this point | CAD 700 / 1,000 budgets | Ceiling CAD 3,725 without founder pay ([section 7.6](#76-cash-required-during-the-acquisition-ramp)) | **Changed** |

Outcome probabilities if every chat assumption is exactly true (pilots Poisson with mean 1.875) `[D]`:

| Outcome | Chat's rule | Proposal |
|---|---|---|
| Stop or pivot | P(0 or 1) = 15.3% + 28.8% = **44.1%** | P(0) = e^−1.875 = **15.3%** |
| Inconclusive | — | P(1) = 1.875 × e^−1.875 = **28.8%** |
| Continue | **55.9%** | **55.9%** |

The proposal does not make a true-assumption venture more likely to continue; it only converts the one-pilot case from "stop" into "measure one pilot before deciding". It also makes a weak venture harder to kill: at half the assumed close rate the mean is 0.9375 pilots and P(exactly 1) is 36.7% `[D]`, all of which the chat's rule would stop. That cost is why this is a proposal for the founder and not a decision. An earlier draft of this section also treated "fewer than 8 demos" as an automatic stop; combined with the 52.5% above, that would have stopped a true-assumption venture 55.6% of the time `[D]`, and it has been removed. The probability that the recording stop fires is unknown: no data exists on how many buildings have recording bylaws.

## 10. What buyer evidence would change the decision

| Evidence | Effect |
|---|---|
| Most interviewed managers say minutes take under 30 minutes | Invalidates the idea `[C]` |
| A firm no-recording policy, or no buildings with a recording bylaw, at most demoed brokerages | Stop the recorded product; consider dictated-notes only, which the chat did not evaluate |
| At least 6 of 11 interviewees say minutes take more than 1 hour per meeting | Passes the chat's week-1 gate `[C]` |
| Managers rate 4 of 5 drafts as needing under 20 minutes of edits | Passes the chat's MVP gate `[C]` |
| Net time saved after correction of 45 minutes or more per meeting on average, and above zero in each of the two authorized meetings `[A]`, with no motion or vote error surviving into approved minutes | Supports continuing. The 45-minute threshold is a plain proposal: half of the assumed 1.5 hours `[A-chat]`. For scale: at 3 managers × 8 meetings × 0.75 h × CAD 45 the saving is worth CAD 810 per month `[D]`, 2.3 times the Pro price of CAD 349; the saving that exactly equals the Pro price for 3 managers is 349 ÷ (3 × 8 × 45) hours = 19.4 minutes per meeting, and for one manager 58.2 minutes `[D]`. Two meetings cannot establish an average; see the note on sample size under M-1 in [PRD.md](PRD.md#how-m-1-is-captured). |
| Brokerages onboard 30 or more buildings each | Moves revenue per account toward Pro and Business and changes [section 7.7](#77-what-would-have-to-be-true-thresholds-not-forecasts) |
| BCFSA count of strata brokerages is well under 300 | Makes the base case optimistic; plan the council or other-province path before building |
| Managers say an existing note-taker plus their template is good enough | The "ChatGPT is enough" weakness is confirmed `[C]` |

## 11. Missing inputs

1. Count of distinct BC brokerages licensed for strata management (BCFSA).
2. Share of buildings whose filed bylaws authorize recording of meetings.
3. Measured baseline minutes-drafting time per meeting type (council, AGM).
4. Tier mix and buildings onboarded per account.
5. Pilot-to-subscription conversion.
6. Whether CAC is per pilot or per subscriber, and the composition of the CAD 800 fixed cost.
7. Location of the founder's VPS and which hosted LLM, if any, can be used with Canadian processing ([TRD.md](TRD.md#9-architecture-decisions)).
8. A BC strata lawyer's view on recording authority, on who must agree in writing before a recording is processed by an outside service, and on whether cited bylaw answers could be treated as legal advice `[C]` risk. The five questions are listed under T-0.1.3 in [execution-plan.md](execution-plan.md).
9. Fair-use ceiling on meetings per building.
10. How often motions at pilot buildings are decided on a show of cards with no count (affects how much of the draft can be checked by arithmetic at all).
11. BC statutory holiday list for the business-day calculation.

## 12. Sources and assumptions

Date consulted for every row: **2026-11-10**. "Opened" means the page content was retrieved and read by the author's tools on that date.

| ID | Source | Jurisdiction | Scope used | Access |
|---|---|---|---|---|
| SPA | *Strata Property Act*, SBC 1998 c. 43, BC Laws, Parts 1, 4 and 7 (`bclaws.gov.bc.ca/civix/document/id/complete/statreg/98043_01`, `_04`, `_07`) | British Columbia | s. 1 definitions of majority vote, 3/4 vote, 80% vote, unanimous vote; s. 35 records including minutes with vote results, and bylaws and rules; s. 36 access to records (owners, tenants with assigned rights, persons authorized in writing, former owners); s. 36(3) within 2 weeks, or one week for bylaws or rules; s. 37 return of records within 4 weeks after a management contract ends; s. 45 two weeks' notice; s. 48(1) no business without a quorum; s. 48(2)(a) quorum 1/3 of votes, subject to the bylaws; s. 48(2)(b) 2/3 where there are fewer than 4 strata lots or fewer than 4 owners; s. 48(3) unless the bylaws provide otherwise, no quorum within half an hour adjourns the meeting one week and those present at the adjourned meeting are a quorum; s. 49 electronic attendance; s. 50 voting; ss. 119–128 bylaws, rules, 3/4 vote amendment, no effect until filed | Opened. Consolidation current to 2026-11-03. Part 4 was opened three times on 2026-11-10; the third reading (fix round 1) supplied s. 36(3) and s. 48(2)(b) and (3). Any special treatment in s. 48(3) of meetings called by voters was not captured and must be read before the adjourned-meeting rule is relied on. |
| SPA-SB | Schedule of Standard Bylaws to the Act (`…/98043_18`) | British Columbia | s. 16(1) council quorum: 1 for a council of 1; 2 for 2, 3 or 4; 3 for 5 or 6; 4 for 7; s. 16(2) present in person; s. 17 council meetings, electronic means, owners as observers; s. 18(1) majority of council members present; s. 18(2) president's second, deciding vote on a tie, not where there are only 2 strata lots; s. 18(3) results of all council votes recorded in the minutes; s. 19 minutes to owners within 2 weeks; s. 27(2) show of voting cards unless a precise count is requested; s. 27(3) chair decides the method of a precise count; s. 27(4) outcome announced and recorded, with numbers for and against only if a precise count was requested; s. 27(5)–(6) president's (or vice president's) second, deciding vote on a tie, not where there are only 2 strata lots; s. 27(7) secret ballot on request; s. 28 order of business | Opened twice on 2026-11-10; the second reading (fix round 1) supplied ss. 16, 18 and 27 in detail. Current to 2026-11-03. Read through a summarising tool with short quotations, so the wording here is a paraphrase; T-4.1.2 transcribes the text itself. |
| SPR | *Strata Property Regulation*, B.C. Reg. 43/2000 (`…/12_43_2000`) | British Columbia | s. 4.1(3) records under Act s. 35(1)(a), which includes minutes, kept at least 6 years; s. 4.1(6) current copies of bylaws and rules; s. 4.2 maximum copy fee 25 cents per page, no inspection fee | Opened; first 100,000 characters read. Current to 2026-11-03. |
| PIPA | *Personal Information Protection Act*, SBC 2003 c. 63 (`…/03063_01`) | British Columbia | s. 4(2) responsibility for information not in custody; s. 6 consent; s. 7; s. 8 implied consent and opt-out notice; s. 10 notification of purposes; s. 23 access; s. 34 reasonable security; s. 35 retention at least 1 year after use in a decision, then destroy when no longer needed | Opened. Current to 2026-11-03. The page read contains no provision on storage outside Canada. |
| OIPC-2022 | Office of the Information and Privacy Commissioner for BC, "Privacy guidelines for strata corporations and strata agents" (`oipc.bc.ca/guidance-documents/3632`) | British Columbia | Recording of meetings likely not authorized by PIPA without a bylaw; implied consent to be named in minutes; minutes need not include exact discussion; use unit or strata lot number for sensitive matters; disclosure to a property manager with contractual restriction; SPA authorizes collection to create minutes | Opened as PDF and text extracted by the author's own parser. Embedded creation timestamp is May 2022, matching the BC government page's description; the visible date was not confirmed. Guidance, not law. Two other OIPC URLs (documents 1455 and 1805) returned "file not found". |
| RESR | *Real Estate Services Rules*, B.C. Reg. 209/2021 (`…/209_2021`) | British Columbia | s. 28 managing broker supervision and records; s. 30(e) confidentiality; s. 43(6)(f)–(g) service agreement terms on records and information; s. 88 strata management records (accounting records; minutes not listed); s. 91 electronic records; s. 92 retention at least 7 years, available at head office | Opened in two parts. Current to 2026-11-03. No rule read requires records to be stored in British Columbia. |
| BCGov | Government of BC strata pages: "Strata property manager licensing" and "Information and record keeping" (`www2.gov.bc.ca`) | British Columbia | BCFSA licenses brokerages and individual managers under the *Real Estate Services Act*; each brokerage has a managing broker; minutes kept at least six years; stratas must comply with PIPA | Opened. Page dates July 2024. |
| BCFSA | BCFSA licensing statistics and licence search (`bcfsa.ca`) | British Columbia | Count of brokerages licensed for strata management | **Blocked: HTTP 403 on every attempt. Unverified, no source consulted.** |
| Otter | Otter.ai pricing page (`otter.ai/pricing`) | Vendor, USD | Plan prices and per-conversation limits | Opened. Vendor-advertised. |
| Fireflies | Fireflies.ai pricing page (`fireflies.ai/pricing`) | Vendor | Feature list only | Opened; prices did not render. Prices unverified, no source consulted. |
| CondoControl | Condo Control pricing page (`condocontrol.com/pricing/`) | Vendor, Canada and US | No published prices; Capstan AI under add-ons | Opened. |
| OpenStrata | OpenStrata site (`openstrata-site.pages.dev`) | Vendor, BC | Feature list; no AI; no price | Opened. |
| StrataPress | `stratapress.com/premium-strata-websites/` | Vendor, BC | Price claim | **HTTP 404. Unverified, no source consulted.** |
| GlobalNews | Global News, "B.C. strata property manager shortage", 2023-03-21 (`globalnews.ca/news/9568141/…`) | British Columbia | Shortage figures | Opened. Journalism quoting industry figures. |
| SpecKit | GitHub Spec Kit README (`github.com/github/spec-kit`) | — | Method: specification states what and why; plan states technical choices; tasks derived from the plan | Opened. Used to keep outcomes in `PRD.md`, choices in `TRD.md`, and independently checkable tasks in `execution-plan.md`. |
| arc42 | arc42 overview (`arc42.org/overview/`) | — | The twelve-section template | Opened. `TRD.md` follows the twelve sections. |

Claims carried from the chat that the author could **not** verify and that stay unverified: the CTV count of licensed managers; StrataPress pricing; the REMI Network advice that AI minutes be reviewed before distribution; the BCFSA priorities statement; the count of BC brokerages; every unit-economics input; every funnel rate.

Not consulted by the author: OWASP ASVS and the WCAG 2.2 quick reference. The independent reviewer consulted OWASP ASVS 5.0.0 and the WCAG 2.2 Recommendation on 2026-11-10; requirement and criterion IDs in [TRD.md](TRD.md) and [design.md](design.md) are cited on the reviewer's reading, not the author's. BC statutory holidays used in the business-day calculation were not looked up: unverified, no source consulted (to be taken from the BC government list in T-5.1.2).

Exchange rates: only one conversion is used (section 4), at the chat's scenario rate 1 USD = 1.38 CAD `[A-chat]`, direction USD→CAD, a scenario assumption and not a sourced rate. All economics are in CAD per month.
