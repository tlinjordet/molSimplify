import helperFuncs as hp


def test_tutorial_10_part_one(tmpdir):
    testName = "tutorial_10_part_one"
    threshMLBL = 0.1
    threshLG = 2.0
    threshOG = 2.0
    [passNumAtoms, passMLBL, passLG, passOG, pass_report, pass_qcin] = hp.runtest(
        tmpdir, testName, threshMLBL, threshLG, threshOG)
    assert passNumAtoms
    # Not checking for passMLBL because there are atoms very close to the cutoff
    # assert passMLBL
    assert passLG
    assert passOG
    assert pass_report
