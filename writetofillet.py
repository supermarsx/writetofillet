import sys

arguments = sys.argv[1:]
argumentLength = len(arguments)

messageErrorArgs = "ERROR: Wrong number of arguments"
messageUsage = "Usage: writetofillet word timestorepeat filename"

print(messageUsage)

if argumentLength != 3:
    sys.exit(messageErrorArgs)

word = arguments[0]
times = int(arguments[1])
filename = arguments[2]

hasNewLine = "\\n" in word
if hasNewLine:
    word = word.replace("\\n", "")

print(hasNewLine)

messagePlay = "Writetofillet, writing {word} {times} time(s) at {filename}".format(word=word, times=times, filename=filename)
print(messagePlay)

textFile = open(filename, "w")

print("Successfully opened file, {filename}".format(filename=filename))
for x in range(0, 5):
    print("{percent}% completed".format(percent=x*20))
    for y in range(0*x, times//5*(x+1)):
        f = textFile.write(word)
        if hasNewLine:
            textFile.write("\n")

print("100% completed")

textFile.close()
print("Closed file successfully, finished writing")
