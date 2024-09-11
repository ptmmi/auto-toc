# auto-toc

A (probably too) simple python script that reads in a table of contents
and adds it to the index of the PDF (such that document viewers can 
display an outline).

There are probably a lot of unhandled edge cases.

The Program currently assumes that
- sections are labelled with arabic numerals and subsections are seperated by `.`s
- the section number is followed by the heading, which is followed by its page number. Multi-line headings should be fine.

## Quick Start

Install the dependencies and run the main script.
```
$ pip install -r requirements.txt
$ python auto-toc.py <your input file>
```