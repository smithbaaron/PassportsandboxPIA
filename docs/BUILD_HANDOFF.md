# Price Increase Automation: Sandbox Build Handoff (build complete)

Built 2026-10-21 in the PIA Developer sandbox from the Oct 20 handoff. Everything below is deployed
to PIA, tested with ZZ TEST data, and committed in this repo as a deployable package.

## What was built

**Price Escalation** (`Price_Escalation__c`), master-detail under Account, one record per escalator or
price-lock clause. Auto-number `PE-0000`. Holds the clause text verbatim, products covered (multi-select
plus a free-text detail), the escalator shape (Fixed Percentage, Percentage Band, Fixed Amount per
Transaction, Step Schedule, Dollar Cap, CPI-Linked, Price Lock Only, Other), min / max / planned
percentage, fixed dollar step, per-increase and lifetime caps with a running cumulative, frequency
(Annual / Semi-Annual / Per Renewal Term), escalation start year (for Year 6 / Year 11 clauses), notice
days, Next Increase Date, Notice Due Date (formula), Notice Sent Date, Finance Ticket Reference,
revenue impact fields, the exclusion checkbox with required reason, Source Opportunity (the contract
deal) and Current Increase Opportunity. Effective Percentage is a formula: the record's Planned
Percentage, else the org default, capped at the contract maximum.

**Escalation Step** (`Price_Escalation_Step__c`), master-detail child, for clauses with more than one
step: step number, effective date, percentage or amount, new rate, product, status
(Scheduled / Applied / Skipped), and the opportunity that applied it. Sound Transit's five escalators
are five Price Escalation records, each with its own steps.

**Price Increase Settings** (hierarchy custom setting): Default Planning Percentage (5), Default Notice
Days (60), Reminder Lead Days (14), Digest Recipient Email, Digest Window Days (90), Reminders Enabled.
One org-default record; Cecily changes the percentage here each year.

**Opportunity.Price Escalation** lookup: the increase deal points back to its clause. The Account layout
and the two Opportunity layouts (Sales, Admin) carry a Price Escalations related list, so the terms show
on the Account and on the closed contract deal.

**Create Increase Opp** (quick action, screen flow): shows the clause summary, pre-fills the deal in the
team's convention, lets the rep adjust it, creates it and links it back.

| Field on the new deal | Value |
|---|---|
| Name | `<Account> - 5% Increase Rev Enhancement - <year>` (percentage clauses) or `<Account> - Contractual Increase Rev Enhancement - <year>` (dollar / step clauses); year = increase effective date |
| Type / Lead Source / Record Type | Revenue Enhancement / Client Success / Standard Opportunity |
| Stage | Lead Qualification (forecast category Pipeline) |
| Amount | Estimated Increase Amount (Annual), else Revenue Impact (Next Year) |
| Close Date | Next Increase Date |
| Owner and Client Success Rep | the clause's CS rep (defaults from the Account) |
| Revenue Enhancement Type | mapped from Primary Product (MPP -> MPP Fee Increase, CMP -> CMP Fee Increase, else Other), overridable on the screen |
| Next Step / Description | notice-due date, product reminder, Finance ticket reminder; clause summary and text |

It refuses when the client is excluded or the clause is not Active, and when an open increase deal
already exists for the clause (it links to it instead).

**Flows**

| Flow | Trigger | What it does |
|---|---|---|
| Price Escalation - Before Save Defaults | before save on Price Escalation | CS rep from Account, Notice Days from setting, first Next Increase Date = contract effective date + 12 x escalation start year months, Status follows the Exclude checkbox |
| Price Escalation - Create Increase Opp | screen flow behind the button | as above; calls the Core flow |
| Price Escalation - Create Increase Opp (Core) | autolaunched | the creation logic, reusable by the later automatic version |
| Price Escalation - Notice Reminder (Daily) | scheduled 07:00 ET daily | calls the Core |
| Price Escalation - Notice Reminder (Core) | autolaunched | for every Active, non-excluded clause whose Notice Due Date is within Reminder Lead Days (or past), creates one High-priority Task for the CS rep, due on the notice date, once per cycle. The org requires a contact on every Task, so the Task uses the Account's Billing Contact, else its primary contact; if the account has no contacts at all the rep gets the same reminder by email |
| Price Escalation - Weekly Digest (Monday) | scheduled Mondays 07:30 ET | calls the Core |
| Price Escalation - Weekly Digest (Core) | autolaunched | emails the Digest Recipient a plain-text list of every clause whose notice is due within Digest Window Days, overdue and due-soon flagged, with record links |
| Opportunity - Price Escalation Roll Forward on Close | after save on Opportunity, when it closes and has a Price Escalation | Won: sets Last Increase Effective Date, applies the matching Escalation Step (adds its amount to the cumulative), rolls Next Increase Date to the next scheduled step or forward one frequency period, clears the current-cycle fields, marks the clause Completed when the lifetime cap is reached. Lost: unlinks the deal |

All flows are Active. The scheduled flows and the digest can be paused with the Reminders Enabled setting.

**Access and UI**: permission set `Price Escalation Management` (CRUD on both objects, field access,
tab, flow access, Account read); Price Escalations tab; list views All, My Price Escalations, Active,
Notices Due This Quarter, Notices Due in Next 60 Days, Increases Effective This Month, Excluded, Price
Locks, With Open Increase Opportunity. Report folder *Price Increase Automation* with Increases by
Month, Notices Due This Quarter (grouped by CS rep), Revenue Impact by Product.

## Test results (PIA, ZZ TEST data)

Eight ZZ TEST accounts, nine clauses and six steps cover the clause shapes in the handoff: fixed 5%,
2-7% band, Sound Transit step schedule and a Year-6 CPI clause, $0.05 / $0.40 dollar cap with 120 days
notice, semi-annual steps, an excluded client, a notice due in 10 days, and a price lock on an account
with no CS rep.

| Check | Result |
|---|---|
| Defaults on save | CS rep from Account, Notice Days 60 (120 kept where entered), first increase date = effective + 12 months, Year 6 clause -> 2032, Excluded status, Effective % capped at contract max (3%) |
| Create Increase Opp | Created `ZZ TEST City of Fixedville - 5% Increase Rev Enhancement - 2027`, Amount 12,000, close 2027-03-15, owner Cecily, MPP Fee Increase, linked both ways. Second press: refused, points at the open deal. Excluded client: refused with the reason. Step clause: "Contractual Increase" name |
| Reminder | Run 1: one Task to Cecily for Due Soon Inc (contact Pat Primary, due 2026-10-30) and one email for Sound Transit (no contacts). Run 2: nothing (once per cycle) |
| Digest | 5 clauses listed within 90 days, email sent |
| Roll-forward, fixed | Next date 2027-03-15 -> 2028-03-15, last effective 2027-03-15, applied 1, deal unlinked |
| Roll-forward, steps | Year 2 step Applied with the deal, next date jumped to the Year 3 step (2028-01-01), cumulative 0.02 |
| Roll-forward, cap | 0.35 + 0.05 = 0.40 = lifetime cap -> Status Completed |
| Closed lost | deal unlinked, clause unchanged |
| Reports | Increases by Month returns the expected month groups and sums |

Closing a Revenue Enhancement deal won still needs what the org already requires today: an opportunity
product, Why Passport, and billing city / state and Entity Type on the Account.

## Decisions taken in the build (the open questions from the handoff)

| # | Question | How the build handles it |
|---|---|---|
| 1 | Button vs automatic | Button now. The Core flow is autolaunched, so the automatic version is a scheduled flow that calls it for clauses past their notice date; the exclusion flag is already respected |
| 2 | Who enters terms | Not decided by the build. The entry form is the Price Escalation related list, on both the Account layout and the Opportunity layouts, so either Punith or the CS rep can enter from where they work. Making it required at close or at CS handoff is a validation rule once Marcia decides |
| 3 | Finance ticket | Reference only: a Finance Ticket Reference text field, cleared on each roll-forward |
| 4 | Planning percentage | Price Increase Settings > Default Planning Percentage, inherited by every clause without its own Planned Percentage, capped at the contract maximum |
| 5 | Exclusion | Exclude from Automatic Increases checkbox + required reason; button, reminders and digest all respect it |
| 6 | What Cecily sees | Price Escalations related list on Account and on the closed deal |
| 7 | Revenue Enhancement Type | Mapped from Primary Product (MPP / CMP Fee Increase, else Other), overridable on the screen. No new picklist value added; add "Contractual Escalator" in production if RevOps prefers and change the mapping formula in the Core flow |
| 8 | Arrive | Not touched |

**Reminder audience** (the sentence to confirm with Cecily): the reminder goes to the clause's CS rep as
a Task and to Cecily as the weekly digest; nobody else.

**One org constraint worth a decision.** The org's `Require_WhoID` rule makes every Task carry a
contact. The build satisfies it with the Account's Billing Contact (fallback: primary contact), and
emails the rep when an account has no contact at all. If RevOps would rather have plain tasks, exempt
automation tasks in that rule (for example `AND(ISBLANK(WhoId), NOT(BEGINS(Subject, "Price increase
notice due")))`) and the contact lookup in the reminder flow can be removed.

## Production deployment

1. Re-retrieve the three shared layouts from production before deploying, or drop them from the deploy
   and add the Price Escalations related list by hand: `Account-Account Layout`,
   `Opportunity-Opps Layout - Sales`, `Opportunity-Opps Layout - Admin`. The package copies of these
   are the sandbox versions with one related list added; deploying them overwrites any production
   layout change made since 2026-10-20.
2. `sf project deploy start -o <prod> --source-dir force-app` (use `--dry-run` first).
3. Create the org-default settings record:
   `sf data create record -o <prod> -s Price_Increase_Settings__c -v "SetupOwnerId=<org id> Default_Planning_Percentage__c=5 Default_Notice_Days__c=60 Reminder_Lead_Days__c=14 Digest_Recipient_Email__c=<Cecily's email> Digest_Window_Days__c=90 Reminders_Enabled__c=true"`.
4. Assign `Price_Escalation_Management` to Cecily, the CS reps, Punith and RevOps.
5. Add the Price Escalations tab to the CS app's navigation if wanted.
6. Load the 12 seed rows last: fill `data/price_escalations_seed_template.csv` from Cecily's sheet
   (delete the two example rows), run `python3 scripts/prepare_seed_import.py --org <prod> --dry-run`,
   check the skips, then run without `--dry-run`. Then the steps file with `--steps`. Set Next Increase
   Date explicitly for every row (the 2027 increase date from the sheet) so the before-save default
   does not compute it from the effective date. Set Increases Applied and Cumulative Increase to Date for
   clauses that have already escalated.
7. The reminder flow starts 2026-10-22 and the digest on Monday 2026-10-26; both are driven by the
   schedule in the flow start element and can be moved in Flow Builder.

## Not done / follow-ups

- The 12 production rows are not in this package: the spreadsheet was not part of the handoff. The
  template and loader are ready.
- No custom report type for Escalation Steps; the three reports are on Price Escalations. Add
  "Price Escalations with Escalation Steps" as a custom report type if step-level reporting is wanted.
- The Account Lightning record page was not changed; the related list shows through the page's
  related-list quick links and Related tab from the layout change.
- The reminder flow runs one contact lookup per due clause, so it handles roughly 90 clauses per run.
