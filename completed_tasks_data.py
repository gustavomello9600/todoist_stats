import re
import pandas as pd
from todoist.api import TodoistAPI
from datetime import date, timedelta
from matplotlib import pyplot as plt

print("Esse script gera um gráfico com suas tarefas completadas por dia e coloridas\n"
      "de acordo com o projeto a que pertenciam em um dado período de interesse")

token = input("\nInsira seu token de acesso: ")

api = TodoistAPI("a24619b4c0cae7ad1c1bf43bf9bd81a0588fdd76" if len(token) == 0 else token)
api.sync()


month_number ={"jan": 1, "fev":  2, "mar":  3, "abr":  4,
                "mai": 5, "jun":  6, "jul":  7, "ago":  8,
                "set": 9, "out": 10, "nov": 11, "dez": 12}

def process(date):
    words = [s.strip() for s in date.split("de")]
    day, month, year = int(words[0]), month_number[words[1].lower()[:3]],\
                       "20" + words[2][-2:] if len(words) == 3 else "2020"
    return "{}-{}-{}T00:00".format(year, month, day)

since = process(input("> Desde a data: "))
until = process(input("> Até a data:   "))

relevant_tasks    = api.completed.get_all(since=since, until=until)["items"]
relevant_projects = api.completed.get_all(since=since, until=until)["projects"]

tasks_table = pd.DataFrame(relevant_tasks)

color_by_index = {
30:	"#b8255f", 40:	"#96c3eb",
31:	"#db4035", 41:	"#4073ff",
32:	"#ff9933", 42:	"#884dff",
33:	"#fad000", 43:	"#af38eb",
34:	"#afb83b", 44:	"#eb96eb",
35:	"#7ecc49", 45:	"#e05194",
36:	"#299438", 46:	"#ff8d85",
37:	"#6accbc", 47:	"#808080",
38:	"#158fad", 48:	"#b8b8b8",
39:	"#14aaf5", 49:	"#ccac93"}

dias_da_semana = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

projects_handler = api.state["projects"]
archive = api.projects.get_archived()

projects_data = list()
for project_handler in projects_handler:
    projects_data.append(project_handler.data)
for project in archive:
    projects_data.append(project)
projects_data = pd.DataFrame(projects_data)[["id", "name", "color"]]
projects_data.set_index("id", inplace=True)

tasks_table = \
tasks_table.assign(project_name  = lambda x: [projects_data["name"][pid] for pid in x.project_id],
                   project_color = lambda x: [color_by_index[int(projects_data["color"][pid])] for pid in x.project_id])
tasks_table = tasks_table[["completed_date", "content", "project_name", "project_color"]]
tasks_table["completed_date"] = pd.to_datetime(tasks_table["completed_date"])
tasks_table = tasks_table.assign(date_label=lambda x: ["{:02}".format(d.month)
                                                       + "/"
                                                       + "{:02d}".format(d.day)
                                                       + " - "
                                                       + dias_da_semana[d.weekday()].capitalize() + " "
                                                       for d in x.completed_date])

graph_data = tasks_table.groupby(["date_label", "project_name"])["content"].count().unstack(level=-1).fillna(0)

delta_days = pd.to_datetime(until) - pd.to_datetime(since)
days = [pd.to_datetime(since) + timedelta(days=i) for i in range(delta_days.days + 1)]
days = ["{:02}".format(d.month)
        + "/"
        + "{:02d}".format(d.day)
        + " - "
        + dias_da_semana[d.weekday()].capitalize() + " "
        for d in days]

for day in days:
    if day not in graph_data.index:
        graph_data.loc[day] = 0

graph_data.sort_index(inplace=True)
graph_data = graph_data.astype("int32")

fig, ax = plt.subplots()
fig.patch.set_facecolor("#282828")
ax.set_facecolor("#282828")
ax.tick_params(axis=u'both', which=u'both',length=0)
ax.tick_params(axis='x', colors='#A5A5A5')
plt.box(False)

y = range(1, len(days) + 1)
cum_sum = graph_data.T.cumsum().T
projects_color = projects_data.set_index("name")
first = True
for i, project in enumerate(graph_data.columns):
    color = color_by_index[projects_color.loc[project]["color"]]
    if first:
        plt.barh(y, graph_data[project], color=color)
        first = False
    else:
        plt.barh(y, graph_data[project], color=color, left=cum_sum.iloc[:, i-1])
plt.yticks(y, days, color="#A5A5A5", fontfamily="monospace")
xmax = max(*[sum(row[1]) for row in graph_data.iterrows()])
plt.xticks([int(x) for x in range(xmax + 1)])
plt.grid(axis="x", color="#505050", linestyle="--")
plt.tight_layout()
l = plt.legend(graph_data.columns, frameon=False)
for text in l.get_texts():
    plt.setp(text, color = '#A5A5A5')

plt.savefig("Relatório_Todoist_{}|{}.png".format(since[:-6], until[:-6]), transparent=True)