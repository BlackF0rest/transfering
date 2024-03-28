#!/usr/bin/env python3
import json

from nicegui import ui
from barcode.writer import ImageWriter
from barcode import Code128

def saveData(saveData:dict)->bool:
    try:
        with open('data.json', 'w') as saveFile:
            json.dump(saveData, saveFile)
        ui.notify('Saved')
    except Exception as e:
        ui.notify('Error Saving File!', category='error')
        return False
    return True

def readData()->dict:
    try:
        with open('data.json', 'r') as loadFile:
            data = json.load(loadFile)
        return data
    except Exception as e:
        ui.notify('Error Loading File!', category='error')

def genNewSerial()->int:
    lastID = max(item["id"] for item in runningData["rows"])
    return  lastID + 1

def updateAvailability(input, tableRef, setting:bool):
    if type(input) == str:
        for row in runningData["rows"]:
            if row["id"] == int(input):
                row["flagged"] = setting
            else:
                pass
    elif type(input) == list:

        for inp in input:
            for row in runningData["rows"]:
                if row["id"] == int(inp['id']):
                    row["flagged"] = setting
                else:
                    pass
    saveData(runningData)
    tableRef.update_rows(runningData['rows'])

def genBarcode(serialNum):
    print(serialNum)
    code = Code128(str(serialNum))
    outputFile = 'barcodes/' + str(serialNum)
    code.save(str(outputFile))
    ui.download(outputFile+".svg")

def addRow(name, descr,table):
    newSerial = genNewSerial()
    table.add_rows({'id': newSerial, 'name': name, 'descr': descr, 'flagged' : False})
    genBarcode(newSerial)

runningData = readData()

@ui.page("/editor")
def editorView():
    with ui.table(columns=runningData['columns'], rows=runningData['rows'], selection='multiple').classes('w-full') as table:
        with table.add_slot('top-left'):
            inputRef = ui.input(placeholder='Search').props('type=search').bind_value(table, 'filter').on('keydown.enter',lambda: (updateAvailability(inputRef.value, table, False),inputRef.set_value(None)))
            with inputRef.add_slot("append"):
                ui.icon('search')
        with table.add_slot('top-right'):
            ui.button('Refilled', on_click=lambda: updateAvailability(table.selected, table, False)).bind_enabled_from(table, 'selected', backward=lambda val: bool(val))
            ui.button('Remove', on_click=lambda: (table.remove_rows(*table.selected),saveData(runningData))).bind_enabled_from(table, 'selected', backward=lambda val: bool(val))
            with ui.link(target=normalView):
                ui.button('Close View')

        with table.add_slot('bottom'):
            with table.row():
                with table.cell():
                    ui.button(on_click=lambda: (
                        addRow(new_name.value, new_descr.value, table),
                        new_name.set_value(None),
                        new_descr.set_value(None),
                        saveData(runningData)
                    ), icon='add').props('flat fab-mini')
                with table.cell():
                    new_name = ui.input('Name')
                with table.cell():
                    new_descr = ui.input('Description')
        table.set_fullscreen(True)
        table.add_slot('body-cell-flag', '''
            <q-td key="flagged" :props="props">
                <q-badge :color="props.value < true ? 'green' : 'red'">
                </q-badge>
            </q-td>
            ''')
        
@ui.page('/')
def normalView():
    with ui.table(columns=runningData['columns'], rows=runningData['rows']).classes('w-full') as table:
        with table.add_slot('top-left'):
            inp = None
            inputRef = ui.input(placeholder='Scanner').bind_value(table, 'filter').on('keydown.enter',lambda: (updateAvailability(inputRef.value, table, True),inputRef.set_value(None))) #.on('keydown.enter', lambda v: (updateAvailability(v.value, table, True), inputRef.set_value(None),inputRef.update(), ui.notify("Scanned")) if v.value != None and len(v.value)==8 else (inputRef.update()))
        with table.add_slot('top-right'):
            with ui.link(target=editorView):
                ui.button('Editor View')
        table.set_fullscreen(True)
        table.add_slot('body-cell-flag', '''
            <q-td key="flagged" :props="props">
                <q-badge :color="props.value < true ? 'green' : 'red'">
                </q-badge>
            </q-td>
            ''')

ui.run(port=80,title='CoTrack',dark=None)
editorView()