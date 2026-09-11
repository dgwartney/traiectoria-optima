from vertex import Vertex


class TestVertex:
    def test_equal_keys_are_equal(self):
        assert Vertex("A") == Vertex("A")

    def test_different_keys_are_not_equal(self):
        assert Vertex("A") != Vertex("B")

    def test_not_equal_to_other_types(self):
        assert Vertex("A") != "A"
        assert Vertex("A") != 1

    def test_equal_keys_have_equal_hash(self):
        assert hash(Vertex("A")) == hash(Vertex("A"))

    def test_usable_as_dict_key(self):
        d = {Vertex("A"): 1}
        assert d[Vertex("A")] == 1

    def test_key_property(self):
        assert Vertex("A").key == "A"
