import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class ErroAuditoria:
    """Classe para armazenar erros encontrados"""
    tipo: str  # 'erro' ou 'aviso'
    codigo_conta: str
    descricao: str
    valor_esperado: float = None
    valor_obtido: float = None
    linha: int = None

class ValidadorPCAsp:
    """Validador de balancetes PCASP"""
    
    TOLERANCIA = 0.01  # Tolerância para arredondamento
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.erros: List[ErroAuditoria] = []
        self.avisos: List[ErroAuditoria] = []
    
    def validar_formula_debito_credito(self) -> List[ErroAuditoria]:
        """
        Valida: SALDO_INICIAL + Débitos - Créditos = SALDO_FINAL
        Respeita natureza D/C
        """
        erros = []
        
        for idx, row in self.df.iterrows():
            saldo_inicial = row['SALDO_INICIAL']
            debitos = row['DEBIT']
            creditos = row['CREDI']
            saldo_final = row['SALDO_FINAL']
            
            # Cálculo esperado
            saldo_calculado = saldo_inicial + debitos - creditos
            
            # Verifica diferença
            diferenca = abs(saldo_calculado - saldo_final)
            
            if diferenca > self.TOLERANCIA:
                erros.append(ErroAuditoria(
                    tipo='erro',
                    codigo_conta=row['BALCO'],
                    descricao=f"Fórmula D/C não fechou. SI({saldo_inicial}) + D({debitos}) - C({creditos}) ≠ SF({saldo_final})",
                    valor_esperado=saldo_calculado,
                    valor_obtido=saldo_final,
                    linha=idx + 2  # +2 para considerar header
                ))
        
        return erros
    
    def validar_debito_credito_separados(self) -> List[ErroAuditoria]:
        """
        Valida as colunas separadas D/C:
        - Para D (Devedor): SI_D + Débitos - Créditos = SF_D
        - Para C (Credor): SI_C + Créditos - Débitos = SF_C
        """
        erros = []
        
        for idx, row in self.df.iterrows():
            natureza = row['D_C']
            
            if pd.isna(natureza) or natureza == '':
                continue  # Pula contas sem natureza definida
            
            if natureza == 'D':
                # Devedor
                si_d = row['SALDO_INICIAL_D']
                sf_d = row['SALDO_FINAL_D']
                debitos = row['DEBIT']
                creditos = row['CREDI']
                
                sf_esperado = si_d + debitos - creditos
                
            elif natureza == 'C':
                # Credor
                si_c = row['SALDO_INICIAL_C']
                sf_c = row['SALDO_FINAL_C']
                creditos = row['CREDI']
                debitos = row['DEBIT']
                
                sf_esperado = si_c + creditos - debitos
            else:
                continue
            
            diferenca = abs(sf_esperado - row[f'SALDO_FINAL_{natureza}'])
            
            if diferenca > self.TOLERANCIA:
                erros.append(ErroAuditoria(
                    tipo='erro',
                    codigo_conta=row['BALCO'],
                    descricao=f"Validação D/C ({natureza}) falhou",
                    valor_esperado=sf_esperado,
                    valor_obtido=row[f'SALDO_FINAL_{natureza}'],
                    linha=idx + 2
                ))
        
        return erros
    
    def validar_balanceamento_ativo_passivo(self) -> List[ErroAuditoria]:
        """
        Valida: Total ATIVO = Total (PASSIVO + PL)
        Conta 100... vs 200... no SALDO_FINAL
        """
        erros = []
        
        # Agrupa por MES/UG
        for (mes, ug), grupo in self.df.groupby(['MES', 'UG']):
            # Identifica contas raiz
            ativo = grupo[grupo['BALCO'].str.startswith('1')]['SALDO_FINAL'].sum()
            passivo_pl = grupo[grupo['BALCO'].str.startswith('2')]['SALDO_FINAL'].sum()
            
            diferenca = abs(ativo - passivo_pl)
            
            if diferenca > self.TOLERANCIA:
                erros.append(ErroAuditoria(
                    tipo='aviso',
                    codigo_conta=f'MES:{mes} UG:{ug}',
                    descricao=f"Desbalanceamento Ativo-Passivo. ATIVO={ativo}, PASSIVO+PL={passivo_pl}",
                    valor_esperado=ativo,
                    valor_obtido=passivo_pl
                ))
        
        return erros
    
    def validar_contas_tipo_sintetica(self) -> List[ErroAuditoria]:
        """
        Contas Sintéticas devem ser iguais à soma de suas Analíticas
        Ex: 111000000000000 = soma(111100000000000, 111110000000000, ...)
        """
        erros = []
        
        sinteticas = self.df[self.df['TIPO'] == 'S']
        
        for idx, row_sintetica in sinteticas.iterrows():
            codigo = row_sintetica['BALCO']
            mes = row_sintetica['MES']
            ug = row_sintetica['UG']
            
            # Contas analíticas que começam com o código sintético
            mask_analiticas = (
                (self.df['BALCO'].str.startswith(codigo)) &
                (self.df['BALCO'] != codigo) &  # Exclui ela mesma
                (self.df['MES'] == mes) &
                (self.df['UG'] == ug) &
                (self.df['TIPO'] == 'A')
            )
            
            analiticas = self.df[mask_analiticas]
            
            if len(analiticas) > 0:
                soma_analiticas = analiticas['SALDO_FINAL'].sum()
                saldo_sintetica = row_sintetica['SALDO_FINAL']
                
                diferenca = abs(soma_analiticas - saldo_sintetica)
                
                if diferenca > self.TOLERANCIA:
                    erros.append(ErroAuditoria(
                        tipo='aviso',
                        codigo_conta=codigo,
                        descricao=f"Sintética não soma suas Analíticas",
                        valor_esperado=soma_analiticas,
                        valor_obtido=saldo_sintetica,
                        linha=idx + 2
                    ))
        
        return erros
    
    def executar_todas_validacoes(self) -> Dict:
        """Executa todas as validações"""
        resultado = {
            'total_linhas': len(self.df),
            'contas_validadas': 0,
            'erros': [],
            'avisos': [],
            'resumo': {}
        }
        
        # Validação 1: Fórmula D/C
        v1 = self.validar_formula_debito_credito()
        resultado['erros'].extend([{
            'tipo': e.tipo,
            'codigo_conta': e.codigo_conta,
            'descricao': e.descricao,
            'valor_esperado': float(e.valor_esperado) if e.valor_esperado else None,
            'valor_obtido': float(e.valor_obtido) if e.valor_obtido else None,
            'linha': e.linha
        } for e in v1])
        
        # Validação 2: D/C Separados
        v2 = self.validar_debito_credito_separados()
        resultado['erros'].extend([{
            'tipo': e.tipo,
            'codigo_conta': e.codigo_conta,
            'descricao': e.descricao,
            'valor_esperado': float(e.valor_esperado) if e.valor_esperado else None,
            'valor_obtido': float(e.valor_obtido) if e.valor_obtido else None,
            'linha': e.linha
        } for e in v2])
        
        # Validação 3: Balanceamento
        v3 = self.validar_balanceamento_ativo_passivo()
        resultado['avisos'].extend([{
            'tipo': e.tipo,
            'codigo_conta': e.codigo_conta,
            'descricao': e.descricao,
            'valor_esperado': float(e.valor_esperado) if e.valor_esperado else None,
            'valor_obtido': float(e.valor_obtido) if e.valor_obtido else None,
            'linha': e.linha
        } for e in v3])
        
        # Validação 4: Sintéticas
        v4 = self.validar_contas_tipo_sintetica()
        resultado['avisos'].extend([{
            'tipo': e.tipo,
            'codigo_conta': e.codigo_conta,
            'descricao': e.descricao,
            'valor_esperado': float(e.valor_esperado) if e.valor_esperado else None,
            'valor_obtido': float(e.valor_obtido) if e.valor_obtido else None,
            'linha': e.linha
        } for e in v4])
        
        resultado['contas_validadas'] = len(self.df)
        resultado['resumo'] = {
            'total_erros': len(resultado['erros']),
            'total_avisos': len(resultado['avisos']),
            'status': 'OK' if len(resultado['erros']) == 0 else 'COM_ERROS'
        }
        
        return resultado
