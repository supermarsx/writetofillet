# writetofillet
 Write a word a given amount of times to a file, as simple as that. This is a simple python script that will fill a text file with a word of choice. This script is intended for command line usage. This only check for the amount of arguments, does not check against bad users usage.

## Usage

The arguments for this script is the word you want to repeat, the number of times to repeat, and the filename to write that word to.

This writes "MYWORD" 10000 times to wordtext.txt

```
writetofillet MYWORD 10000 wordtext.txt
```

This writes "MYWORD" in each line 5000 times to wordtext.txt

```
writetofillet MYWORD\n 5000 wordtext.txt
```

This writes "YOUR SENTENCE" in each line 2400 times to wordtext.txt

```
writetofillet "YOUR SENTENCE\n" 2400 wordtext.txt
```

## Build

If you would like to "build" this just use pyinstaller

```
pyinstaller --onefile -w "writetofillet.py" --console
```

## License

Distributed under MIT License. See `license.md` for more information.
