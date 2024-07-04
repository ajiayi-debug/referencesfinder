from gptapi import *
from pdftotext import *
from filenames import *

def main():
    text=full_cycle(PDF,filename="extracted")
    output=request(text)
    print(output)

if __name__=="__main__":
    main()
    