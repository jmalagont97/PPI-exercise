import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from extract_esm2_embeddings import mean_pool_residue_embeddings, residue_pool_mask


def test_residue_pool_mask_excludes_special_and_padding():
    input_ids = [[0, 10, 11, 2, 1]]
    attention_mask = [[1, 1, 1, 1, 0]]

    mask = residue_pool_mask(input_ids, attention_mask, special_token_ids={0, 1, 2})

    assert mask.tolist() == [[False, True, True, False, False]]


def test_mean_pool_uses_only_residue_positions():
    hidden = [[[100.0, 100.0], [1.0, 3.0], [5.0, 7.0], [200.0, 200.0]]]
    mask = [[False, True, True, False]]

    pooled = mean_pool_residue_embeddings(hidden, mask)

    assert pooled.tolist() == [[3.0, 5.0]]


def test_mean_pool_rejects_sequence_without_residue():
    with pytest.raises(ValueError, match="no valid residue"):
        mean_pool_residue_embeddings([[[1.0, 2.0]]], [[False]])
