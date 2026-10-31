"""Conservative admission gate evaluator. No real authorization can be inferred from file presence."""

REQUIRED = {
    'G0': 'Written authority and source rights of an operator',
    'G1': 'Vendor OSS mapping and counter contracts accepted by SME',
    'G2': 'Source-preserving audit and independent real-data validation',
    'G3': 'Holdout on real sites/times with mature independent labels',
    'G4': 'Privacy approval, remote CI, hardening, recovery and shadow pilot',
    'G5_TECH': 'Independent technical signoff',
    'G5_BUSINESS': 'Verified NOC value and accountable business approval',
}

def decide(evidence):
    # None of these switches is set by local test execution. They require human authorizations.
    result = {k:('PASS' if evidence.get(k,False) is True else 'BLOCK') for k in REQUIRED}
    result['G5'] = 'PASS' if all(result.get(g)=='PASS' for g in ('G0','G1','G2','G3','G4','G5_TECH','G5_BUSINESS')) else 'BLOCK'
    return result
