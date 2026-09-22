from scopedact.scenarios import run_all

for result in run_all("audit/example.jsonl"):
    print(f"{result.name}: {'PASS' if result.passed else 'FAIL'} ({result.observed})")

