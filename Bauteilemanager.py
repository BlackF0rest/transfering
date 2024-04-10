import pandas as pd
import qrcode
import os
import asyncio
from nicegui import ui, App
from typing import Union
from PIL import Image, ImageDraw, ImageFont

#DONE Part name in image
#DONE Refilled scanner
#TODO auf INGO bestellen
#DONE Prompt to delete
#TODO Focus on Scanner field

class InventoryManager:

    """
    A class for managing an inventory of items with unique serial numbers, names, descriptions, 
    and availability statuses.
    """

    qr_width = 1000

    def __init__(self):
        """
        Initializes the InventoryManager with the inventory data from the Excel file 
        Bauteileschrank.xlsx.
        """
        self.running_data = pd.read_excel('Bauteileschrank.xlsx', sheet_name='Tabelle', dtype={'Available':bool})
        self.table = None

    def save_data(self):
        """
        Saves the current inventory data to an Excel file.
        """
        try:
            self.running_data.to_excel(excel_writer='Bauteileschrank.xlsx', sheet_name='Tabelle', index=False)
        except Exception as e:
            ui.notify('Error Saving File!', category='error')

    def read_data(self):
        """
        Reads the inventory data from an Excel file.

        :return: The inventory data.
        :rtype: pd.DataFrame
        """
        try:
            self.running_data = pd.read_excel('Bauteileschrank.xlsx', sheet_name='Tabelle', dtype={'Available':bool})
        except Exception as e:
            ui.notify('Error Loading File!', category='error')

    def gen_new_serial(self) -> int:
        """
        Generates a new serial number for the inventory.

        :return: The new serial number.
        :rtype: int
        """
        lastID = self.running_data['id'].max()
        return  lastID + 1

    def update_availability(self, input: Union[str, list[dict[str, int]]], setting:bool=False):
        """
        Updates the availability of an item or a list of items.

        :param input: The serial number or list of items.
        :type input: Union[str, List[Dict[str, int]]
        :param setting: The availability setting.
        :type setting: bool
        """
        if input!= None:
            if type(input) == str:
                self.running_data.loc[self.running_data['id']==int(input), 'Available'] = setting
            elif type(input) == list:
                for inp in input:
                    self.running_data.loc[self.running_data['id']==inp['id'], 'Available'] = setting
            self.save_data()
        self.update_data()
    
    def update_data(self):
        """
        Updates the data in the table.
        """
        self.read_data()
        self.table.update_rows(self.running_data.loc[:].to_dict('records'))
        self.table.update()
        ui.update()
        self.save_data()

    def add_row(self, name:str, descr=""):
        """
        Adds a new item to the inventory.

        :param name: The name of the item.
        :type name: str
        :param descr: The description of the item.
        :type descr: str
        """
        newSerial = self.gen_new_serial()
        self.running_data.loc[len(self.running_data)] = [newSerial, True, name, descr]
        self.save_data()
        self.update_data()

    async def delete_row(self, input: Union[str, list[dict[str, int]]]):
        """
        Deletes an item from the inventory.

        :param input: The serial number of the item.
        :type input: str
        """

        with ui.dialog() as dialog, ui.card():
            ui.label('Are you sure?')
            with ui.row():
                ui.button('Yes', on_click=lambda: dialog.submit(True))
                ui.button('No', on_click=lambda: dialog.submit(False))

        result = await dialog

        if result:
            try:
                for inp in input:
                    self.running_data = self.running_data[self.running_data['id']!=int(inp['id'])]
                self.save_data()
                self.update_data()
            except Exception as e:
                ui.notify('Error Deleting File!', category='error')

    def download_qr_codes(self, ids):
        """
        Downloads a QR code for each item with the given IDs.

        :param ids: The IDs of the items.
        :type ids: List[int]
        """
        for id in ids:
            filename = "barcodes/"+str(id['id'])+".png"
            if not os.path.exists(filename):
                img = qrcode.make(id['id'])
                img.save(filename)
                img = Image.open(filename)
                new_width = self.qr_width
                new_height = img.height
                new_img = Image.new(img.mode, (new_width,new_height))
                new_img.paste(img,(0,0))
                draw = ImageDraw.Draw(new_img)
                font = ImageFont.truetype('arial.ttf', 200)
                text = str(id["Name"])
                text_widht,text_height = draw.textsize(text,font=font)
                size_var = 10
                while text_widht >  new_width-(img.width+1):
                    font = ImageFont.truetype('arial.ttf', 200-size_var)
                    text_widht,text_height = draw.textsize(text,font=font)
                    size_var += 5
                x = img.width + 1
                y = img.height // 2 - text_height // 2
                rectangle = Image.new(img.mode,((self.qr_width-img.width),img.height), color='white')
                new_img.paste(rectangle,(img.width,0))
                draw.text((x,y), text, font=font, fill='black')
                new_img.save(filename)
            ui.download(filename)

    def run(self):
        """
        Starts the inventory management application.

        The application will run until it is manually stopped.
        """
        ui.run(port=80,title='CoTrack',dark=None)
        ui.open('/')

        #asyncio.create_task(asyncio.sleep(60,lambda: self.update_data))

inv = InventoryManager()

@ui.page('/')
def normal_view():
    """
    Displays the normal view of the inventory.
    """
    inv.table =  ui.table.from_pandas(inv.running_data).classes('w-full')
    inv.table.columns[1]['sortable'] = True
    inv.table.columns[0]['sortable'] = True
    with inv.table.add_slot('top-left'):
        inp = None
        inputRef = ui.input(placeholder='Scanner').bind_value(inv.table, 'filter').on('keydown.enter',lambda: (inv.update_availability(inputRef.value,False),inputRef.set_value(None)))
    with inv.table.add_slot('top-right'):
        with ui.link(target=editor_view):
            ui.button('Editor View')
    inv.table.set_fullscreen(True)
    inv.table.add_slot('body-cell-Available', '''
        <q-td key="Available" :props="props">
            <q-badge :color="props.value < true ? 'red' : 'green'">
                {{ props.value < true ? 'No' : 'Yes' }}
            </q-badge>
        </q-td>
        ''')

@ui.page('/editor')
def editor_view():
        """
        Displays the editor view of the inventory.
        """
        inv.table = ui.table.from_pandas(inv.running_data, selection='multiple').classes('w-full')
        inv.table.columns[1]['sortable'] = True
        inv.table.columns[0]['sortable'] = True
        with inv.table.add_slot('top-left'):
            inputRef = ui.input(placeholder='Search').props('type=search').bind_value(inv.table, 'filter').on('keydown.enter',lambda: (inv.update_availability(inputRef.value, True),inputRef.set_value(None)))
            with inputRef.add_slot("append"):
                ui.icon('search')
        with inv.table.add_slot('top-right'):
            ui.button('Refresh',on_click=lambda: inv.update_data())
            ui.button('QR-Code/s', on_click=lambda: inv.download_qr_codes(inv.table.selected)).bind_enabled_from(inv.table, 'selected', backward=lambda val: bool(val))
            ui.button('Refilled', on_click=lambda: inv.update_availability(inv.table.selected, True)).bind_enabled_from(inv.table, 'selected', backward=lambda val: bool(val))
            ui.button('Remove', on_click=lambda: (inv.delete_row(inv.table.selected))).bind_enabled_from(inv.table, 'selected', backward=lambda val: bool(val))
            with ui.link(target=normal_view):
                ui.button('Close View')

        with inv.table.add_slot('bottom'):
            with inv.table.row():
                with inv.table.cell():
                    ui.button(on_click=lambda: (
                        inv.add_row(new_name.value, new_descr.value),
                        new_name.set_value(None),
                        new_descr.set_value(None)
                    ), icon='add').props('flat fab-mini')
                with inv.table.cell():
                    new_name = ui.input('Name')
                with inv.table.cell():
                    new_descr = ui.input('Description')
        inv.table.set_fullscreen(True)
        inv.table.add_slot('body-cell-Available', '''
            <q-td key="Available" :props="props">
                <q-badge :color="props.value < true ? 'red' : 'green'">
                    {{ props.value < true ? 'No' : 'Yes' }}
                </q-badge>
            </q-td>
            ''')

inv.run()