#!/usr/bin/env python3
import json
import threading, traceback
import time

from nicegui import ui
from barcode import Code128

table = None

def automaticRefresh(delay):
    nextTime = time.time() + delay
    while True:
        time.sleep(max(0,nextTime-time.time()))
        try:
            updateAvailability()
        except Exception:
            traceback.print_exc()
        nextTime += (time.time()-nextTime)//delay*delay+delay

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

def updateAvailability(input=None, setting:bool=False):
    global table
    if input != None:
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
    table.update_rows(runningData['rows'])

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
    global table
    table = ui.table(columns=runningData['columns'], rows=runningData['rows'], selection='multiple').classes('w-full')
    with table.add_slot('top-left'):
        inputRef = ui.input(placeholder='Search').props('type=search').bind_value(table, 'filter').on('keydown.enter',lambda: (updateAvailability(inputRef.value, False),inputRef.set_value(None)))
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
    global table
    table =  ui.table(columns=runningData['columns'], rows=runningData['rows']).classes('w-full')
    with table.add_slot('top-left'):
        inp = None
        inputRef = ui.input(placeholder='Scanner').bind_value(table, 'filter').on('keydown.enter',lambda: (updateAvailability(inputRef.value, True),inputRef.set_value(None)))
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
    
#threading.Thread(target=lambda: automaticRefresh(30))

ui.run(port=80,title='CoTrack',dark=None)
editorView()