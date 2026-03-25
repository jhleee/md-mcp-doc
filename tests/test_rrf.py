from core.rrf import reciprocal_rank_fusion


def test_single_list():
    result = reciprocal_rank_fusion(["a", "b", "c"])
    keys = [k for k, _ in result]
    assert keys == ["a", "b", "c"]


def test_two_lists_merge():
    list1 = ["a", "b", "c"]
    list2 = ["b", "c", "d"]
    result = reciprocal_rank_fusion(list1, list2)
    scores = dict(result)
    # "b" appears in both lists, should have highest score
    assert scores["b"] > scores["a"]
    assert scores["b"] > scores["d"]


def test_identical_lists():
    result = reciprocal_rank_fusion(["x", "y"], ["x", "y"])
    keys = [k for k, _ in result]
    assert keys[0] == "x"


def test_empty_lists():
    result = reciprocal_rank_fusion([], [])
    assert result == []


def test_disjoint_lists():
    result = reciprocal_rank_fusion(["a", "b"], ["c", "d"])
    keys = [k for k, _ in result]
    assert set(keys) == {"a", "b", "c", "d"}
