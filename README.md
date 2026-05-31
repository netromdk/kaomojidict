# Kaomoji dictionaries for HeliBoard and AOSP keyboards

## Build

```sh
git submodule update --init --recursive
./build_all.sh
```

Requires `java` on PATH.

## Format

Each JSON file contains a locale, description, version, and map of kaomoji to search tags:

```json
{
  "locale": "en",
  "description": "Kaomoji dictionary",
  "version": 1,
  "kaomoji": {
    "(◕‿◕)": ["happy", "cute"],
    "(╯°□°)╯︵┻━┻": ["tableflip", "rage"]
  }
}
```

Build with `build_kaomoji_dict.py`:

```sh
python build_kaomoji_dict.py kaomoji_en.json
```

## Tests

Run all unit tests:

```sh
python -m pytest tests/
```

Run `./check.sh` to run all linters (`flake8`, `bandit`, `vulture`, `pylint`,
`mypy`, `vermin`, `shellcheck`) and unit tests (`pytest`).

## Acknowledgments

Thanks to [HeliBoard](https://github.com/Helium314/HeliBoard) for making an
awesome keyboard app, and to [remi0s](https://github.com/remi0s) for
[`aosp-dictionary-tools`](https://github.com/remi0s/aosp-dictionary-tools/),
which this project uses to build `.dict` files.
