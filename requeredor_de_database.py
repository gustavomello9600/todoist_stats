from notion_client import Client
from pprint import pprint

notion = Client(auth="secret_Rvlf6qUOEuOaWx68sCpNKvdZ0e8ObgpzqXhcAthofWh")

track_record_do_todoist = notion.databases.list()['results'][1]
pprint(track_record_do_todoist)
