from benchmark.run_benchmark import load_cases, score


def test_dataset_is_labelled():
    cases = load_cases()
    assert len(cases) >= 20
    harmless = [c for c in cases if c["set"] == "harmless_changes"]
    assert harmless and all(c["expected"] == [] for c in harmless)
    assert all(c["diff"].startswith("diff --git") for c in cases)


def test_static_mode_quality_floor():
    report = score()
    assert report["false_positives"] == 0, report["cases_with_false_positives"]
    assert report["precision"] >= 0.9
    assert report["recall"] >= 0.6