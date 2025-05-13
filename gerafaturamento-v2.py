import pandas as pd
from sys import exit

# Lê as entradas
try:
    df = pd.read_csv("Clockify.csv")
    pool = pd.read_csv("pool_de_horas-v2.csv")
except FileNotFoundError:
    print("Erro: Arquivos Clockify.csv ou pool_de_horas.csv não encontrados.")
    exit()
    
try:
    pool_por_cliente = dict(zip(pool["Cliente"], pool["Pool"]))
    dias_por_cliente = dict(zip(pool["Cliente"], pool["Dias"]))
    horas_por_cliente = dict(zip(pool["Cliente"], pool["Horas"]))
except KeyError:
    print("Erro: Colunas 'Cliente', 'Dias' ou 'Horas' não encontradas no arquivo pool_de_horas.csv")
    exit()    
 
 
    
# Converte colunas de data e hora para datetime
try:
  df["datetime"] = pd.to_datetime(df["Data de início"] + " " + df["Hora de início"], format="%d/%m/%Y %H:%M", errors='coerce')
except KeyError:
    print("Erro: Colunas 'Data de início' ou 'Hora de início' não encontradas no arquivo Clockify.csv")
    exit()
except ValueError:
    print("Erro: Formato de data/hora incorreto no arquivo Clockify.csv. Verifique se as colunas 'Data de início' e 'Hora de início' estão no formato DD/MM/AAAA HH:MM.")
    exit()
df.dropna(subset=['datetime'], inplace=True) # Remove linhas com erro na conversão de data/hora

# Remove tarefas de monitoramento
df = df.drop(df[df["Tarefa"] == "Monitoramento"].index)

# Ordena por data e hora
df = df.sort_values(by=["datetime"])


# Itera por cliente
horas_a_faturar = []
for cliente in df["Cliente"].unique():
    df_cliente = df[df["Cliente"] == cliente].copy() # Cria uma cópia para evitar SettingWithCopyWarning

    # Calcula horas acumuladas
    df_cliente["Total de Horas"] = df_cliente["Duração (decimal)"].cumsum()

    # Define se fatura ou não
    df_cliente["Faturar"] = df_cliente["Total de Horas"] > pool_por_cliente[cliente]

    df_cliente.loc[df_cliente["Etiqueta"] == "Fora do Horário", "Faturar"] = True


    # Calcula horas a faturar
    faturar = df_cliente[df_cliente["Faturar"]].copy()
    faturar = faturar.assign(Horas_a_faturar=0)  # Cria a coluna "Horas_a_faturar"

    for i in faturar.index:
        total_anterior = df_cliente.loc[:i, "Duração (decimal)"].sum() - faturar.loc[i, "Duração (decimal)"]
        horas_a_faturar_calculadas = faturar.loc[i, "Duração (decimal)"] if total_anterior >= pool_por_cliente[cliente] else faturar.loc[i, "Total de Horas"] - pool_por_cliente[cliente]
        faturar = faturar.assign(Horas_a_faturar=lambda x: x['Horas_a_faturar'].mask(x.index == i, horas_a_faturar_calculadas))

    faturar = faturar.assign(Horas_a_faturar=lambda x: x['Horas_a_faturar'].mask(x["Etiqueta"] == "Fora do Horário", x["Duração (decimal)"]))

    # Sumariza horas -  Use o nome correto da coluna!
    soma_extra = faturar.loc[faturar["Etiqueta"] == "Fora do Horário", "Horas_a_faturar"].sum() # "Horas_a_faturar"
    h_extra = f"{int(soma_extra)}:{int((soma_extra * 60) % 60):02d}"

    soma_comercial = faturar.loc[faturar["Etiqueta"] == "Horário Comercial", "Horas_a_faturar"].sum() # "Horas_a_faturar"
    h_comercial = f"{int(soma_comercial)}:{int((soma_comercial * 60) % 60):02d}"

    soma_total = faturar["Horas_a_faturar"].sum() # "Horas_a_faturar"
    h_total = f"{int(soma_total)}:{int((soma_total * 60) % 60):02d}"

    horas_a_faturar.append([cliente, h_total, h_extra, h_comercial])


# Imprime resultados
df2 = pd.DataFrame(horas_a_faturar, columns=["Cliente", "Total de horas", "Fora de horário", "Horário Comercial"])
df2.to_string(buf='faturamento-geral.txt', header=True, index=True, encoding='utf-8')


# Salva arquivos CSV
for cliente in df["Cliente"].unique():
    df[df["Cliente"] == cliente].to_csv(f"{cliente}_faturamento.csv", index=None, sep=',', mode='w')