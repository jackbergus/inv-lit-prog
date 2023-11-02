__author__ = "Giacomo Bergami"
__copyright__ = "Copyright 2023"
__credits__ = ["Giacomo Bergami"]
__license__ = "GPL"
__version__ = "3.0"
__maintainer__ = "Giacomo Bergami"
__email__ = "bergamigiacomo@gmail.com"
__status__ = "Production"
from typing import TypedDict
from argparse import ArgumentParser
try:
    from typing_extensions import Required
except ImportError:
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class Required(Generic[T]):
        pass


import regex
import itertools
from pathlib import Path

def product_dict(**kwargs):
    """
    Providing the cartesian product across all the lists of the provided dictionary

    :param kwargs:  The dictionary
    :return:        {x->y}_{x\in kwargs.keys(), y\in kwargs[x]}
    """
    keys = kwargs.keys()
    for instance in itertools.product(*kwargs.values()):
        yield dict(zip(keys, instance))

def expand_with_generic(d, var_rgx, str, callable):
    """
    Replacing all the occurrences of the regex match in str with the output provided by callble

    :param d:           Additional value coming from the outside
    :param var_rgx:     Regex to be matched
    :param str:         String where to find multiple matches of the regex
    :param callable:    Callable object/function to be called over the matched data, the regex, and the additional value
    :return:            The expanded string
    """
    init = ""
    end = 0
    for m in var_rgx.finditer(str):
        c = m.capturesdict()
        init = init + str[end:m.start()]
        init = init + callable(d, c, str, var_rgx)
        end = m.end()
    return init + str[end:]

def expand_with_lambda(d, var_rgx, str):
    return expand_with_generic(d, var_rgx, str, lambda d, c, str, rgx: d.get(c["varmatch"][0], ""))

example = """
// §f:funzione!
void funzione() {

// §[literate1: now, we are performing a sum]§
   x+y=z;
// §[/literate1]§


// §[return1: then, we are returning a value]§
   return k;
// §[/return1]§
}
// §f:funzione.


// §f:funzione45!
void funzione45() {

// §[literate2: we are doing another sum]§
   x+y=z;
// §[/literate2]§


// §[return7: then, we return yet another value]§
   return k;
// §[/return7]§
}
// §f:funzione45.
"""

class Coordinates(TypedDict):
    lineno : Required[int]
    linestart : Required[int]
    char : Required[int]
    fullchar : Required[int]

def coordinates(lineno, linestart, fullchar):
    a: Coordinates = {'lineno': lineno, 'linestart': linestart, 'char':fullchar-linestart, 'fullchar': fullchar}
    return a

class Capture(TypedDict):
    d: dict[str, list[str]]
    begin: Coordinates
    end: Coordinates

def capture(d : dict[str, list[str]], begin : Coordinates, end : Coordinates):
    a: Capture = {'d': d, 'begin': begin, 'end': end}
    return a

class LineNos:
    def __init__(self, string):
        end = '.*\n'
        self.line = []
        self.startsAt = []
        import re
        for m in re.finditer(end, string):
            self.line.append(m.end())
            self.startsAt.append(m.start())

    def startsFrom(self, lineno):
        return self.startsAt[lineno]

    def __call__(self, *args, **kwargs):
        d = dict()
        for key, value in kwargs.items():
            a = getattr(value, key)
            d[key] = next(i for i in range(len(self.line)) if self.line[i] > a())
        return d

class Generalizer:
    def __init__(self, rgx : str):
        self.rgx = regex.compile(rgx)

    def __call__(self, *args, **kwargs)->dict[str, list[Capture]]:
        result = dict()
        for key, value in kwargs.items():
            d : list[Capture] = list()
            ln = LineNos(value)
            ## Getting the universal quantifiers
            for m in self.rgx.finditer(value):
                D = ln(start=m, end=m)
                charStartPlusOne = ln.startsFrom(D["start"])
                charEndPlusOne = ln.startsFrom(D["end"])
                d.append(capture(m.capturesdict(),
                                 coordinates(D["start"], charStartPlusOne, m.start()),
                                 coordinates(D["end"],  charEndPlusOne, m.end()))
                         )
            result[key] = d
        return result

regex_open_description = Generalizer("§\[(?P<name>[^[:]+):(?P<commento>[^\]§]+)\]§")
regex_close_description = Generalizer("§\[\/(?P<name>[^[:]+)\]§")
regex_open_function = Generalizer("§f:(?P<name>[^[\!\s]+)!")
regex_close_function = Generalizer("§f:(?P<name>[^[\.\s]+)\.")



def PairMatch(b,e,d)->dict[str, tuple[list[Capture], list[Capture]]]:
    begin_block:dict[str,list[Capture]] = b(**d)
    end_block:dict[str,list[Capture]] = e(**d)
    blocks:dict[str, tuple[list[Capture], list[Capture]]] = dict()
    for k in set(begin_block.keys()).intersection(set(end_block.keys())):
        t :tuple[list[Capture], list[Capture]] = tuple([begin_block[k], end_block[k]])
        blocks[k] = t
    return blocks

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.



class Description:
    sliceName:str
    description:str
    begin:Coordinates
    end:Coordinates

    def __init__(self, sliceName=None, description=None, begin=None, end=None):
        self.sliceName = sliceName
        self.description = description
        self.begin = begin
        self.end = end

    def toLatex(self,filename,functionName):
        return (self.description +
                "\n\n\lstinputlisting[firstline ="+
                str(self.begin["lineno"])+
                ", lastline = "+
                str(self.end.beginline)+
                ",caption={"+
                functionName+
                " in "+
                filename+
                ", line "+
                str(self.begin["lineno"])+
                " onwards.},label={"+
                self.sliceName+"}]{"+
                filename+
                "}\n\n")

class FunctionMatch:
    name:str
    begin:int
    end:int
    beginline:int
    endline:int
    def __init__(self,name, b,e,bl,el):
        self.name = name
        self.begin = b
        self.end = e
        self.beginline = bl
        self.endline = el
        self.blocks = dict()

    def extendWith(self, end):
        if (self.name == end.name):
            self.begin = min(self.begin, end.begin)
            self.end = max(self.end, end.end)
            self.beginline = min(self.beginline,end.beginline)
            self.endline = max(self.endline,end.endline)

    def retrieveRelevantBlocks(self, d):
        for blockname,block in d.items():
            if (block.begin["lineno"] >= self.beginline) and (block.end.beginline <= self.endline):
                self.blocks[blockname] = block

    def toLatex(self,filename):
        l = []
        for x in self.blocks:
            l.append(self.blocks[x])
        l.sort(key=lambda x:x.begin["lineno"])
        return "\n".join(map(lambda x : x.toLatex(filename,self.name), l))


def processGeneralMatch(ls, selecter):
    D = dict()
    for x in ls:
        d = x["d"]
        name = selecter(d)
        begin = x["begin"]["fullchar"]
        bl = x["begin"]["lineno"]
        end = x["end"]["fullchar"]
        el = x["end"]["lineno"]
        D[name] = FunctionMatch(name, begin, end, bl, el)
    return D

def processDescriptionMatch(ls, selecter, descriptor):
    D = dict()
    for x in ls:
        d = x["d"]
        name = selecter(d)
        descr = descriptor(d)
        begin = x["begin"]
        end = x["end"]
        D[name] = Description(name, descr, begin, end)
    return D

def matcher(functionRemarking, filename, grouper, lam):
    declaredFunctionsBegin = grouper(functionRemarking[filename][0], lam)
    declaredFunctionsEnd = grouper(functionRemarking[filename][1], lam)
    for k in set(declaredFunctionsBegin.keys()).intersection(set(declaredFunctionsEnd.keys())):
        declaredFunctionsBegin[k].extendWith(declaredFunctionsEnd[k])
    del declaredFunctionsEnd
    return declaredFunctionsBegin

def matcher2(functionRemarking, filename, grouper, grouper2, lam, lam2):
    declaredFunctionsBegin = grouper(functionRemarking[filename][0], lam, lam2)
    declaredFunctionsEnd = grouper2(functionRemarking[filename][1], lam)
    for k in set(declaredFunctionsBegin.keys()).intersection(set(declaredFunctionsEnd.keys())):
        fst = declaredFunctionsBegin[k].end
        declaredFunctionsBegin[k].begin = fst
        declaredFunctionsBegin[k].end = declaredFunctionsEnd[k]
    del declaredFunctionsEnd
    return declaredFunctionsBegin

def files_reading(filenames, latexfile):
    with open(latexfile, 'w') as latex:
        files = dict()
        for filename in filenames:
            with open(filename, 'r') as file:
                files[filename] = file.read()
        descriptionBlockOfCodeInFunction = PairMatch(regex_open_description, regex_close_description, files)
        functionRemarking = PairMatch(regex_open_function, regex_close_function, files)
        for filename in files:
            declaredFunctionsBegin = matcher(functionRemarking, filename, processGeneralMatch, lambda x: x["name"][0])
            blocksOfCode = matcher2(descriptionBlockOfCodeInFunction, filename, processDescriptionMatch, processGeneralMatch, lambda x: x["name"][0], lambda x: x["commento"][0])
            if (len(declaredFunctionsBegin)>0) and (len(blocksOfCode)>0):
                for k,v in declaredFunctionsBegin.items():
                    v.retrieveRelevantBlocks(blocksOfCode)
                    latex.write(v.toLatex(filename))

def file_crawling(dirs, exts, latexfile):
    import os
    L = []
    for dir in dirs:
        for root, dirs, files in os.walk(dirs):
            for file in files:
                for ext in exts:
                    if file.endswith(ext):
                        L.append(os.path.join(root, file))
    files_reading(L, latexfile)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = ArgumentParser(
                    prog='Inverse Literate Programming',
                    description='Generates a LaTeX file in the style of Literate Programming from the source code',
                    epilog='All Rights are Reserved')
    parser.add_argument('-d', '--dirs', nargs='+', default=[], help="List of directories to crawl", required=True)
    parser.add_argument('-x', '--exts', nargs='+', default=[], help="List of extension of allowed files", required=True)
    parser.add_argument('--latex', type=str, default="whole_codebase.tex", help='The name of the LaTeX file to be generated in a bulk', required=True)
    args = parser.parse_args()
    file_crawling(args.dirs, args.exts, args.latex)





# See PyCharm help at https://www.jetbrains.com/help/pycharm/
