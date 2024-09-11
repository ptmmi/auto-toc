import inquirer
from PIL import Image
import fitz # PyMuPdf
import os
import sys

import re

from typing import NamedTuple, List
from enum import Enum

def cls():
    os.system('cls' if os.name=='nt' else 'clear')

def pretty_print(toc):
    for level, heading, page in toc:
        print(f"Level {level}:\t {heading},\t p. {page}")

class Tokentype(Enum):
    TITLE = 0,
    NUMBER = 1,
    SECTION = 2

class Token(NamedTuple):
    type: Tokentype
    value: str

def get_tocless_document(pdf_path):
    document = fitz.open(pdf_path)

    assert document.is_pdf, f"Document at {pdf_path} does not seem to be a PDF."

    toc = document.get_toc()
    if (toc):

        print(
            "The provided PDF already seems to have a table of contents." 
            + "\nContinuing may overwrite the existing outline. Continue? y/N/show"
        )

        ans = inquirer.prompt([
            inquirer.Text(
                'choice', 
                message='',
                validate=lambda _, x: x in ['y', 'n', '', 'show']
            )
        ])
        print(ans)

        cls()
        match ans['choice']:
            case 's': pretty_print(toc)
            case 'show': pretty_print(toc)
            case '': exit(0)
            case 'n': exit(0)

    return document


def tokenize(words):
    """
        Parses words into tokens by matching regular expressions.
        Assumes an entry is a section number, followed by a heading,
        followed by a page number. Discards everything else.
    """

    tokens: List[Token] = []

    title_re = r"(?:[a-zA-Z]|\-)+"
    section_re = r"(?:\d+\.?)+"
    pagenumber_re = r"^\d+$"

    for word in words:

        if re.match(pagenumber_re, word):
            tokens.append(Token(Tokentype.NUMBER, word))
            continue
        
        if re.match(section_re, word):
            tokens.append(Token(Tokentype.SECTION, word))
            continue

        if re.match(title_re, word):
            tokens.append(Token(Tokentype.TITLE, word))
            continue

    return tokens


def lex(tokens):
    """
        Turns a list of tokens into a list of entries for the table of contents.
    """
    title_parts = []
    entries = []

    for index, token in enumerate(tokens):

        # assume a `SECTION` token is an entry starting token,
        # and a `NUMBER` token is an entry termination token
        match token.type:

            case Tokentype.SECTION:
                title_parts = [token.value]

            case Tokentype.TITLE:
                # the entry should start with a section
                if len(title_parts) == 0: continue
                title_parts.append(token.value)

            case Tokentype.NUMBER:
                # the entry should start with a section
                if len(title_parts) == 0: continue
                # The level is the number of non-empty strings seperated by `.`
                # in the section, e.g. `1.` is level 1, `2.3` is level 2, `4.2.23` level 3
                
                if not index == len(tokens)-1:
                    if tokens[index+1].type != Tokentype.SECTION:
                        # If the next token is not a section, then this is probably a number that
                        # occurred in the heading instead of a page number.
                        title_parts.append(token.value)
                        continue

                if len(title_parts) == 1:
                    # In this branch the entry has no title, only a section and page number.
                    # We assume this is because a section has been read with extra spaces,
                    # e.g. 
                    #   11. 7 Section title . . . . . . . . . . 305
                    #   Section(11) Page(7) Title(Section) Title(title) Page(305)
                    # instead of
                    #   Section(11.7) Title(Section) Title(title) Page(305)

                    title_parts[0] += token.value
                    continue

                section = title_parts[0]
                level = len(
                    list(filter(
                        lambda x: x != '',
                        section.split('.')
                    ))
                )
                entries.append(
                    [level, title_from(title_parts), int(token.value)]
                )

    return entries

def title_from(parts: List[str]):
    """
        Concatenates the title and performs some "sanitization".
    """

    title = ' '.join(parts)
    # sometimes, strings of periods are appended to a title depending on the character recognition.
    title = re.sub(r"\.{2,}", '', title)

    return title


if __name__=='__main__':

    if len(sys.argv) < 2:
        print("No input file provided.")
        exit(1)

    input_file = sys.argv[1]
    doc = get_tocless_document(input_file)
    cls()

    possible_pagestarts = list(map(
        lambda x: str(x['startpage']),
        doc.get_page_labels()
    ))

    print("Please enter document page range that contains the table of contents.")
    range = inquirer.prompt([
        inquirer.Text('begin', message='begin', validate=lambda _, x: x.isnumeric()),
        inquirer.Text('end', message='end', validate=lambda _, x: x.isnumeric())
    ])

    print("Please enter the page offset. This should be the PDF page that is labelled with 1.")

    if len(possible_pagestarts) > 0:
        print(f"From the document it looks like the offset is one of: {", ".join(possible_pagestarts)}")

    ans = inquirer.prompt([
        inquirer.Text(
            'offset',
            message="offset",
            default=int(range['end'])+1,
            validate=lambda _,x: x.isnumeric())
    ])

    gloabl_offset = int(ans['offset'])
    toc = []

    pages = doc.pages(
        # convert page numbers to page indices
        int(range['begin'])-1,
        int(range['end'])
    )

    for page in pages:
        blocks = page.get_textpage().extractBLOCKS()
        # discard unused info, such as bounding boxes

        for block in blocks:

            words = block[4].replace('\n', ' ').split(' ')
            tokens = tokenize(words)

            for entry in lex(tokens):
                toc.append(entry)

    print("Do you want to review the contents before setting them?")
    ans = inquirer.prompt([
        inquirer.Confirm(
            'review',
            message=f"({len(toc)} entries)",
            default=False
        )
    ])

    if ans['review']:
        cls()
        pretty_print(toc)

        fans = inquirer.prompt([
            inquirer.Confirm(
                'confirm',
                message=f"Set this table of contents?",
                default=True
            )
        ])

        if not fans['confirm']:
            exit(0)

    # apply the global offset
    for entry in toc:
        entry[2] += gloabl_offset

    doc.set_toc(toc)

    ans = inquirer.prompt([
        inquirer.Text(
            'fname',
            message="Please provide an output filename",
            default=doc.name
        )
    ])

    doc.save(ans['fname'])
    print("Done.")