from gpt import *
from pdftotext import *
from dotenv import load_dotenv
load_dotenv()
PDF=os.getenv("PDF")

def main():
    text=full_cycle(PDF,filename="extracted")
    output=request(text)
    ref=findref(output)
    ref=eval(ref) if ref else []
    get_summary_of_existing(ref)

if __name__=="__main__":
    main()
    