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

## Merge with upstream emoji dictionaries

To get Kaomoji suggestions alongside the official upstream emoji entries,
download the `.combined` wordlists and use `--merge-combined`:

```sh
wget https://codeberg.org/Helium314/aosp-dictionaries/raw/branch/main/emoji_cldr_signal_wordlists/emoji_en.combined
wget https://codeberg.org/Helium314/aosp-dictionaries/raw/branch/main/emoji_cldr_signal_wordlists/emoji_da.combined
./build_all.sh
```

Kaomoji entries are appended to the upstream wordlist, producing a single
`.dict` per locale with both emoji and Kaomoji. Note that Kaomoji appear as
text suggestions, not rendered emoji. They consist of multiple Unicode code
points (e.g., `(╯°□°)╯︵┻━┻`), so HeliBoard displays them inline as text.

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
