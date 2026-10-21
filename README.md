# Price Increase Automation (PIA)

Salesforce DX project for the Price Increase Automation build. It moves Cecily's spreadsheet of
contractual fee increases and price-lock clauses into Salesforce so notice dates, the increase itself
and the resulting Revenue Enhancement opportunity are tracked and timed by the system.

Built and tested in the **PIA Developer sandbox** (`passportlabs--pia`). See
[docs/BUILD_HANDOFF.md](docs/BUILD_HANDOFF.md) for what was built, how it was tested, decisions taken,
and the production deployment steps.

## Layout

| Path | What |
|---|---|
| `force-app/main/default/objects/Price_Escalation__c` | The clause object: fields, validation rules, list views |
| `force-app/main/default/objects/Price_Escalation_Step__c` | Child object for per-year / semi-annual step schedules |
| `force-app/main/default/objects/Price_Increase_Settings__c` | Hierarchy custom setting (planning %, notice days, reminder lead, digest recipient) |
| `force-app/main/default/objects/Opportunity/fields/Price_Escalation__c` | Lookup from the increase deal back to its clause |
| `force-app/main/default/flows` | 8 flows: before-save defaults, create-opp (screen + core), daily reminder (scheduled + core), weekly digest (scheduled + core), closed-won roll-forward |
| `force-app/main/default/quickActions` | The **Create Increase Opp** button |
| `force-app/main/default/permissionsets` | `Price_Escalation_Management` |
| `force-app/main/default/layouts` | Object layouts, plus Account / Opportunity layouts with the related list added |
| `force-app/main/default/reports` | Folder *Price Increase Automation* with three reports |
| `data/` | Seed CSV templates for the 12 production rows |
| `scripts/prepare_seed_import.py` | Resolves account / rep names and bulk-loads the seed rows |

## Deploy

```
sf project deploy start -o <org-alias> --source-dir force-app
```

Then follow the post-deploy steps in the handoff (settings record, permission set, seed rows).
