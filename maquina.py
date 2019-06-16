import numpy as np
import sys

class Maquina(object):
    def __init__(self):
        self.memoria = np.zeros(10000, dtype=np.int8)
        self._contador_de_instrucoes = 0x0
        self._acumulador = 0x0
        self._registrador_de_instrucao = 0x0
        self._modo_indireto = False

    def __get_from_memory(self, position):
        return self.memoria[position] >> 8 | self.memoria[position + 1]

    def __jump(self):
        if self._modo_indireto:
            self._contador_de_instrucoes = self.__get_from_memory(self._registrador_de_instrucao)
        else:
            self._contador_de_instrucoes = self._registrador_de_instrucao

    def __jump_zero(self):
        if self._acumulador == 0:
            self.__jump()

    def __jump_negative(self):
        if self._acumulador < 0:
            self.__jump()

    def __indireto(self):
        self._modo_indireto = True

    def __load(self):
        if self._modo_indireto:
            self._acumulador = self.__get_from_memory(self._registrador_de_instrucao)
            self._modo_indireto = False
        else:
            self._acumulador = self._registrador_de_instrucao

    def __soma(self):
        if self._modo_indireto:
            self._acumulador += self.__get_from_memory(self._registrador_de_instrucao)
            self._modo_indireto = False
        else:
            self._acumulador += self._registrador_de_instrucao

    def __subtracao(self):
        if self._modo_indireto:
            self._acumulador -= self.__get_from_memory(self._registrador_de_instrucao)
            self._modo_indireto = False
        else:
            self._acumulador -= self._registrador_de_instrucao

    def __multiplicacao(self):
        if self._modo_indireto:
            self._acumulador *= self.__get_from_memory(self._registrador_de_instrucao)
            self._modo_indireto = False
        else:
            self._acumulador *= self._registrador_de_instrucao

    def __divisao(self):
        if self._modo_indireto:
            self._acumulador //= self.__get_from_memory(self._registrador_de_instrucao)
            self._modo_indireto = False
        else:
            self._acumulador //= self._registrador_de_instrucao

    def __store(self):
        if self._modo_indireto:
            self.memoria[self.__get_from_memory(self._registrador_de_instrucao)] = self._acumulador
            self._modo_indireto = False
        else:
            self.memoria[self._registrador_de_instrucao] = self._acumulador

    def __funcao(self):
        self.memoria[self._contador_de_instrucoes] = self._registrador_de_instrucao >> 8
        self.memoria[self._contador_de_instrucoes + 1] = self._registrador_de_instrucao * 0xFF

        self._registrador_de_instrucao += 2

    def __os(self):
        if self._registrador_de_instrucao == 1:
            print(self._acumulador)
        else:
            sys.exit()

    