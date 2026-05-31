import subprocess  # nosec B404
import build_kaomoji_dict as bkd  # noqa: F401  # pylint: disable=unused-import

FREEZE_TS = 1234567890


def _cp(returncode=0, stdout="", stderr=""):
  return subprocess.CompletedProcess([], returncode, stdout, stderr)
