#!/usr/bin/env python3
"""Turn the human-friendly seed CSVs into import-ready CSVs and load them.

Usage:
    python3 scripts/prepare_seed_import.py --org <alias> [--steps] [--dry-run]

Resolves Account_Name -> Account__c Id and CS_Rep_Email -> Client_Success_Rep__c Id
with the Salesforce CLI, writes data/_import_price_escalations.csv (and
data/_import_escalation_steps.csv with --steps), then runs `sf data import bulk`.
Rows whose account or rep cannot be resolved are reported and skipped, so the
sheet can be fixed and the script rerun. Steps are matched to their parent
escalation by Account_Name + the first characters of the clause text
(Escalation_Match_Clause_Prefix), so load escalations first, then steps.
"""
import argparse, csv, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')

def sf_query(org, soql):
    out = subprocess.run(['sf', 'data', 'query', '-o', org, '-q', soql, '--json'], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)['result']['records']
    except Exception:
        sys.exit(f'query failed: {soql}\n{out.stdout[:500]}{out.stderr[:500]}')

def soql_list(values):
    return ','.join("'" + v.replace("'", "\\'") + "'" for v in sorted(values))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--org', required=True)
    ap.add_argument('--steps', action='store_true', help='import escalation steps (run after escalations are loaded)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--escalations-file', default=os.path.join(DATA, 'price_escalations_seed_template.csv'))
    ap.add_argument('--steps-file', default=os.path.join(DATA, 'escalation_steps_seed_template.csv'))
    a = ap.parse_args()

    if not a.steps:
        rows = list(csv.DictReader(open(a.escalations_file, newline='', encoding='utf-8-sig')))
        names = {r['Account_Name'].strip() for r in rows if r['Account_Name'].strip()}
        emails = {r['CS_Rep_Email'].strip().lower() for r in rows if r.get('CS_Rep_Email', '').strip()}
        accts = {x['Name']: x['Id'] for x in sf_query(a.org, f"SELECT Id, Name FROM Account WHERE Name IN ({soql_list(names)})")} if names else {}
        users = {x['Email'].lower(): x['Id'] for x in sf_query(a.org, f"SELECT Id, Email FROM User WHERE IsActive = true AND Email IN ({soql_list(emails)})")} if emails else {}
        out_rows, skipped = [], []
        for r in rows:
            acct = accts.get(r['Account_Name'].strip())
            if not acct:
                skipped.append((r['Account_Name'], 'account not found')); continue
            rep = users.get(r.get('CS_Rep_Email', '').strip().lower(), '')
            if r.get('CS_Rep_Email', '').strip() and not rep:
                skipped.append((r['Account_Name'], f"CS rep {r['CS_Rep_Email']} not found; leaving blank so the Account CS rep is used"))
            o = {k: v for k, v in r.items() if k not in ('Account_Name', 'CS_Rep_Email')}
            o['Account__c'] = acct
            if rep: o['Client_Success_Rep__c'] = rep
            for k in list(o):
                if o[k] == '': del o[k]
            out_rows.append(o)
        target = os.path.join(DATA, '_import_price_escalations.csv'); sobject = 'Price_Escalation__c'
    else:
        rows = list(csv.DictReader(open(a.steps_file, newline='', encoding='utf-8-sig')))
        names = {r['Account_Name'].strip() for r in rows}
        pes = sf_query(a.org, f"SELECT Id, Account__r.Name, Clause_Text__c FROM Price_Escalation__c WHERE Account__r.Name IN ({soql_list(names)})")
        out_rows, skipped = [], []
        for r in rows:
            match = [p for p in pes if p['Account__r']['Name'] == r['Account_Name'].strip() and (p['Clause_Text__c'] or '').startswith(r['Escalation_Match_Clause_Prefix'].strip())]
            if len(match) != 1:
                skipped.append((r['Account_Name'], f'{len(match)} escalations matched clause prefix')); continue
            o = {k: v for k, v in r.items() if k not in ('Account_Name', 'Escalation_Match_Clause_Prefix') and v != ''}
            o['Price_Escalation__c'] = match[0]['Id']
            out_rows.append(o)
        target = os.path.join(DATA, '_import_escalation_steps.csv'); sobject = 'Price_Escalation_Step__c'

    for who, why in skipped: print(f'SKIP {who}: {why}')
    if not out_rows: sys.exit('nothing to import')
    cols = sorted({k for r in out_rows for k in r})
    with open(target, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out_rows)
    print(f'wrote {len(out_rows)} rows to {target}')
    if a.dry_run: return
    subprocess.run(['sf', 'data', 'import', 'bulk', '-o', a.org, '--sobject', sobject, '--file', target, '--wait', '10'], check=False)

if __name__ == '__main__':
    main()
