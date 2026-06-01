from unittest.mock import patch

from tests.helpers import FREEZE_TS, bkd


def test_build_combined_basic():
  kaomoji = {"¯\\_(ツ)_/¯": ["shrug"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji)
  lines = result.split("\n")
  assert len(lines) == 1 + sum(2 * len(v) for v in kaomoji.values())
  assert lines[0] == (
    "dictionary=kaomoji:en,locale=en,"
    "description=Kaomoji dictionary,"
    f"date={FREEZE_TS},version=1"
  )
  assert lines[1] == f" word=shrug,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[2] == rf"  shortcut=¯\_(ツ)_/¯,f={bkd.KAOMOJI_FLAGS}"


def test_build_combined_empty():
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined({})
  lines = result.split("\n")
  assert len(lines) == 1
  assert f"date={FREEZE_TS}" in lines[0]
  assert "version=1" in lines[0]


def test_build_combined_multiple_words():
  kaomoji = {"(╯°□°)╯︵┻━┻": ["tableflip", "rage"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji)
  lines = result.split("\n")
  assert len(lines) == 1 + sum(2 * len(v) for v in kaomoji.values())
  assert lines[1] == f" word=tableflip,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[2] == f"  shortcut=(╯°□°)╯︵┻━┻,f={bkd.KAOMOJI_FLAGS}"
  assert lines[3] == f" word=rage,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[4] == f"  shortcut=(╯°□°)╯︵┻━┻,f={bkd.KAOMOJI_FLAGS}"


def test_build_combined_multiple_kaomoji():
  kaomoji = {
    "¯\\_(ツ)_/¯": ["shrug"],
    "(◕‿◕)": ["happy"],
  }
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji)
  lines = result.split("\n")
  assert len(lines) == 1 + sum(2 * len(v) for v in kaomoji.values())
  assert lines[1] == f" word=shrug,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[3] == f" word=happy,f={bkd.KAOMOJI_FLAGS},not_a_word=true"


def test_build_combined_custom_metadata():
  kaomoji = {"¯\\_(ツ)_/¯": ["shrug"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji, locale="ja", description="My dict", version=3)
  first = result.split("\n", maxsplit=1)[0]
  assert "locale=ja" in first
  assert "kaomoji:ja" in first
  assert "description=My dict" in first
  assert "version=3" in first


def test_build_combined_special_chars():
  kaomoji = {"🔥": ["fire", "flame🔥"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji)
  lines = result.split("\n")
  assert f" word=fire,f={bkd.KAOMOJI_FLAGS},not_a_word=true" in lines
  assert f"  shortcut=🔥,f={bkd.KAOMOJI_FLAGS}" in lines
  assert f" word=flame🔥,f={bkd.KAOMOJI_FLAGS},not_a_word=true" in lines


def test_KAOMOJI_FLAGS_value():
  assert bkd.KAOMOJI_FLAGS == bkd.NOT_A_WORD | bkd.HAS_EMOJI | bkd.PROBING


def test_build_combined_dictionary_type():
  result = bkd.build_combined({}, locale="en")
  header = result.split("\n", maxsplit=1)[0]
  assert "dictionary=kaomoji:en" in header
  assert "emoji:en" not in header
