# pylint: disable=protected-access
from unittest.mock import patch

from tests.helpers import FREEZE_TS, bkd


def test_build_combined_basic():
  kaomoji = {"¯\\_(ツ)_/¯": ["shrug"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji, word_joiner=False)
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
    result = bkd.build_combined(kaomoji, word_joiner=False)
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
    result = bkd.build_combined(kaomoji, word_joiner=False)
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


def test_build_kaomoji_lines_lowercases_tags():
  kaomoji_map = {"¯\\_(ツ)_/¯": ["SHRUG", "Shrugging"], "(◕‿◕)": ["HAPPY"]}
  lines = bkd._build_kaomoji_lines(kaomoji_map)
  assert f" word=shrug,f={bkd.KAOMOJI_FLAGS},not_a_word=true" in lines
  assert f" word=shrugging,f={bkd.KAOMOJI_FLAGS},not_a_word=true" in lines
  assert f" word=happy,f={bkd.KAOMOJI_FLAGS},not_a_word=true" in lines


def test_with_word_joiner_empty():
  assert bkd._with_word_joiner("") == ""


def test_with_word_joiner_single():
  assert bkd._with_word_joiner("a") == "\u2060a\u2060"


def test_with_word_joiner_normal():
  assert bkd._with_word_joiner("(ツ)") == "\u2060(\u2060ツ\u2060)\u2060"


def test_with_word_joiner_multiple():
  kaomoji = "(╯°□°)╯︵┻━┻"
  result = bkd._with_word_joiner(kaomoji)
  assert result == \
    "\u2060(\u2060╯\u2060°\u2060□\u2060°\u2060)\u2060╯\u2060︵\u2060┻\u2060━\u2060┻\u2060"


def test_with_word_joiner_already_has_joiner():
  result = bkd._with_word_joiner("a\u2060b")
  assert result == "\u2060a\u2060b\u2060"


def test_with_word_joiner_idempotent():
  once = bkd._with_word_joiner("abc")
  twice = bkd._with_word_joiner(once)
  assert once == twice


def test_with_word_joiner_all_joiners():
  result = bkd._with_word_joiner("\u2060\u2060")
  assert result == ""


def test_with_word_joiner_mixed():
  result = bkd._with_word_joiner("\u2060x\u2060y\u2060")
  assert result == "\u2060x\u2060y\u2060"


def test_build_kaomoji_lines_wj_enabled():
  kaomoji_map = {"(ツ)": ["test"]}
  lines = bkd._build_kaomoji_lines(kaomoji_map, word_joiner=True)
  expected_shortcut = f"  shortcut=\u2060(\u2060ツ\u2060)\u2060,f={bkd.KAOMOJI_FLAGS}"
  assert expected_shortcut in lines


def test_build_kaomoji_lines_wj_disabled():
  kaomoji_map = {"(ツ)": ["test"]}
  lines = bkd._build_kaomoji_lines(kaomoji_map, word_joiner=False)
  expected_shortcut = f"  shortcut=(ツ),f={bkd.KAOMOJI_FLAGS}"
  assert expected_shortcut in lines


def test_build_combined_word_joiner_flag():
  kaomoji = {"(ツ)": ["test"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji, word_joiner=True)
  expected = f"  shortcut=\u2060(\u2060ツ\u2060)\u2060,f={bkd.KAOMOJI_FLAGS}"
  assert expected in result

  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.build_combined(kaomoji, word_joiner=False)
  expected = f"  shortcut=(ツ),f={bkd.KAOMOJI_FLAGS}"
  assert expected in result
