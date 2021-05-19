from random import choice

import pandas as pd

from notion.client import NotionClient
from notion.collection import Collection, NotionDate, TableView
from notion.block import CollectionViewBlock
from matplotlib import pyplot as plt
from todoist.api import TodoistAPI
from datetime import timedelta
from uuid import uuid4

#Autenticação no Notion
client = NotionClient(token_v2="4abee418c178fa57d1f5d1fde8ab313a28b0859921c74f74874709258f863b0a846dbccfdbb717"
                               "121f9d5282e0fe93b28590dc37bcf28c98d3d937c23db1a27a475624d2e4bd0754dc5b1e263cb7")

# Constantes e Dicionários
month_number = {"jan": 1, "fev": 2, "mar": 3, "abr": 4,
                "mai": 5, "jun": 6, "jul": 7, "ago": 8,
                "set": 9, "out": 10, "nov": 11, "dez": 12}

dias_da_semana = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

color_by_index = {
    30: "#b8255f", 40: "#96c3eb",
    31: "#db4035", 41: "#4073ff",
    32: "#ff9933", 42: "#884dff",
    33: "#fad000", 43: "#af38eb",
    34: "#afb83b", 44: "#eb96eb",
    35: "#7ecc49", 45: "#e05194",
    36: "#299438", 46: "#ff8d85",
    37: "#6accbc", 47: "#808080",
    38: "#158fad", 48: "#b8b8b8",
    39: "#14aaf5", 49: "#ccac93"}

print("Esse script gera um gráfico com suas tarefas completadas por dia e coloridas\n"
      "de acordo com o projeto a que pertenciam em um dado período de interesse")

# Recebe token do usuário
token = input("\nInsira seu token de acesso: ")

# Autentica e sincroniza os dados do Todoist
api = TodoistAPI("a24619b4c0cae7ad1c1bf43bf9bd81a0588fdd76" if len(token) == 0 else token)
api.sync()


# Ensina o Python a processar as datas
def process(date):
    words = [s.strip() for s in date.split("de")]
    day, month, year = int(words[0]), month_number[words[1].lower()[:3]], \
                       "20" + words[2][-2:] if len(words) == 3 else "2020"
    return "{}-{}-{}T00:00".format(year, month, day)


# Recebe e processa o intervalo desejado
since = process(input("> Desde a data: "))
until = process(input("> Até a data  : "))[:-5] + "23:59"

# Recupera as tarefas completadas no período de interesse
relevant_tasks = api.completed.get_all(since=since, until=until)["items"]

# Recupera informações sobre os projetos aos quais essas tarefas pertenciam
relevant_projects = api.completed.get_all(since=since, until=until)["projects"]

# Cria uma tabela com os dados das tarefas
tasks_table = pd.DataFrame(relevant_tasks)

# Recupera uma lista de objetos que lidam cada um com os projetos atualmente em curso
projects_handler = api.state["projects"]

# TODO Mostrar tarefas de projetos já acabados também
archive = api.projects.get_archived()

# Cria e povoa uma lista com os dados de cada projeto
projects_data = list()
for project_handler in projects_handler:
    projects_data.append(project_handler.data)

# Adiciona também os dados de projetos arquivados
for project in archive:
    projects_data.append(project)

# Filtra as informações relevantes de cada projeto
projects_data = pd.DataFrame(projects_data)[["id", "name", "color"]]

# Determina o id do projeto como seu índice na tabela
projects_data.set_index("id", inplace=True)

# Adiciona os dados do projeto de cada tarefa da tabela de tarefas
tasks_table = \
    tasks_table.assign(project_name=lambda x: [projects_data["name"][pid] for pid in x.project_id],
                       project_color=lambda x: [color_by_index[int(projects_data["color"][pid])]
                                                for pid in x.project_id])

# Filtra e reorganiza a tabela
tasks_table = tasks_table[["task_id", "completed_date", "content", "project_name", "project_color"]]

# Transforma o tipo de dados da coluna para o formato de data
tasks_table["completed_date"] = pd.to_datetime(tasks_table["completed_date"])
print(tasks_table["completed_date"])

# Ensina o Python a criar etiquetas identificadoras do dia
def make_label(dat):
    return ("{:02}".format(dat.month)
            + "/"
            + "{:02d}".format(dat.day)
            + " - "
            + dias_da_semana[dat.weekday()].capitalize() + " ")

# Ensina o Python a inverter a ordem com que o mês e o dia aparecem na etiqueta
def swap_dm(s):
    return s[3:5] + "/" + s[:2] + s[5:]

# Cria as etiquetas identificadoras do dia para cada data
tasks_table = tasks_table.assign(date_label=lambda x: [make_label(d) for d in x.completed_date])

# Cria a tabela que será usada para formar o gráfico
graph_data = tasks_table.groupby(["date_label", "project_name"])["content"].count().unstack(level=-1).fillna(0)

# Cria a lista de dias do período no formato de etiquetas identificadoras
delta_days = pd.to_datetime(until) - pd.to_datetime(since)
days = [pd.to_datetime(since) + timedelta(days=i) for i in range(delta_days.days + 1)]
days = [make_label(d) for d in days]

# Adiciona as linhas dos dias em que nenhuma tarefa foi completada
for day in days:
    if day not in graph_data.index:
        graph_data.loc[day] = 0

# Põe as datas em ordem cronológica
graph_data.sort_index(inplace=True)

# Transforma os dados em números inteiros
graph_data = graph_data.astype("int32")

# Inicia os objetos gráficos
fig, ax = plt.subplots()

# Define a cor do fundo da imagem e do gráfico
fig.patch.set_facecolor("#282828")
ax.set_facecolor("#282828")

# Remove os tracinhos dos eixos
ax.tick_params(axis=u'both', which=u'both', length=0)
ax.tick_params(axis='x', colors='#A5A5A5')

# Remove a grade do gráfico
plt.box(False)

# Dá as posições de cada dia no eixo y
y = range(1, len(days) + 1)

# Dá a soma cumulativa dos dados para cada barra, útil para empilhá-los horizontalmente
cum_sum = graph_data.T.cumsum().T

# Retorna uma tabela a ser usada como dicionário
projects_color = projects_data.set_index("name")

# Delimita que estamos trabalhando com o primeiro elemento
first = True

# Para cada índice e projeto dentro dos dados do gráfico
for i, project in enumerate(graph_data.columns):

    # Recupera a cor do projeto
    color = color_by_index[projects_color.loc[project]["color"]]

    # Se for o primeiro, começa a barra no gráfico
    if first:
        plt.barh(y, graph_data[project], height=0.3, color=color)
        first = False

    # Introduz, à direita, os subsequentes
    else:
        plt.barh(y, graph_data[project], height=0.3, color=color, left=cum_sum.iloc[:, i - 1])

# Muda a fonte do eixo y para deixá-la com espaçamento regular e dá o devido nome a cada dia
plt.yticks(y, [swap_dm(d) for d in days], color="#A5A5A5", fontfamily="monospace")

# Determina o maior valor de x
xmax = max(*[sum(row[1]) for row in graph_data.iterrows()])

# Transforma os índices no eixo x em números inteiros
plt.xticks([int(x) for x in range(xmax + 1)])

# Cria linhas de grade tracejadas paralelas ao eixo y
plt.grid(axis="x", color="#505050", linestyle="--")

# Força tudo a caber na tela
plt.tight_layout()

# Exclui o fundo diferente da legenda
leg = plt.legend(graph_data.columns, frameon=False)

# Muda a cor do texto da legenda
for text in leg.get_texts():
    plt.setp(text, color='#A5A5A5')

# Traça a linha das metas
plt.axvline(x=5, c="grey")

# Salva o gráfico num arquivo png de fundo transparente
plt.savefig("Relatório_Todoist_{}|{}.png".format(since[:-6], until[:-6]), transparent=True)

print("Gráfico gerado e salvo na pasta raiz")

## RELATÓRIO NO NOTION

# Abre a página de integração com o Todoist
page = client.get_block("https://www.notion.so/Track-Record-do-Todoist-0e2d8455260d45d29418ba44dd88936d")

# Abre o histórico de tarefas
task_history = page.children[0]

# Atualiza a lista de projetos
color_options = ["red", "green", "pink", "orange", "yellow", "purple", "blue", "default", "gray", "brown"]

schema = task_history.collection.get("schema")
options_list = [op["value"] for op in schema["}%J^"]["options"]]
project_name_list = list(pd.unique(tasks_table["project_name"]))
new_options = [pn for pn in project_name_list if pn not in options_list]

if len(new_options) > 0:
    updated_schema = schema
    for option in new_options:
        updated_schema["}%J^"]["options"].append(
            {"id": str(uuid4()), "color": choice(color_options), "value": option})
        task_history.collection.set("schema", updated_schema)

reported_tasks_id = [row.unico for row in task_history.collection.get_rows()]

# Adiciona linhas de acordo com as tarefas completadas
for i, task in tasks_table.iterrows():
    if task["task_id"] in reported_tasks_id: continue
    row               = task_history.collection.add_row()
    row.nome          = task["content"]
    row.projeto       = task["project_name"]
    row.completada_em = NotionDate(task["completed_date"])
    row.unico = task["task_id"]

# Adiciona uma linha em branco ao final
row = task_history.collection.add_row()

print("Notion atualizado")
