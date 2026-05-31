from unittest.mock import MagicMock, patch

import pytest

from tests.helpers import FREEZE_TS, _cp, bkd


def test_compile_dict_success(capsys):
  mock_run = MagicMock(return_value=_cp())
  with patch("pathlib.Path.is_file", return_value=True), patch("subprocess.run", mock_run):
    with patch("time.time", return_value=FREEZE_TS):
      combined = bkd.build_combined({"¯\\_(ツ)_/¯": ["shrug"]})
    bkd.compile_dict(combined, "/tmp/out.dict", "/tmp/jar")

  call_args = mock_run.call_args[0][0]
  assert call_args == [
    "java", "-jar", "/tmp/jar", "makedict",
    "-s", call_args[5], "-d", "/tmp/out.dict",
  ]
  assert call_args[5].endswith(".combined")

  out = capsys.readouterr().out
  assert "Dictionary created: /tmp/out.dict" in out


def test_compile_dict_failure():
  mock_run = MagicMock(return_value=_cp(returncode=1, stderr="invalid wordlist"))
  with patch("pathlib.Path.is_file", return_value=True), patch("subprocess.run", mock_run):
    with pytest.raises(RuntimeError, match="invalid wordlist"):
      bkd.compile_dict("", "/tmp/out.dict", "/tmp/jar")


def test_compile_dict_jar_missing():
  with patch("pathlib.Path.is_file", return_value=False):
    with pytest.raises(RuntimeError, match="jar not found"):
      bkd.compile_dict("", "/tmp/out.dict", "/tmp/jar")
