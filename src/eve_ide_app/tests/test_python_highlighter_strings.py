from PySide6.QtCore import QRegularExpression


def test_python_string_regexes_sequence_basic():
    # Mirrors the patterns used by PythonHighlighter; we validate behavior directly on regex level
    # Updated to remove leading word-boundary to allow matches at start-of-line or after non-word chars
    str_sgl = QRegularExpression(r"(?i)(?:[rubf]|br|rb|fr|rf)?\'([^\'\\]|\\.)*\'")
    # FIXED double-quote regex (should exclude ") and no leading word-boundary
    str_dbl = QRegularExpression(r'(?i)(?:[rubf]|br|rb|fr|rf)?"([^"\\]|\\.)*"')
    # Triple double-quote start should be detected even when not at a word boundary
    triple_double_start = QRegularExpression(r'(?i)(?:[rubf]|br|rb|fr|rf)?"""')

    s = '""\'word"""'

    # Expect an empty double-quoted string at the start
    m1 = str_dbl.match(s, 0)
    assert m1.hasMatch(), 'Empty double-quoted string should match at start'
    assert m1.capturedStart() == 0 and m1.capturedLength() == 2

    # The single-quoted part here is intentionally unterminated; we only verify that
    # the triple-double-quote start is still detected immediately after it.
    m3 = triple_double_start.match(s, m1.capturedEnd())
    assert m3.hasMatch(), 'Triple double-quote start should match after the unterminated single quote segment'
    assert m3.capturedStart() == 7


def test_double_quote_regex_does_not_swallow_following_strings():
    # Ensure the double-quoted regex does not overmatch into the next string
    str_dbl = QRegularExpression(r'(?i)(?:[rubf]|br|rb|fr|rf)?"([^"\\]|\\.)*"')

    s = 'a = "" "b"'
    it = str_dbl.globalMatch(s)
    starts = []
    lens = []
    while it.hasNext():
        m = it.next()
        starts.append(m.capturedStart())
        lens.append(m.capturedLength())

    # Positions: 0 a,1 space,2 =,3 space,4 ",5 ",6 space,7 ",8 b,9 "
    assert starts == [4, 7], f'Expected two double-quoted strings at positions [4, 7], got {starts}'
    assert lens == [2, 3], f'Expected lengths [2, 3] for "" and "b"; got {lens}'