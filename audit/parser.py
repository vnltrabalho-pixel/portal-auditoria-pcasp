import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import re

class ParserCSVFiorilli:
    """Parser para CSVs exportados do Fiorilli SCPI"""
    
    def __init__(self, caminho_arquivo: str, encoding: str = 'latin1', separator: str = ';'):
        self.caminho = caminho_arquivo
        self.encoding = encoding
        self.separator = separator
        self.df = None
        self.contas_normalizadas = {}
    
    def carregar_csv(self) -> pd.DataFrame:
        """Carrega e valida CSV"""
        try:
            self.df = pd.read_csv(
                self.caminho,
                sep=self.separator,
                encoding=self.encoding,
                dtype={
                    'MES': int,
                    'UG': str,
                    'BALCO': str,
                }
            )
            return self.df
        except Exception as e:
            raise ValueError(f"Erro ao carregar CSV: {str(e)}")
    
    def normalizar_valores(self) -> None:
        """Converte valores de vírgula decimal para float"""
        colunas_numericas = ['SALDO_INICIAL', 'CREDI', 'DEBIT', 'SALDO_FINAL',
                             'SALDO_INICIAL_D', 'SALDO_INICIAL_C', 
                             'SALDO_FINAL_D', 'SALDO_FINAL_C']
        
        for col in colunas_numericas:
            if col in self.df.columns:
                # Remove separador de milhar (.) e substitui vírgula por ponto
                self.df[col] = self.df[col].astype(str)\
                    .str.replace('.', '')\
                    .str.replace(',', '.')\
                    .astype(float)
    
    def agrupar_contas_duplicadas(self) -> pd.DataFrame:
        """
        Agrupa contas Tipo A que aparecem múltiplas vezes.
        Soma valores para a mesma conta no mesmo mês.
        """
        # Contas analíticas (TIPO == 'A') duplicadas devem ser somadas
        df_agrupado = self.df.copy()
        
        # Identificar duplicatas
        contas_duplas = df_agrupado[df_agrupado['TIPO'] == 'A']\
            .groupby(['MES', 'UG', 'BALCO']).size()
        contas_duplas = contas_duplas[contas_duplas > 1].index
        
        if len(contas_duplas) > 0:
            # Agrupar e somar
            indices_duplos = []
            for mes, ug, balco in contas_duplas:
                mask = (df_agrupado['MES'] == mes) & \
                       (df_agrupado['UG'] == ug) & \
                       (df_agrupado['BALCO'] == balco)
                
                indices = df_agrupado[mask].index.tolist()
                indices_duplos.extend(indices[1:])  # Mantém primeiro, marca resto
            
            # Somar duplicatas
            for mes, ug, balco in contas_duplas:
                mask = (df_agrupado['MES'] == mes) & \
                       (df_agrupado['UG'] == ug) & \
                       (df_agrupado['BALCO'] == balco)
                
                colunas_soma = ['SALDO_INICIAL', 'CREDI', 'DEBIT', 'SALDO_FINAL',
                               'SALDO_INICIAL_D', 'SALDO_INICIAL_C',
                               'SALDO_FINAL_D', 'SALDO_FINAL_C']
                
                df_agrupado.loc[mask, colunas_soma] = \
                    df_agrupado.loc[mask, colunas_soma].sum()
            
            # Remove duplicatas
            df_agrupado = df_agrupado.drop(indices_duplos)
        
        self.df = df_agrupado.reset_index(drop=True)
        return self.df
    
    def validar_estrutura(self) -> Tuple[bool, List[str]]:
        """Valida se CSV tem todas as colunas necessárias"""
        colunas_requeridas = [
            'MES', 'UG', 'BALCO', 'SALDO_INICIAL', 'CREDI', 'DEBIT', 
            'SALDO_FINAL', 'SALDO_INICIAL_D', 'SALDO_INICIAL_C',
            'SALDO_FINAL_D', 'SALDO_FINAL_C', 'D_C', 'TIPO'
        ]
        
        faltantes = [col for col in colunas_requeridas if col not in self.df.columns]
        
        if faltantes:
            return False, [f"Colunas faltantes: {', '.join(faltantes)}"]
        
        return True, []
    
    def processar(self) -> Tuple[pd.DataFrame, List[str]]:
        """Processa completo: carrega → valida → normaliza → agrupa"""
        erros = []
        
        try:
            self.carregar_csv()
        except ValueError as e:
            return None, [str(e)]
        
        valido, msgs = self.validar_estrutura()
        if not valido:
            return None, msgs
        
        try:
            self.normalizar_valores()
            self.agrupar_contas_duplicadas()
        except Exception as e:
            erros.append(f"Erro no processamento: {str(e)}")
            return None, erros
        
        return self.df, erros
