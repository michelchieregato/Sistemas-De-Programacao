import pandas as pd
import numpy as np


def prepare_line(line):
    if line == '':
        return
    return line.split(';')[0].strip()


class Montador(object):
    def __init__(self, file):
        self.file = file

        self.dicionarios_de_operacoes = {
            "JP": (0x0, 2), "JZ": (0x1, 2), "JN": (0x2, 2), "CN": (0x3, 1),
            "+": (0x4, 2), "-": (0x5, 2), "*": (0x6, 2), "/": (0x7, 2),
            "LD": (0x8, 2), "MM": (0x9, 2), "SC": (0xA, 2), "OS": (0xB, 1),
            "IO": (0xC, 1),
        }

        self.code = [*filter(lambda line: line != '', map(lambda x: prepare_line(x), read_file))]

    def montar(self):
        tabela = pd.DataFrame(columns=['End', 'Obj', 'Linha', 'Codigo'])

