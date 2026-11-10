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
| `[S: name]` | Taken from a named source that the author opened on 2026-11-10. The source list is in [Sources and assumptions](#13-sources-and-assumptions). |
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

**Base-case result:** after contacting every brokerage in a 300-brokerage pool, the business has about 2.3 subscribers and CAD 573 of monthly revenue against CAD 800 of fixed cost. It does not reach break-even even without founder pay. Cash required over 12 months: **CAD 8,225 without founder pay, CAD 80,225 with it** `[D]`, and still rising. Both are counted from the first contact. The preparation fortnight before it ([section 12.8](#128-first-30-60-and-90-days)) is deliberately outside this table; with it the figures are 8,225.29 + 400 = **CAD 8,625** and 80,225.29 + 3,400 = **CAD 83,625** `[D]`.

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

All cells `[D]`. In the downside the expected number of pilots after 150 contacts is below 1, so the stop rule should fire at about day 60. With the preparation fortnight the month-12 figures are 11,124.62 + 400 = CAD 11,525 and 83,124.62 + 3,400 = CAD 86,525 `[D]`.

**Cost of reaching the stop decision** (months 1–2 of either case):

| View | Amount (CAD) | What it contains |
|---|---|---|
| The chat's first-month budget | 700 `[C]` | Hosting, Sales Navigator, event fee, travel |
| The chat's 30-day roadmap budget | 1,000 `[C]` | The same lines at higher amounts |
| **This file's cap, without founder pay** | 1,000 + 1,125 + 2 × 800 = **3,725** `[D]` | Two months, not one; the modelled acquisition and fixed buckets; and CAD 1,000 for legal review and other items the chat did not budget |
| This file's cap, with founder pay | 3,725 + 2 × 6,000 = **15,725** `[D]` | As above plus two months of founder compensation |
| **The same caps counted from the start of preparation** | 3,725 + 400 = **4,125**; 15,725 + 3,400 = **19,125** `[D]` | Adds the preparation fortnight before the first contact: half a month of fixed cost (0.5 × 800) and, with founder pay, half a month of compensation (0.5 × 6,000) `[A]`; see [section 12.8](#128-first-30-60-and-90-days) |

The cap is 3.7 to 5.3 times the chat's budget `[D]` (3,725 ÷ 1,000; 3,725 ÷ 700) because it covers two months instead of one (the 30-day sales cycle cannot finish in the chat's four weeks), uses the modelled CAD 600 per pilot, and adds legal review. **Proposal `[A]`: the founder plans to the chat's CAD 1,000 for month 1 and treats CAD 3,725 as the ceiling by day 60 after the first contact, which is CAD 4,125 counted from the start of preparation.** The 3,725 and 15,725 figures in this section are the preparation-exclusive ones on purpose, because the ramp counts months from the first contact; the stop-rule memo reports spend against 4,125 (19,125 with founder pay). Which figure to hold to is the founder's decision and was not decided in chat.

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
| When to evaluate | After 150 contacts and 8 demos; the weekly plan implies week 4 | Day 60 after first contact, or earlier if all 150 are contacted and every open conversation has closed. If on day 60 a signed pilot is unpaid or a free test is still running and could change the outcome, the memo is provisional and is closed by day 74 ([section 12.9](#129-gtm-stop-rule)) | **Changed** (adds a date and a 14-day close-out) |
| What counts as a paid pilot | "pay for a pilot" | Pilot agreement signed and the CAD 299 invoice paid, for a pilot first delivered by hand ([section 5](#5-offer-channel-pilot)) | Clarified |
| 0 paid pilots | Stop or pivot | Stop or pivot | Same |
| Exactly 1 paid pilot | **Stop or pivot** | **Inconclusive:** deliver that pilot by hand, spend nothing on Phases 1–6, and decide on its measured time saving at the end of its 60 days | **Changed** |
| 2 or more paid pilots | Continue | Continue to Phase 1 | Same |
| Fewer than 8 demos from 150 contacts | Not stated | Not a stop by itself; the pilot count decides. The demo count is reported in the memo. | **Added** |
| Firms refuse recording | Stop (no number given) | Stop the recorded-audio product if 5 or more of the demoed brokerages (or more than half, if fewer than 8 were demoed) either state a no-recording policy or cannot name two upcoming meetings at buildings with a recording bylaw | **Changed** (adds a number) |
| Spend to this point | CAD 700 / 1,000 budgets | Ceiling CAD 3,725 without founder pay from the first contact; CAD 4,125 from the start of preparation ([section 7.6](#76-cash-required-during-the-acquisition-ramp)) | **Changed** |

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
8. A BC strata lawyer's view on recording authority, on who must agree in writing before a recording is processed by an outside service, and on whether cited bylaw answers could be treated as legal advice `[C]` risk. The first five of the six questions listed under T-0.1.3 cover these in [execution-plan.md](execution-plan.md).
9. Fair-use ceiling on meetings per building.
10. How often motions at pilot buildings are decided on a show of cards with no count (affects how much of the draft can be checked by arithmetic at all).
11. BC statutory holiday list for the business-day calculation.
12. The lawyer's answer on outreach (question 6 of T-0.1.3). The statute and both regulations were read ([section 12.4](#124-channel-and-sequence)); what stays open is judgment: whether an association directory listing counts as an address the recipient caused to be published, whether the sender block is sufficient, and whether a LinkedIn connection note is a commercial electronic message. Telemarketing rules for calls to businesses: unverified, no source consulted.
13. The share of the 150 brokerages whose managing broker has an email address published on the brokerage's own website (sets the mix of email and phone first touches).

## 12. Go-to-market plan

Added 2026-11-10 at the owner's request, after the independent review, and revised the same day after the reviewer's findings F-027 to F-030. Nothing here has been tried: no message has been sent and no prospect has been called. This section arranges what sections 2 to 11 already decide into a plan for the first paying accounts and cites them instead of repeating them. Every rate is an assumption. Tasks are in Phase 0 of [execution-plan.md](execution-plan.md#phase-0--validation-by-hand-no-application).

### 12.1 Ideal customer profile

| Item | Value | Label |
|---|---|---|
| Firm type | A brokerage licensed by BCFSA for strata management services; one legal entity is one prospect ([section 8](#8-funnel-recomputed-from-distinct-reachable-prospects)) | `[C]`, `[A]` distinctness rule |
| Size | 3–40 strata managers; 5–80 employees; 10 or more strata corporations under management | `[C]` |
| Region | Metro Vancouver and Victoria first; the Fraser Valley for the second and third accounts | `[C]` |
| Trigger | One of the four buying triggers in [section 5](#5-offer-channel-pilot): a manager resigns, AGM season, owner complaints about late minutes, new buildings without new staff | `[C]`, untested |
| Qualified when | The two qualification rows of [section 5](#5-offer-channel-pilot) both hold: the chat's rule `[C]` and the added rule on two upcoming authorized meetings or dictated notes `[A]` | — |

**Disqualifiers** `[A]`, each the negative of a rule already in this file. A prospect is dropped from the wave, and logged with the reason, when:

1. it manages fewer than 10 strata corporations `[C]`;
2. its managers do not write their own minutes `[C]` (someone else already does it, so no manager time is saved);
3. it has a firm no-recording policy **and** refuses the dictated-notes mode; this also counts toward the recording stop in [section 9.3](#93-proposed-revision-a--a-change-to-the-chats-rule-not-a-restatement);
4. it cannot name two upcoming meetings at buildings whose filed bylaws allow recording **and** refuses dictated notes `[S: OIPC-2022]`;
5. its managing broker will not sign the hand-run agreement (T-0.3.2), or a council withholds the written acknowledgement that the protocol requires until the lawyer answers question 4 of T-0.1.3;
6. it is a self-managed council or is outside British Columbia: those belong to the pivot and the scale path, not to this plan `[C]`.

### 12.2 Named roles

| Role in the sale | Who | Why | Label |
|---|---|---|---|
| Feels the pain | The strata manager, who writes minutes after evening meetings and answers repeat bylaw questions | [Section 3](#3-launch-market-problem-workaround) | `[C]`, not measured |
| Signs and pays | The managing broker or director of strata operations: signs the hand-run agreement (T-0.3.2) and the pilot agreement (T-0.4.1) and pays the CAD 299 invoice | [Section 2](#2-who-pays-who-uses-what-is-billed) | `[C]` |
| Can block | (1) The strata council of each building: recording authority comes from the strata corporation's filed bylaws and the brokerage cannot supply it. (2) The managing broker in their supervisory role: a new vendor handling owner recordings must pass their confidentiality duty. (3) Whoever approves software at the brokerage. | (1) `[S: OIPC-2022]`, `[S: SPA]` s. 128; (2) `[S: RESR]` s. 30(e); (3) "brokerage IT approval" is a dependency named in the chat's research `[C]` | as shown |
| Supplies the sample data | The strata manager supplies the per-building and per-meeting inputs and the stopwatch baseline listed under "Sample inputs needed" in [section 5](#5-offer-channel-pilot); the managing broker supplies the signed agreement and the building counts | `[A]` | `[A]` |

### 12.3 Prospect list

- **Sources:** the "Prospect sources" row of [section 5](#5-offer-channel-pilot) `[C]`. LinkedIn Sales Navigator `[C]` is used to find names only. The BCFSA licence search defines the prospects; PAMA, CHOA and CCI Vancouver listings only add a named contact to a licence number ([section 8](#8-funnel-recomputed-from-distinct-reachable-prospects)).
- **How many exist:** not established ([section 11](#11-missing-inputs), item 1). The plan uses the two pools of [section 8](#8-funnel-recomputed-from-distinct-reachable-prospects): 300 distinct brokerages in the base case `[A]` and 150 in the downside `[A]`. The first wave needs 150 `[C]`.
- **How it is built:** task T-0.1.1, subtasks (a) to (f), 6–10 founder hours `[A]`. Subtask (c) records, for each email address, where the recipient published it, the date seen and that no refusal statement was beside it; an address without that record is marked "phone or visit only" (12.4).
- **How it is checked:** the acceptance check of T-0.1.1 (a second person finds 10 random rows in the BCFSA search; no licence number twice). The sales log of T-0.2.1 is keyed by the same licence number, so a brokerage cannot be contacted or counted twice.
- **Cost:** about CAD 80 per 100 prospects `[A-chat]`, so 150 × 0.80 = CAD 120 for the first wave `[D]`. It sits inside the acquisition bucket of [section 7.6](#76-cash-required-during-the-acquisition-ramp), not on top of it.
- **If the count is under 150:** the first wave is the whole pool, every expected value in 12.8 scales down in proportion, and the last row of [section 10](#10-what-buyer-evidence-would-change-the-decision) applies.

### 12.4 Channel and sequence

**First channel to test:** direct outreach to the managing broker with the free two-meeting test `[C]`. The backup channel (association seminars and newsletters `[C]`) is used only if the channel check in 12.9 fails.

| Step | When | What | Label |
|---|---|---|---|
| 0 | Preparation, about 14 days before the first contact `[A]` | The list is built with a consent record for each email address (T-0.1.1); the authority pack and six questions go to the lawyer (T-0.1.3). **No first touch of any kind is made until the lawyer's written answer to question 6 is in hand.** | `[A]`; follows from `[S: CASL]` |
| 1 | Day 0 for that brokerage | First touch to the managing broker by name. **By email** (text in 12.5) only where the list holds a consent record for that address; **by phone** (call script in 12.5) for every other brokerage. LinkedIn is used to find the managing broker's name and nothing else: no connection request, note or message is sent there in this wave. | `[C]` channel; `[A]` wording and channel rule |
| 2 | 5 business days `[A]` later | One follow-up `[A]`: by phone where a number is listed, asking for the managing broker and avoiding Monday mornings and AGM evenings `[C]`; otherwise by email (text in 12.5), and only to an address that has a consent record. No third touch `[A]`. | T-0.2.1 subtask (e); `[C]` call advice |
| 3 | On a reply | A 20-minute `[A]` call or visit: the five discovery questions and two added ones (T-0.1.2), then the demo and qualification record (T-0.2.2) | `[C]`, `[A]` |
| 4 | After a qualified demo | Hand-run agreement signed, then the free two-meeting test (T-0.3.2 to T-0.3.4) | `[C]` offer; `[A]` protocol |
| 5 | After the measurement table is shown | Pilot agreement and CAD 299 invoice (T-0.4.1) | `[C]` |

Anyone who unsubscribes, or says no by any means, goes on a suppression list in the sales log and is not contacted again.

**Canada's anti-spam legislation: what the text says, and what is left to the lawyer.** This is the author's reading of the statute and two regulations, opened on 2026-11-10 (rows CASL, CASL-CRTC and CASL-GIC in [section 13](#13-sources-and-assumptions)). **It is not legal advice**, and no message is sent on the strength of it: the lawyer's answer to question 6 of T-0.1.3 comes first.

| Point | What the source says | What this plan does | Left to the lawyer |
|---|---|---|---|
| Is the first-touch email covered? | A commercial electronic message is one whose purpose, or one of whose purposes, is to encourage participation in a commercial activity, including an offer to sell a service `[S: CASL]` s. 1(2). It may be sent to an electronic address only with express or implied consent **and** in the required form, s. 6(1). | Both email texts are treated as commercial electronic messages, although the test they offer is free. | — |
| Consent for a cold email | Consent is implied only in listed cases. The one that can fit a cold contact: the recipient "has conspicuously published, or has caused to be conspicuously published" the address, the publication carries no statement refusing unsolicited commercial messages, and the message is relevant to the recipient's business or role, s. 10(9)(b). The sender has the onus of proving consent, s. 13. The exclusion for messages between organizations needs an existing relationship `[S: CASL-GIC]` s. 3(a)(ii), which a cold contact lacks. | Email is used only where the list records, per address: the address, the page on which the recipient or their brokerage published it, the date seen, and that no refusal statement was beside it (T-0.1.1). The message is about minutes written by the brokerage's managers, which is within a managing broker's role. Addresses taken from Sales Navigator, guessed from a pattern, or found only in a third party's list get no email. | Whether a listing in an association's member directory counts as "caused to be published" by the recipient (question 6(a)). Until answered, only addresses on the brokerage's own website count. |
| Form of every email, first touch and follow-up | The message must identify the sender, give contact information and set out an unsubscribe mechanism, s. 6(2). Required: the sender's name or business name; the mailing address; and a telephone number, an email address or a web address `[S: CASL-CRTC]` s. 2(1); set out clearly and prominently, s. 3(1). The mechanism must name an electronic address or link to a web page to which the wish can be sent, at no cost, s. 11(1); a request takes effect within 10 business days, s. 11(3); the contact information and the mechanism stay valid for at least 60 days, ss. 6(3) and 11(2). | Both email texts in 12.5 end with a block holding the name, mailing address, telephone number, email address and an unsubscribe line naming an address. The founder keeps that address working for 60 days after the last send and acts on each request the same day. | Whether the block as drafted is sufficient (question 6(b)). |
| Phone call and voicemail | Section 6 does not apply to a message that is an interactive two-way voice communication between individuals, or a voice recording sent to a telephone account, s. 6(8)(a) and (c). | A phone first touch or follow-up, with or without a voicemail, is used where email has no consent record. | Telemarketing rules for calls to businesses were **not checked: unverified, no source consulted** (question 6(d)). |
| LinkedIn | "Electronic address" includes an instant messaging account and "any similar account", s. 1(1). Messages on a messaging service are excluded only if the required information and unsubscribe mechanism are published on the service's interface and the recipient consents expressly or by implication `[S: CASL-GIC]` s. 3(d). | No commercial message is sent on LinkedIn in the first wave, so no consent basis is claimed for it. The chat's connection text and follow-up `[C]` are not used. | Whether a connection request with a note is a commercial electronic message, and whether s. 3(d) could cover it (question 6(c)). |
| Exposure | The maximum penalty for a violation is CAD 1,000,000 for an individual, s. 20(4). | Stated so the cost of skipping step 0 is visible. | — |

**Weekly volume for one founder, and the paying accounts it yields.** The chat's weekly plan sends 60 first touches in week 1 and 90 in week 3 `[C]`. This plan keeps the two cohort sizes and sends the 90 in week 4 `[A]`, one week later, so that the message check in 12.9 can be read before they go. Both cohorts are still contacted in month 1, so no month of the ramp in [section 7.6](#76-cash-required-during-the-acquisition-ramp) moves. Rates are the chat's `[A-chat]`; pilot conversion is the author's 70% `[A]`.

| Cohort | First touches | Replies (10%) | Demos (50%) | Paid pilots (25%) | Recurring accounts (70%) |
|---|---|---|---|---|---|
| Week 1 | 60 `[C]` | 6 `[D]` | 3 `[D]` | 0.75 `[D]` | 0.525 `[D]` |
| Week 4 | 90 `[C]` | 9 `[D]` | 4.5 `[D]` | 1.125 `[D]` | 0.7875 `[D]` |
| **Wave (one month of outreach)** | **150** | **15** | **7.5** | **1.875** | **1.3125** |

- Check: 60 × 0.10 × 0.50 × 0.25 = 0.75; 90 × 0.10 × 0.50 × 0.25 = 1.125; 0.75 + 1.125 = **1.875** paid pilots; 1.875 × 0.70 = **1.3125** recurring accounts `[D]`. These are the "Paid pilots" and "Paying subscribers" rows of [section 8](#8-funnel-recomputed-from-distinct-reachable-prospects).
- Paying accounts by month, counted from the first contact, using the definition of one paying account in [section 2](#2-who-pays-who-uses-what-is-billed) and rules 2 and 3 of [section 7.6](#76-cash-required-during-the-acquisition-ramp): month 1, **0**; month 2, **1.875** paid pilots start; month 3, the same 1.875 pilots, no new account; month 4, **1.3125** recurring accounts first billed. These are the "Pilots starting" and "Subscribers billed" cells of months 1 to 4 in the base-case table (0, 1.875, 0, 1.312) `[D]`.
- The base case sends one wave every three months (months 1 and 4) until the pool of 300 `[A]` is used up, so the average is 1.875 ÷ 3 = 0.625 new paid pilots and 1.3125 ÷ 3 = 0.4375 new recurring accounts per month `[D]`. Two waves give 3.75 pilots and 2.625 recurring accounts `[D]`, the last row of the funnel table.
- Workload: T-0.2.1 allows 20–30 hours `[A]` for 150 first touches and their follow-ups, which is 8–12 minutes per brokerage `[D]` (20 × 60 ÷ 150; 30 × 60 ÷ 150). Week 1 is therefore 8–12 hours of first touches and week 2 about 54 follow-ups (60 less 6 expected replies `[D]`); week 4 is 12–18 hours and week 5 about 81 follow-ups (90 less 9 `[D]`). What limits the plan is not sending but delivery: at most 2 hand-run pilot brokerages at once ([execution-plan.md](execution-plan.md#milestone-04--paid-pilot-agreement-and-stop-rule)) `[A]`, which the expected 1.875 just fits.
- The mix of email and phone first touches is unknown until the list is built. The 10% reply rate `[A-chat]` and the 8–12 minutes are **assumed** to hold whatever the mix `[A]`; the chat gave one rate and did not separate channels. A phone-heavy wave is likely to take longer per brokerage, and in-person visits (the chat's "first customer" plan uses them for 15 brokerages `[C]`) do not fit in 12 minutes. Neither is re-estimated here: the sales log records channel and minutes per brokerage so that the rate and the hours can be restated in the stop-rule memo.

### 12.5 Message

All three texts are synthetic drafts `[A]`, written to the invented managing broker "Marta" at the invented Harbourline Strata Services Ltd. They replace the chat's draft email and LinkedIn messages `[C]`, which offered to process past meeting recordings and said nothing about recording authority. None says recording is permitted. None says where files are stored: the location of the founder's server is unconfirmed ([section 11](#11-missing-inputs), item 7), so the texts state only that drafting uses models on the founder's own computer, which the protocol under T-0.3.2 requires. If asked, the founder says the server's location is being confirmed and offers to collect files in person, which the protocol allows.

**First touch (email, only to an address with a consent record)**

> Subject: Timing the minutes for two Harbourline council meetings
>
> Hi Marta,
>
> I am a Vancouver developer testing a minutes-drafting service for BC strata managers. I have no customers yet, so I am offering a free test. For two upcoming meetings, one of your managers sends me a recording or their own dictated notes, and by the next business morning gets a draft in BC form, with motions, movers, seconders and outcomes, to correct. The manager times their usual method and the correction with a stopwatch, and you see the difference in minutes.
>
> One condition matters. Guidance from the BC privacy commissioner says recording a strata meeting is likely not authorized unless the strata's own bylaws allow it. I cannot tell you that recording is permitted at your buildings. I accept a recording only from a building whose filed bylaws allow it; for any other building I work from notes the manager dictates after the meeting.
>
> What I would need from you: two upcoming meetings; the bylaws and rules of those buildings; the attendance and vote notes your manager already takes; two sets of minutes timed the usual way; your signature on a one-page data-handling agreement; and, until my lawyer confirms otherwise, a written acknowledgement from each council. Drafts are made with models that run on my own computer, not by a hosted AI service, and your files are deleted on a fixed schedule.
>
> If the test shows a real saving after correction, the next step is a 60-day pilot for up to 3 managers at CAD 299 in total. If it does not, you owe nothing and I will tell you so.
>
> Would a 20-minute call next week be useful?
>
> [Founder's full name], [business name, if one is registered]
> [Street address, city, BC, postal code]
> [Telephone number] · [founder's email address]
> I found your address on [page where it is published]. If you do not want further email from me, reply "unsubscribe" or write to unsubscribe@[founder's domain] and I will stop.

**Follow-up (5 business days later; the only one). By email, only to an address with a consent record:**

> Hi Marta,
>
> One follow-up on my note of [date]; I will not send another. The offer is a free test on two upcoming council meetings: a draft of the minutes by the next business morning, and a stopwatch comparison against the way your manager writes them now. If it saves time after correction, a 60-day pilot for up to 3 managers is CAD 299 in total.
>
> It would need the same things from Harbourline as before: two meetings at buildings whose filed bylaws allow recording, or a manager willing to dictate notes afterwards instead; those buildings' bylaws and rules; the manager's attendance and vote notes; two sets of minutes timed the usual way; a one-page data-handling agreement signed by you; and, until my lawyer confirms otherwise, a written acknowledgement from each council. If none of your buildings has a recording bylaw, that is worth knowing too, and the dictated-notes test still works.
>
> Is there a manager I should speak to?
>
> [Founder's full name], [business name, if one is registered]
> [Street address, city, BC, postal code]
> [Telephone number] · [founder's email address]
> If you do not want further email from me, reply "unsubscribe" or write to unsubscribe@[founder's domain] and I will stop.

**Call script (phone first touch, or phone follow-up; about one minute)**

> "Hello, my name is [name]. I am a developer in Vancouver, and I am calling for Marta, the managing broker. Is this a bad moment?"
>
> If it is: "When would be better?" Note the time and end the call.
>
> Otherwise: "I am testing a service that drafts strata council minutes for the manager to correct. I have no customers yet. I would like to run a free test on two of your upcoming meetings and time it against how your manager writes minutes now. I can take a recording only from a building whose filed bylaws allow recording; I cannot tell you whether yours do. Otherwise your manager dictates notes after the meeting. It would need the buildings' bylaws, your manager's vote notes, two timed sets of minutes, a one-page agreement from you and, for now, a written acknowledgement from each council. If it saves time, a 60-day pilot for up to 3 managers is CAD 299 in total. Could I have 20 minutes with you or one of your managers next week?"
>
> If no: "Thank you. I will not call again." Mark the brokerage as declined.
>
> Voicemail: name, telephone number, "a free test of minutes drafting for two of your council meetings", and "I will not call again unless I hear from you."

Prices and terms in the texts are the chat's `[C]`; "20-minute", "5 business days", the single follow-up, the stopwatch comparison, the agreement, the acknowledgement, and the identification and unsubscribe block are the author's `[A]`. The block follows `[S: CASL]` s. 6(2) and `[S: CASL-CRTC]` s. 2(1) as read by the author; the lawyer checks it (question 6(b)).

**Items in the chat's go-to-market research `[C]` that this plan leaves out, and why** `[A]`:

| Item in the brief | What happened to it | Reason |
|---|---|---|
| LinkedIn search filter (titles, British Columbia, Real Estate), connection text and LinkedIn follow-up | Filter kept only as a way to find a managing broker's name; both texts dropped | No commercial message is sent on LinkedIn until the lawyer answers question 6(c); the follow-up also offered to process a past recording |
| Draft cold email | Replaced by the first touch above | It promised a draft from recordings without mentioning recording authority, and had no sender block or unsubscribe line |
| Five search keywords | Not used | The plan has no search advertising or content channel; nothing in the economics pays for one |
| Five-minute demo script (upload, draft, export, bylaw question, audit log and price) | Replaced by the demo in T-0.2.2 | It demonstrates an application that does not exist in Phase 0; the demo uses a synthetic recording and a hand-made draft |
| Positioning line "the only minutes and bylaw assistant built on the BC Strata Property Act…" | Not used in any message | "Only" rests on a search that found nothing, which is not proof ([section 4](#4-competitor-gap-supporting-evidence-counterargument)), and nothing is built yet |
| Referral offer for self-managed councils (a discount code at CHOA and VISOA seminars) | Not used; the brokerage half is in [section 5](#5-offer-channel-pilot) | Councils are not customers in this pilot |
| Notice script as the answer to the recording objection | Replaced in 12.7 | Weakened by `[S: OIPC-2022]` |

### 12.6 Pilot offer and conversion

What the buyer gets, pays and supplies is decided in [section 5](#5-offer-channel-pilot) (rows "Free test", "Paid pilot", "What the paid pilot delivers before the application exists", "When a pilot counts as paid", "Sample inputs needed") and is not repeated here.

**What ends the pilot** `[A]`: the 60th day `[C]` after the first pilot meeting that follows payment. In its last week the founder gives the managing broker the end-of-pilot summary (T-0.4.3, subtask (e)) with three results: whether minutes went out within 3 business days for every meeting `[C]`; the net time saved per meeting after correction against the 45-minute proposal in [section 10](#10-what-buyer-evidence-would-change-the-decision) `[A]`; and every motion, vote or citation error and who caught it.

**The exact step from pilot to a recurring paid account** `[A]`; the chat did not describe it:

1. In the same meeting the managing broker states how many buildings the brokerage will load.
2. That count sets the tier: up to 10 buildings Starter CAD 149, up to 30 Pro CAD 349, up to 100 Business CAD 799, plus CAD 15 per extra building, all per month `[C]`.
3. The managing broker signs a one-page monthly subscription order that carries over the pilot's data-handling terms and its recording-authority condition.
4. The founder issues the first monthly invoice when the pilot ends. This is the "first billed two months after the pilot's start month" of rule 3 in [section 7.6](#76-cash-required-during-the-acquisition-ramp).
5. The brokerage is counted as a recurring paid account when that invoice is **paid**, the same test as for a paid pilot.

Until the application is released the subscriber is still served by hand at the pilot's cap of about 12 meetings per month `[A]`; a brokerage that needs more cannot be served yet and is told so. Annual billing, a notice period and what happens to a pilot that neither converts nor declines are not decided in chat. The assumed share that converts is 70% `[A]` (50% in the downside `[A]`); no evidence supports either.

### 12.7 Objections

The chat's three objections and its answers are in [section 5](#5-offer-channel-pilot) `[C]`. Below are the three the author expects most often `[A]`, with the answer the founder can give today without overstating anything.

| Objection | Honest answer | Basis |
|---|---|---|
| "Our councils will not agree to recording", or "Are we even allowed to record?" | Possibly not, and the founder cannot say they are. The regulator's guidance is that recording is likely not authorized without a bylaw, and passing one takes a 3/4 vote at a general meeting and a filing. A notice script, the chat's answer, is not offered as enough. The test uses only buildings that already have a filed recording bylaw, or the manager's dictated notes. If a brokerage has neither, the honest answer is that the product does not fit it today. | `[S: OIPC-2022]`; `[S: SPA]` s. 128; counterargument 1 in [section 4](#4-competitor-gap-supporting-evidence-counterargument); lawyer's questions 1 to 3 in T-0.1.3 still open |
| "Otter or ChatGPT and our Word template are enough" (the current workaround) | That may be true, and it is cheaper: Otter Business for 3 managers costs about a third of the Pro price. Nobody has measured whether a BC-form draft cuts correction time enough to earn the difference. The free test measures exactly that with a stopwatch, on the brokerage's own meetings; if the saving after correction is small, the brokerage should not buy. One caution the founder can add truthfully: Otter's pricing page carries no data-residency statement, and pasting owners' information into a general chatbot is the managing broker's own confidentiality question. | 2.81× and 3.58× in [section 4](#4-competitor-gap-supporting-evidence-counterargument) `[D]`; `[S: Otter]`; `[S: RESR]` s. 30(e); ChatGPT itself not checked |
| "We cannot rely on AI for a vote result or a legal question" | Agreed, and the service does not ask for that. A motion's outcome is what the chair declared or a count the manager confirms, never the model's reading; a bylaw answer is the quoted clause with its number, or "none found". The manager corrects and approves everything and sends it the way they do now. Two limits are stated plainly: the draft will contain errors, which is why correction time is the thing measured; and whether a quoted clause could be treated as legal advice is an open question for the lawyer. | Counterargument 3 in [section 4](#4-competitor-gap-supporting-evidence-counterargument); MH-06 and MH-10 in [PRD.md](PRD.md#must-haves); lawyer's question 5 in T-0.1.3 |

"Condo Control has AI" stays in [section 5](#5-offer-channel-pilot) with the chat's answer; its pricing page lists Capstan AI as an add-on and does not mention British Columbia `[S: CondoControl]`, and what that add-on does for minutes was not tested.

### 12.8 First 30, 60 and 90 days

**Day 1 is the first contact**, as in the stop rule and the ramp. It is preceded by a preparation period of about 14 days `[A]` in which nothing is sent, because the first touch waits for the lawyer's answer to question 6 (12.4, step 0). The 14 days are the author's guess at a lawyer's turnaround; no lawyer has been asked. If the answer takes longer, day 1 moves and nothing else in this section changes. Expected values are the funnel of [section 8](#8-funnel-recomputed-from-distinct-reachable-prospects) `[D]` on assumed rates `[A-chat]`; fractions are expectations, not customers. Money is the base-case table of [section 7.6](#76-cash-required-during-the-acquisition-ramp); hours are sums of the task ranges in [execution-plan.md](execution-plan.md#effort-summary) `[A]`.

**Weekly activity targets**

| Week | First touches | Follow-ups | Other work | Tasks |
|---|---|---|---|---|
| Preparation (two weeks before day 1) | 0 | 0 | Build and check the list with its consent records; send the authority pack and six questions to the lawyer; receive the answer to question 6 | T-0.1.1, T-0.1.3 |
| 1 (days 1–7) | 60 `[C]` | 0 | Interviews booked by phone or introduction; stopwatch sheet and hand-run protocol | T-0.2.1, T-0.1.2, T-0.3.1, T-0.3.2 |
| 2 (days 8–14) | 0 | about 54 `[D]` | Interviews (11 in all `[C]`); first demos | T-0.1.2, T-0.2.2 |
| 3 (days 15–21) | 0 | 0 | Demos; interview gate checked (6 of 11 `[C]`); **message check on day 21**; first free tests if the lawyer's recording answers are in and agreements are signed | T-0.2.2, T-0.3.3 |
| 4 (days 22–28) | 90 `[C]`, timing `[A]` | 0 | Demos; free tests | T-0.2.1, T-0.2.2, T-0.3.3 |
| 5 (days 29–35) | 0 | about 81 `[D]` | Demos; free tests | T-0.2.2, T-0.3.3 |
| 6–8 (days 36–60) | 0 | 0 | **Channel check on day 40**; free two-meeting tests for up to 5 brokerages `[C]`; measurement tables; pilot agreements and invoices; stop-rule memo on day 60 | T-0.3.3, T-0.3.4, T-0.4.1, T-0.4.2 |
| 9–13 (days 61–90) | 0 | 0 | Memo closed by day 74 if it was provisional (12.9); hand-run delivery of the paid pilots, weekly table to each managing broker; Phase 1 only if the stop rule allows | T-0.4.2, T-0.4.3; T-1.1.1 to T-1.1.3 |

The second wave of 150 first touches belongs to month 4 (weeks 14 to 17), and only if the T-0.1.1 count shows that a second 150 exist and the stop rule said continue.

**Expected position at each point** (days counted from the first contact; cumulative unless stated)

| | Day 30 | Day 60 | Day 90 |
|---|---|---|---|
| Distinct brokerages contacted | 150 `[C]` | 150 | 150 |
| Replies | 6 to 15 `[D]`: the first cohort's 6 are due; the second cohort's follow-ups go out on days 29–33 and their replies are due by day 40 | 15 `[D]` | 15 |
| Calls: discovery interviews | 11 `[C]` | 11 | 11 |
| Calls: demos | about 3 `[D]` (the first cohort's; the second cohort's 4.5 are still to be booked) | 7.5 `[D]` | 7.5 |
| Free tests running or done | first ones running | up to 5 brokerages `[C]` | up to 5 |
| Paid pilots (agreement signed and CAD 299 paid) | 0 `[D]` (30-day sales cycle `[A-chat]`) | 1.875 `[D]` **if nothing slips**; see "Slack" below | 1.875, still being delivered |
| Recurring paid accounts | 0 | 0 | 0; 1.3125 `[D]` are first billed in month 4 |
| Revenue received | 0 | 1.875 × 299 = CAD 560.62 `[D]` | CAD 560.62 |
| Cumulative cash from day 1, no founder pay | −2,925.00 `[D]` | −3,246.82 `[D]`; spend ceiling before revenue 3,725 `[D]` (4,125 from the start of preparation) | −4,112.45 `[D]` |
| Cumulative cash from day 1, with founder pay | −8,925.00 `[D]` | −15,246.82 `[D]` | −22,112.45 `[D]` |
| The same, including the preparation fortnight | −3,325.00 / −12,325.00 `[D]` | −3,646.82 / −18,646.82 `[D]` | −4,512.45 / −25,512.45 `[D]` |
| Founder hours in the period | 49–73 `[D]`, after 14–22 `[D]` in preparation | 36–55 `[D]` | 22.5–37.5 `[D]` for pilot delivery, plus 20–30 `[A]` if Phase 1 starts |

- **No month of the ramp moves.** The ramp counts months from the first contact; both cohorts are contacted in month 1, pilots are booked in month 2 and recurring accounts in month 4, exactly as in [section 7.6](#76-cash-required-during-the-acquisition-ramp). What moves is the calendar: everything is about 14 days `[A]` later than a plan that sent on the day the list was ready.
- **Cost of the preparation fortnight**, which the ramp table does not contain: if the fixed costs are already running `[A]`, half a month is 0.5 × 800 = CAD 400 `[D]`, and with founder pay 0.5 × 6,000 = CAD 3,000 more `[D]`. The row above adds these: −2,925 − 400 = −3,325; −8,925 − 3,400 = −12,325; and the same 400 and 3,400 at days 60 and 90. The ceiling of CAD 3,725 becomes 3,725 + 400 = **CAD 4,125** counted from the start of preparation, and 15,725 + 3,400 = CAD 19,125 with founder pay `[D]`. The lawyer's fee is already the startup line of month 1; it is only paid earlier.
- Hours, preparation: T-0.1.1 and T-0.1.3 = (6+8) to (10+12) = 14–22 `[D]`.
- Hours, days 1–30: T-0.1.2, T-0.2.1, T-0.3.1, T-0.3.2 and half of T-0.2.2 = (16+20+3+4+6) to (24+30+5+6+8) = 49–73 `[D]`. Preparation and days 1–30 together are 63–95; the chat planned 70 for its first month `[C]`.
- Hours, days 31–60: the other half of T-0.2.2, T-0.3.3, T-0.3.4, T-0.4.1, T-0.4.2 = (6+20+3+5+2) to (8+30+5+8+4) = 36–55 `[D]`. All three together are 99–150, the Phase 0 total in the effort summary.
- Hours, days 61–90: T-0.4.3 is 24–40 hours per pilot over 60 days, so 12–20 per pilot per month; × 1.875 = 22.5–37.5 `[D]`. A pilot that starts before day 60 costs the same monthly rate from its start, which the day-60 column does not include.
- **Slack.** The day-60 pilot count is a best case. The second cohort is contacted on days 22–26; a 30-day cycle `[A-chat]` ends on days 52–56, which is 4 to 8 days before day 60 `[D]`. The cycle itself is optimistic for this offer: a brokerage has to reply, see a demo, sign the hand-run agreement, hold two meetings that happen to fall in the window, see its table, sign and pay. Any slip moves a pilot past day 60 and lowers the number the stop rule reads, which biases the decision toward "stop". The 14-day close-out in 12.9 `[A]` is the slack this plan gives. A pilot paid on days 61–74 is booked in month 3 instead of month 2: CAD 299 and its costs move one month later and its first subscription invoice moves from month 4 to month 5; totals do not change, and the ramp table is not re-run for it.
- The chat's own targets for the first four weeks (2 pilot agreements in week 3, 2 paying brokerages and CAD 500 of monthly revenue in week 4) `[C]` are not used here: checks 4 and 6 in [section 9.2](#92-checks-on-the-chats-rule) show they do not fit the 30-day cycle or the pilot price.
- In the downside case of [section 8](#8-funnel-recomputed-from-distinct-reachable-prospects) the same activity yields 7.5 replies, 3.75 demos and 0.9375 paid pilots by day 60 and 0.469 recurring accounts in month 4 `[D]`, at the same spend.
- What the money buys in acquisition terms is in [section 7.4](#74-acquisition-cost-including-founder-time): CAD 857.14 per converted subscriber in cash-like terms, CAD 3,362 to 4,819 with this plan's founder hours `[D]`.

### 12.9 GTM stop rule

**The product stop rule is the chat's rule in [section 9.1](#91-the-chats-rule-exactly-as-stated).** The chat's rule names no date. Evaluating it on day 60 after the first contact is the author's `[A]`, a "changed" row of the proposal in [section 9.3](#93-proposed-revision-a--a-change-to-the-chats-rule-not-a-restatement); the rest of that proposal applies only if the founder adopts it in writing. Nothing below changes a threshold. The rows marked `[A]` are added checkpoints for the *channel*, which the chat's rule does not separate from the product, and for timing.

| What is judged | Number | Consequence | Label |
|---|---|---|---|
| Message (day 21) | 0, 1 or 2 replies from the first 60, counted on day 21, when replies to their follow-ups (sent on days 8–12) have had at least 5 business days to arrive; 6 are expected | Rewrite the first touch and lead with a phone call for the remaining 90, which go out in week 4. Not a stop. If the 10% rate is true this happens 6.2% of the time; at 5% it happens 42.3% of the time `[D]` (Poisson, means 6 and 3). Replies that arrive after day 21 would lower both figures; none are assumed. | `[A]` |
| Channel (day 40) | Fewer than 8 replies from 150 distinct brokerages, counted on day 40, 5 business days after the last follow-up; 15 are expected | Cold outreach is dropped as the first channel: no second wave is sent this way, and the remaining pool is approached through the backup channel `[C]`. The product decision still waits for the memo. If the 10% rate is true this happens 1.8% of the time; at the downside's 5% it happens 52.5% of the time `[D]` (Poisson, means 15 and 7.5) | `[A]` |
| Product: paid pilots | Fewer than 2 paid pilots after 150 contacts and 8 demos | Stop or pivot to self-managed councils | `[C]`; checks and the one-pilot proposal in section 9 |
| Timing of that count | Day 60 after the first contact. If on day 60 a brokerage has a signed pilot agreement with the invoice unpaid, or a free test still running, and its payment could change the outcome, the memo is marked provisional and is closed on day 74 at the latest. No money is spent on Phases 1–6 in between. | Gives the count 14 days of slack without changing the threshold | `[A]`, both the date and the close-out |
| Product: recording | Brokerages refuse recording as policy; the proposal puts a number on it (5 or more of the demoed brokerages, or more than half if fewer than 8 were demoed, counting those that cannot name two meetings with a recording bylaw) | Stop the recorded-audio product; dictated notes alone were not evaluated in chat | `[C]`; number `[A]` |
| Product: the problem itself | Most interviewed managers say minutes take under 30 minutes; or the free tests show no net time saved after correction | Stop | `[C]`; second half `[A]`, from [section 10](#10-what-buyer-evidence-would-change-the-decision) |
| Money | CAD 3,725 spent before revenue by day 60, without founder pay (CAD 4,125 counted from the start of preparation) | No further spend until the memo is written | `[A]`, [section 7.6](#76-cash-required-during-the-acquisition-ramp) and 12.8 |
| Channel: the law | The lawyer's answer to question 6 is that cold email is not available on a published-address basis | Every first touch and follow-up is by phone or visit; the hours and reply rate are restated before day 1 | `[A]` |

Consistency with the funnel: the channel number (8) is the downside's expected 7.5 replies rounded up, so a channel running at half the assumed reply rate is caught about half the time at day 40 instead of at day 60; the product number (2 paid pilots) sits just above the 1.875 the funnel expects, which [section 9.2](#92-checks-on-the-chats-rule) already reports as a weakness of the rule, and the timing of the count adds a second bias in the same direction (12.8, "Slack"). A channel that fails its check while the paid-pilot count still reaches 2 is not a product stop: it changes how the second 150 are reached, and the cost of the backup channel is not modelled.

## 13. Sources and assumptions

Date consulted for every row: **2026-11-10**. "Opened" means the page content was retrieved and read by the author's tools on that date.

| ID | Source | Jurisdiction | Scope used | Access |
|---|---|---|---|---|
| SPA | *Strata Property Act*, SBC 1998 c. 43, BC Laws, Parts 1, 4 and 7 (`bclaws.gov.bc.ca/civix/document/id/complete/statreg/98043_01`, `_04`, `_07`) | British Columbia | s. 1 definitions of majority vote, 3/4 vote, 80% vote, unanimous vote; s. 35 records including minutes with vote results, and bylaws and rules; s. 36 access to records (owners, tenants with assigned rights, persons authorized in writing, former owners); s. 36(3) within 2 weeks, or one week for bylaws or rules; s. 37 return of records within 4 weeks after a management contract ends; s. 45 two weeks' notice; s. 48(1) no business without a quorum; s. 48(2)(a) quorum 1/3 of votes, subject to the bylaws; s. 48(2)(b) 2/3 where there are fewer than 4 strata lots or fewer than 4 owners; s. 48(3) unless the bylaws provide otherwise, no quorum within half an hour adjourns the meeting one week and those present at the adjourned meeting are a quorum; s. 49 electronic attendance; s. 50 voting; ss. 119–128 bylaws, rules, 3/4 vote amendment, no effect until filed | Opened. Consolidation current to 2026-11-03. Part 4 was opened three times on 2026-11-10; the third reading (fix round 1) supplied s. 36(3) and s. 48(2)(b) and (3). Any special treatment in s. 48(3) of meetings called by voters was not captured and must be read before the adjourned-meeting rule is relied on. |
| SPA-SB | Schedule of Standard Bylaws to the Act (`…/98043_18`) | British Columbia | s. 16(1) council quorum: 1 for a council of 1; 2 for 2, 3 or 4; 3 for 5 or 6; 4 for 7; s. 16(2) present in person; s. 17 council meetings, electronic means, owners as observers; s. 18(1) majority of council members present; s. 18(2) president's second, deciding vote on a tie, not where there are only 2 strata lots; s. 18(3) results of all council votes recorded in the minutes; s. 19 minutes to owners within 2 weeks; s. 27(2) show of voting cards unless a precise count is requested; s. 27(3) chair decides the method of a precise count; s. 27(4) outcome announced and recorded, with numbers for and against only if a precise count was requested; s. 27(5)–(6) president's (or vice president's) second, deciding vote on a tie, not where there are only 2 strata lots; s. 27(7) secret ballot on request; s. 28 order of business | Opened twice on 2026-11-10; the second reading (fix round 1) supplied ss. 16, 18 and 27 in detail. Current to 2026-11-03. Read through a summarising tool with short quotations, so the wording here is a paraphrase; T-4.1.2 transcribes the text itself. |
| SPR | *Strata Property Regulation*, B.C. Reg. 43/2000 (`…/12_43_2000`) | British Columbia | s. 4.1(3) records under Act s. 35(1)(a), which includes minutes, kept at least 6 years; s. 4.1(6) current copies of bylaws and rules; s. 4.2 maximum copy fee 25 cents per page, no inspection fee | Opened; first 100,000 characters read. Current to 2026-11-03. |
| PIPA | *Personal Information Protection Act*, SBC 2003 c. 63 (`…/03063_01`) | British Columbia | s. 4(2) responsibility for information not in custody; s. 6 consent; s. 7; s. 8 implied consent and opt-out notice; s. 10 notification of purposes; s. 23 access; s. 34 reasonable security; s. 35 retention at least 1 year after use in a decision, then destroy when no longer needed | Opened. Current to 2026-11-03. The page read contains no provision on storage outside Canada. |
| OIPC-2022 | Office of the Information and Privacy Commissioner for BC, "Privacy guidelines for strata corporations and strata agents" (`oipc.bc.ca/guidance-documents/3632`) | British Columbia | Recording of meetings likely not authorized by PIPA without a bylaw; implied consent to be named in minutes; minutes need not include exact discussion; use unit or strata lot number for sensitive matters; disclosure to a property manager with contractual restriction; SPA authorizes collection to create minutes | Opened as PDF and text extracted by the author's own parser. Embedded creation timestamp is May 2022, matching the BC government page's description; the visible date was not confirmed. Guidance, not law. Two other OIPC URLs (documents 1455 and 1805) returned "file not found". |
| RESR | *Real Estate Services Rules*, B.C. Reg. 209/2021 (`…/209_2021`) | British Columbia | s. 28 managing broker supervision and records; s. 30(e) confidentiality; s. 43(6)(f)–(g) service agreement terms on records and information; s. 88 strata management records (accounting records; minutes not listed); s. 91 electronic records; s. 92 retention at least 7 years, available at head office | Opened in two parts. Current to 2026-11-03. No rule read requires records to be stored in British Columbia. |
| CASL | *An Act to promote the efficiency and adaptability of the Canadian economy by regulating certain activities that discourage reliance on electronic means of carrying out commercial activities…*, S.C. 2010, c. 23 ("Canada's anti-spam legislation"), Justice Laws (`laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html`) | Canada (federal) | s. 1(1) electronic address; s. 1(2) commercial electronic message; s. 6(1) consent and form; s. 6(2) sender identification, contact information, unsubscribe mechanism; s. 6(3) contact information valid 60 days; s. 6(8) voice calls and voice recordings excluded; s. 10(9)(b) implied consent for a conspicuously published address; s. 11(1)–(3) unsubscribe mechanism, 60 days, effect within 10 business days; s. 13 onus of proving consent; s. 20(4) maximum penalty | Opened in full; page text extracted by the author's own parser and the cited subsections read directly. Current to 2026-10-19, last amended 2026-01-01. The author's reading, not legal advice. |
| CASL-CRTC | *Electronic Commerce Protection Regulations (CRTC)*, SOR/2012-36 (`laws-lois.justice.gc.ca/eng/regulations/SOR-2012-36/FullText.html`) | Canada (federal) | s. 2(1) information to be set out: name, mailing address, and a telephone number, email address or web address; s. 2(2) link to a web page where including it is not practicable; s. 3 clearly and prominently, readily performed | Opened in full, same method. Current to 2026-10-19, last amended 2015-01-15. |
| CASL-GIC | *Electronic Commerce Protection Regulations*, SOR/2013-221 (`laws-lois.justice.gc.ca/eng/regulations/SOR-2013-221/FullText.html`) | Canada (federal) | s. 3(a)(ii) messages between organizations that have a relationship; s. 3(d) messages on an electronic messaging service | Opened in full, same method. Current to 2026-10-19, last amended 2015-01-15. Other exclusions in s. 3 were read and do not fit a cold contact; s. 4 was not relied on. |
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

Not consulted by the author: CRTC guidance on the anti-spam legislation and the telemarketing rules (the reviewer reports the CRTC's FAQ page returned HTTP 403); OWASP ASVS and the WCAG 2.2 quick reference. The independent reviewer consulted OWASP ASVS 5.0.0 and the WCAG 2.2 Recommendation on 2026-11-10; requirement and criterion IDs in [TRD.md](TRD.md) and [design.md](design.md) are cited on the reviewer's reading, not the author's. BC statutory holidays used in the business-day calculation were not looked up: unverified, no source consulted (to be taken from the BC government list in T-5.1.2).

Exchange rates: only one conversion is used (section 4), at the chat's scenario rate 1 USD = 1.38 CAD `[A-chat]`, direction USD→CAD, a scenario assumption and not a sourced rate. All economics are in CAD per month.
