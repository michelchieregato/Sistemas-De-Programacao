import pandas as pd
import numpy as np

OPERACOES = {
    "JP": 0x0, "JZ": 0x1, "JN": 0x2, "CN": 0x3,
    "+": 0x4, "-": 0x5, "*": 0x6, "/": 0x7,
    "LD": 0x8, "MM": 0x9, "SC": 0xA, "OS": 0xB,
    "IO": 0xC,
}

TAMANHO_DAS_OPERACOES = {
    "JP": 2, "JZ": 2, "JN": 2, "CN": 1,
    "+": 2, "-": 2, "*": 2, "/": 2,
    "LD": 2, "MM": 2, "SC": 2, "OS": 1,
    "IO": 1,
}


def prepare_line(line):
    if line == '':
        return
    return line.split(';')[0].strip()


def try_to_make_int(op):
    try:
        return int(op)
    except:
        return op


class Montador(object):
    def __init__(self, file):

        with open(file, 'r') as f:
            read_file = f.readlines()

        codigo = [*filter(lambda line: len(line), map(lambda x: prepare_line(x).split(), read_file))]

        for linha in codigo:
            if len(linha) == 2:
                linha.insert(0, '')

        self.contador_de_instrucoes = 0
        self.codigo_tabelado = pd.DataFrame(codigo, columns=['Label', 'Operacao', 'Operador'])
        self.codigo_tabelado['Operador'] = self.codigo_tabelado['Operador'].apply(lambda op: try_to_make_int(op))

        self.tabela_final = pd.DataFrame(columns=['End', 'Obj', 'Linha', 'Codigo'])
        self.tabela_labels = pd.DataFrame(columns=['Label', 'Valor'])

        self.inicio_do_programa = 0
        self.dicionario_de_labels = dict()

    def montar(self):
        self.primeiro_passo()
        self.dicionario_de_labels = dict(zip(self.tabela_labels.Label, self.tabela_labels.Valor))
        self.contador_de_instrucoes = 0
        self.segundo_passo()
        self.tabela_final.sort_values('Linha')

    def primeiro_passo(self):
        for index, linha_de_codigo in self.codigo_tabelado.iterrows():
            if linha_de_codigo['Label']:
                self.tabela_labels.loc[index] = [linha_de_codigo['Label'], hex(self.contador_de_instrucoes)]

            if linha_de_codigo['Operacao'] == '@':
                self.inicio_do_programa = self.contador_de_instrucoes = linha_de_codigo['Operador']
                self.tabela_final.loc[index] = [
                    '',
                    '',
                    index + 1,
                    ' '.join(linha_de_codigo.apply(str).values).strip()
                ]
            elif linha_de_codigo['Operacao'] == '$':
                self.tabela_final.loc[index] = [
                    hex(self.contador_de_instrucoes),
                    hex(linha_de_codigo['Operador']),
                    index + 1,
                    ' '.join(linha_de_codigo.apply(str).values).strip()
                ]
                self.contador_de_instrucoes += linha_de_codigo['Operador']
            elif linha_de_codigo['Operacao'] == 'K':
                self.tabela_final.loc[index] = [
                    hex(self.contador_de_instrucoes),
                    hex(linha_de_codigo['Operador']),
                    index + 1,
                    ' '.join(linha_de_codigo.apply(str).values).strip()
                ]
                self.contador_de_instrucoes += 1
            elif linha_de_codigo['Operacao'] == '#':
                continue
            else:
                self.contador_de_instrucoes += TAMANHO_DAS_OPERACOES[linha_de_codigo['Operacao']]

    def segundo_passo(self):
        self.codigo_tabelado['Operador Recalculado'] = self.codigo_tabelado['Operador'].apply(
            lambda op: self.__update_table(op))
        for index, linha_de_codigo in self.codigo_tabelado.iterrows():
            if linha_de_codigo['Operacao'] == '@':
                self.inicio_do_programa = self.contador_de_instrucoes = int(linha_de_codigo['Operador Recalculado'], 0)
                continue
            elif linha_de_codigo['Operacao'] == '$':
                self.contador_de_instrucoes += int(linha_de_codigo['Operador Recalculado'], 0)
                continue
            elif linha_de_codigo['Operacao'] == 'K':
                self.contador_de_instrucoes += 1
                continue
            elif linha_de_codigo['Operacao'] == '#':
                self.tabela_final.loc[index] = [
                    hex(self.contador_de_instrucoes),
                    linha_de_codigo['Operador'],
                    index + 1,
                    ' '.join(linha_de_codigo.apply(str).values).strip()
                ]
                continue

            op = OPERACOES[linha_de_codigo['Operacao']]
            if TAMANHO_DAS_OPERACOES[linha_de_codigo['Operacao']] == 1:
                value = hex(op << 4 | int(linha_de_codigo['Operador Recalculado'], 16))
            else:
                value = op << 12 | int(linha_de_codigo['Operador Recalculado'], 16)
                value = hex(value >> 8) + hex(value & 0xFF)[2:]

            self.tabela_final.loc[index] = [
                hex(self.contador_de_instrucoes),
                value,
                index + 1,
                ' '.join(linha_de_codigo.drop(['Operador Recalculado']).apply(str).values).strip()
            ]
            self.contador_de_instrucoes += TAMANHO_DAS_OPERACOES[linha_de_codigo['Operacao']]

    def __update_table(self, operador):
        operador = str(operador)
        if '+' in operador:
            aux = operador.split('+')
            return hex(int(self.dicionario_de_labels[aux[0]], 0) + int(aux[1]))
        elif '-' in operador:
            aux = operador.split('+')
            return hex(int(self.dicionario_de_labels[aux[0]], 0) - int(aux[1]))
        elif operador in self.dicionario_de_labels.keys():
            return self.dicionario_de_labels[str(operador)]

        return hex(int(operador.replace('/', '0x'), 0))
