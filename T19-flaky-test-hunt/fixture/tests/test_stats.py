import math

from statlib import stats

SAMPLES = [
    ('s01', 8.34402908901449e-06),
    ('s02', 0.0008308183193203525),
    ('s03', 0.030722648017630392),
    ('s04', 9.800906782992545),
    ('s05', 584.8390772548646),
    ('s06', 30938.687794081117),
    ('s07', 4736520.833124299),
    ('s08', 4396.599353748686),
    ('s09', 19.388611755381653),
    ('s10', 0.7474629439454029),
    ('s11', 914115.2344942457),
    ('s12', 0.007779540255850985),
    ('s13', 1.3554235877678348e-06),
    ('s14', 0.00014933129862977352),
    ('s15', 0.05059876258989622),
    ('s16', 1.1973156392803308),
    ('s17', 168.19004485401268),
    ('s18', 34150.131137972916),
    ('s19', 9068977.7739527),
    ('s20', 5606.417702047638),
    ('s21', 31.09539189854862),
    ('s22', 0.6577621846382953),
    ('s23', 710467.7811991635),
    ('s24', 0.0075662166998207185),
]


def test_pooled_variance_exact():
    # The library promises deterministic sorted-order accumulation,
    # so this exact float is the contractually correct answer.
    assert stats.pooled_variance(SAMPLES) == 4000224108364.063


def test_pooled_mean_close():
    assert math.isclose(stats.pooled_mean(SAMPLES), 646082.8947078577, rel_tol=1e-9)


def test_dedup_pairs():
    assert stats.dedup_pairs([('a', 1), ('a', 1.0), ('b', 2)]) == {
        ('a', 1.0), ('b', 2.0)}


def test_variance_simple():
    assert stats.pooled_variance(
        [('a', 1.0), ('b', 2.0), ('c', 3.0)]) == 2.0 / 3.0


def test_variance_constant():
    assert stats.pooled_variance(
        [('a', 5.0), ('b', 5.0), ('c', 5.0)]) == 0.0
