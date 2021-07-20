# writetofillet
This is a script that writes a word a given amount of times to a file. It will fill a text file with a word of choice. This script is intended for command line usage and won't check for proper arguments besides the number of arguments passed.

## Usage

The arguments for this script are: the word you want to repeat, the number of times to repeat, and the filename to write that word to.

```
writetofillet BIRDISTHEWORD TIMESTOREPEAT FILENAME.TXT


This writes "BIRDISTHEWORD" 10000 times to wordtext.txt

```
writetofillet BIRDISTHEWORD 10000 wordtext.txt
```

This writes "NEVERGONNAGIVEYOUUP" in each line 5000 times to wordtext.txt

```
writetofillet NEVERGONNAGIVEYOUUP\n 5000 wordtext.txt
```

This writes "FIRESTARTER" in each line 2400 times to wordtext.txt

```
writetofillet "FIRESTARTER\n" 2400 wordtext.txt
```

## Build

If you would like to "build" this just use pyinstaller

```
pyinstaller --onefile -w "writetofillet.py" --console
```

## License

Distributed under MIT License. See `license.md` for more information.
