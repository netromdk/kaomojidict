# Kaomoji dictionaries for HeliBoard and AOSP keyboards

Kaomoji (顔文字) are Japanese-style emoticons built from text characters,
e.g. `¯╲_(ツ)_╱¯` or `(╯°□°)╯︵┻━┻`. [Wikipedia](https://en.wikipedia.org/wiki/Kaomoji)

## Build

```sh
git submodule update --init --recursive
./build_all.sh
```

`build_all.sh` produces **two** `.dict` files per locale:

| File | Tags used |
|------|-----------|
| `kaomoji_en.dict` | locale-specific (`en`) |
| `kaomoji_en_all_locales.dict` | all locales merged (`en` + `da` + ...) |

The `_all_locales` variant has more trigger words per Kaomoji at the cost of
mixing languages, so a Danish tag can trigger an English Kaomoji suggestion.

Requires `java` on PATH.

## Format

A single `kaomoji.json` contains all locales with per-locale tags and descriptions:

```json
{
  "locales": ["en", "da"],
  "description": {
    "en": "English Kaomoji dictionary",
    "da": "Dansk Kaomoji-ordbog"
  },
  "version": 1,
  "kaomoji": {
    "(◕‿◕)": {
      "en": ["happy", "cute"],
      "da": ["glad", "sød"]
    },
    "(╯°□°)╯︵┻━┻": {
      "*": ["flip"],
      "en": ["tableflip", "rage"],
      "da": ["bordvæltning", "raseri"]
    }
  }
}
```

A special `"*"` locale adds tags shared by all locales. These are prepended
before each locale's specific tags.

Build one locale at a time:

```sh
./build_kaomoji_dict.py kaomoji.json --locale en
./build_kaomoji_dict.py --locale da
```

Note: It defaults to using `kaomoji.json` if none is given.

Or use `--all-locales` to merge all locales' tags into a single dictionary with
more trigger words for each Kaomoji:

```sh
./build_kaomoji_dict.py --locale en --all-locales
```

Version is not written back to `kaomoji.json` by default. Use `--bump` to
increment the version in the JSON file after building:

```sh
./build_kaomoji_dict.py kaomoji.json --locale en --bump
```

## Merge with upstream emoji dictionaries

To get Kaomoji suggestions alongside the official upstream emoji entries,
download the `.combined` wordlists for each locale:

```sh
wget https://codeberg.org/Helium314/aosp-dictionaries/raw/branch/main/emoji_cldr_signal_wordlists/emoji_en.combined
wget https://codeberg.org/Helium314/aosp-dictionaries/raw/branch/main/emoji_cldr_signal_wordlists/emoji_da.combined
```

Then run the merge step manually using `--merge-combined` / `-m`:

```sh
./build_kaomoji_dict.py --locale en --merge-combined emoji_en.combined \
                        --output kaomoji_en.dict
./build_kaomoji_dict.py --locale en --all-locales --merge-combined emoji_en.combined \
                        --output kaomoji_en_combined.dict
```

Kaomoji entries are appended to the upstream wordlist, producing a single
`.dict` per locale with both emoji and Kaomoji. Both standalone and merged
dictionaries use `kaomoji:<locale>` as the dictionary type prefix.
Note that Kaomoji appear as text suggestions, not rendered emoji.
They consist of multiple Unicode code points (e.g., `(╯°□°)╯︵┻━┻`), so
HeliBoard displays them inline as text.

The merged description follows the format:
`<kaomoji_desc> [<all locales>] (<orig_desc> v<orig_version>)`.

Note: `build_all.sh` produces standalone dicts only (`kaomoji_en.dict` and
`kaomoji_en_all_locales.dict`). It does not merge with upstream combined
files. Use the commands above for that.

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
