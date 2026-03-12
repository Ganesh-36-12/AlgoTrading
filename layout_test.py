from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.coordinate import Coordinate
from textual.binding import Binding
from textual.containers import Vertical,Horizontal,Container
from textual.widgets import  DataTable, Static, Button, Footer, RadioButton, Input, SelectionList, Select, RichLog
# from textual.reactive import reactive

import os

from core.options_main import OptionTrader
from core.TradeReplicator import Replicator
from utils.auth_helper import authenticate_all_sequential

accounts_dir = "accounts"

class SelectionScreen(Screen):
    """
    Ask user to select the main and child accounts
    
    returns: tuple of (main account, [child accounts,])
    
    """
    CSS_PATH = "layout.tcss"
    def compose(self) -> ComposeResult:
        with Container(id="center_region"):
            with Vertical(id="main_cont"):
                yield (Static("Select master",classes="title"))
                self.master_list = SelectionList(id='master_list')
                yield self.master_list
                self.master_confirm = Button("Confirm master",id="master_confirm")
                yield self.master_confirm
        yield Footer()
    
    def on_mount(self):
        self.files = [f for f in os.listdir(accounts_dir) if f.endswith(".env")]
        for i in self.files:
            self.master_list.add_option((i,i))
        
    async def show_children(self):
        self.main_cont = self.query_one("#main_cont")
        self.main_cont.mount(Static("Select child accounts",classes="title"))
        self.child_list = SelectionList(id="child_list")
        for i in self.files:
            if i != self.master:
                self.child_list.add_option((i,i))
        await self.main_cont.mount(self.child_list)
        
        self.child_confirm = Button("Confirm child",id="child_confirm")
        await self.main_cont.mount(self.child_confirm)

    async def confirm_master(self):
        master_selected = self.master_list.selected
        if len(master_selected) != 1:
            self.notify("Select one master account")
            return 
        self.master = master_selected[0]
        await self.query_one("#main_cont",Vertical).remove_children()
        await self.show_children()

    async def on_button_pressed(self,event: Button.Pressed):
        if event.button.id == "master_confirm":
            await self.master_confirm.remove()
            await self.confirm_master()
        if event.button.id == "child_confirm":
            await self.child_confirm.remove()
            self.children_list = self.child_list.selected
            self.app.selected_tuple = (self.master,*self.children_list)
            self.app.switch_screen(AuthScreen())
            

class AuthScreen(Screen):
    """
    from the tuples it will authenticate the users
    """
    CSS = """
    #log {
        height: 20;
        border: green;
        margin-bottom: 1;
    }
    """
    def compose(self):
        with Vertical(id="right-info"):
            yield Static("Status", id="status-title")
            self.status = RichLog(id="log", highlight=True,markup=True,wrap=False)
            yield self.status
            yield RadioButton("SELL",id="confirm_sell",value=self.app.enable_sell)
            
        yield Button("Next stage",id="next",disabled=True)
        yield Footer()
    
    def on_mount(self) -> None:
    # ... create trader objects first ...
        self.master_trader = OptionTrader(f"accounts/{self.app.selected_tuple[0]}")
        self.child_traders = []
        
        for i in self.app.selected_tuple[1:]:
            child_trader = OptionTrader(f"accounts/{i}")
            self.child_traders.append(child_trader)
        def _on_status(msg: str):
            # marshal to UI thread
            self.app.call_from_thread(lambda: self.status.write(msg))
        def _on_result(trader, ok, err):
            def apply():
                if ok:
                    self.status.write(f"[green]{trader.CLIENT} auth OK[/]")
                else:
                    self.status.write(f"[red]{trader.CLIENT} auth FAIL[/]: {err}")
            self.app.call_from_thread(apply)
        def _run_auth():
            successes, failures = authenticate_all_sequential(self.master_trader, self.child_traders, _on_status, _on_result)
            for tr in successes:
                self.status.write(f"success list entries: {tr.name, tr.get_fund_details()}")
            self.query_one("#next").disabled = False
            self.app.trader_obj = successes

        self.run_worker(_run_auth, thread=True, exclusive=True)
        
    async def on_button_pressed(self,event: Button.Pressed):
        if event.button.id == "next":
            self.app.switch_screen(TraderApp())
            
            
    def on_radio_button_changed(self, event: RadioButton.Changed) -> None:
            self.app.enable_sell = event.radio_button.value


class TraderApp(Screen):
    CSS_PATH = "styles.tcss"
    
    BINDINGS = [
        Binding("s", "sell", "SELL item", show=True),
        Binding("b", "buy", "BUY item", show=True)
        
    ]

    def compose(self) -> ComposeResult:
        # Row 1
        with Horizontal(id="top"):
            with Vertical(id="left-info"):
                self.account_table = DataTable(id="account-table")
                yield self.account_table
                
            with Vertical(id="right-info"):
                self.status = RichLog(id="log", highlight=True,markup=True,wrap=False)
                self.status.border_title = "Status"
                yield self.status
                
            with Vertical(name="signals",id="replicator-info"):
                yield RadioButton("SELL",id="sell_status",value=self.app.enable_sell)
                yield RadioButton("BUY",id='buy_status')

        # with Horizontal:
        with Vertical(id="middle"):
            self.expiry_select =  Select(id="expiry_dropdown",allow_blank=True,options=[])
            yield self.expiry_select
            self.price_table = DataTable(id="price_table")
            self.price_table.cursor_type = "cell"
            yield self.price_table

        with Horizontal(id="bottom"):
            self.preview_input = Input(placeholder="Enter spot number:",id="preview_cmd")
            yield self.preview_input
            yield Button("Place", id="btn-place", variant="success")
            yield Button("Quit", id="btn-quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        self.column_map = self.account_table.add_columns("Name","funds")
        

        for t in self.app.trader_obj:
            cash = float(t.get_fund_details())
            name =  max(t.name.split(), key=lambda s: len(s))
            self.row_map = self.account_table.add_row(name,f"{cash:.2f}",key=t.name) 
        
        self.trader = self.app.trader_obj[0]
        self.replicator = Replicator(
            master=self.trader,
            children=self.app.trader_obj[1:],
            logger=lambda msg: self.app.call_from_thread(self.status.write,msg))
        
        expiry_options = [(x,x) for x in self.trader.expiry_list]
        self.expiry_select.set_options(expiry_options)
        
        self.trader.trade_taken = not self.app.enable_sell
        self.trader.on_status = lambda text: self.app.call_from_thread(self._ui_status, text)
        self.trader.on_tokens_changed = lambda atm, ce, pe: self.app.call_from_thread(self._ui_tokens_changed, atm, ce, pe)
        self.trader.on_preview = lambda spot, preview_ce, preview_pe, preview_diff: self.app.call_from_thread(self._ui_preview, spot,preview_ce,preview_pe,preview_diff)
        self.trader.on_table = lambda rows: self.app.call_from_thread(self._ui_ladder,rows)
        self.trader.on_trade_signal = self._on_trade_signal

        self.price_table.add_columns("current_atm","CE","PE","DIFF")
        self.price_table.zebra_stripes = True

        self.price_table.add_row('-','-','-','-',key="preview")
        self.ladder_keys = []

        self.run_worker(self.trader.start_connection, thread=True, exclusive=True)

    # ---------- UI update handlers ----------
    def _ui_status(self, text: str):
        self.status.write(text)

    def _ui_tokens_changed(self, atm: int, ce_token: str, pe_token: str):
        self.atm, self.ce_token, self.pe_token = atm, ce_token, pe_token
        try:
            ce_symbol = self.trader.symbol_token_map.inv[str(ce_token)]
            pe_symbol = self.trader.symbol_token_map.inv[str(pe_token)]

            self.status.write(f"[blue]ATM[/] changed {atm}")
        except Exception as e:
            self.status.write(f"[red]UI token update failed: {e!r}[/]")
                
    def _ui_preview(self, atm: int, ce_ltp: float, pe_ltp: float, diff: float):
        try:
            new_row_data = (f"{atm}",f"{ce_ltp:.2f}",f"{pe_ltp:.2f}",f"{diff:.2f}")
            column_keys = list(self.price_table.columns.keys())
            
            for col_key, new_value in zip(column_keys, new_row_data):
                self.price_table.update_cell("preview", col_key, new_value,update_width=True)
        except Exception as e:
            self.status.write(f"[red]UI diff update failed: {e!r}[/]")            

    def _ui_ladder(self,rows):
        try:
            table = self.price_table
            cursor = table.cursor_coordinate
            new_keys = []
            for strike ,ce,pe,diff in rows:
                key = f"ladder_{strike}"
                new_keys.append(key)
                values = (f"{strike}",f"{ce:.2f}",f"{pe:.2f}",f"{diff:.2f}")
                
                if key in table.rows:
                    if self.atm == key.split("_")[1]:
                        values = [Text(v, style="bold #186ac7") for v in values]
                    for col,val in zip(table.columns.keys(),values):
                        table.update_cell(key,col,val)
                else:
                    if strike == self.atm:
                        styled = [Text(v, style="bold #186ac7") for v in values]
                        table.add_row(*styled,key=key)
                    else:
                        table.add_row(*values,key=key)
            for old in list(self.ladder_keys):
                if old not in new_keys and old in table.rows:
                    table.remove_row(old)
                self.ladder_keys = new_keys
            if cursor.row < table.row_count:
                table.cursor_coordinate = cursor
                
        except Exception as e:
            self.status.write(f"[red] Ladder update failed: {e!r}[/]")

    def _on_trade_signal(self, signal: dict):
        if self.app.enable_sell:
            if self.trader.trade_taken:
                self._ui_status(f"[yellow]Trade signal[/]: Trade already taken")
            else:
                self.run_worker(lambda: self.replicator.test(signal),thread=True)
                self.trader.trade_taken = True
        else:
            self._ui_status(f"[red]Trade signal[/]: Selling disabled")
        # Optional: auto-place orders here

    def get_spot_tokens(self,cell_coordinate : Coordinate):
        coordinate = Coordinate(cell_coordinate.row,0)
        spot_value = self.price_table.get_cell_at(coordinate)
        ce, pe = self.trader.get_ce_pe_tokens(spot_value)
        if cell_coordinate.column == 0:
            return (ce,pe)
        elif cell_coordinate.column == 1:
            return (ce,)
        elif cell_coordinate.column == 2:
            return (pe,)
        
    def action_sell(self) -> None:
        self.status.write(f"tokens: {self.trader.range_tokens}")
        self.status.write(f"strikes: {self.trader.ranged_strikes}")
        
        
        coord = self.price_table.cursor_coordinate
        if coord:
            tokens = self.get_spot_tokens(coord)
            signal = self.trader.build_trade_signal([*tokens],"SELL")
            self._on_trade_signal(signal)

    def action_buy(self) -> None:
        coord = self.price_table.cursor_coordinate
        if coord:
            tokens = self.get_spot_tokens(coord)
            signal = self.trader.build_trade_signal([*tokens],"BUY")
            self._on_trade_signal(signal)

    # ---------- Input & buttons ----------
    async def on_input_submitted(self, event: Input.Submitted):
        await self._handle_command((event.value or "").strip().lower())

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-place":
            await self._handle_command("place")
        elif event.button.id == "btn-quit":
            await self._handle_command("quit")
    
    def on_radio_button_changed(self, event: RadioButton.Changed) -> None:
        if event.radio_button.id == "sell_status":
            self.app.enable_sell = event.radio_button.value
            if event.radio_button.value == False :
                self.trader.trade_taken = True
                self.status.write(f"[red]selling stopped currently[/]")
            else:
                self.trader.trade_taken = False
                self.replicator.executed = False
                self.status.write(f"[green]selling started currently[/]")
                
    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        self.trader.expiry = str(event.value)
        self.trader.subscribe_strike_range(self.trader.current_atm)

    
    async def _handle_command(self, cmd: str):
        if cmd == "place":
            signal = self.trader.build_trade_signal([],"BUY")
            self._on_trade_signal(signal)
            self.preview_input.value = ""
        elif cmd == "quit":
            await self.action_quit()
        elif cmd.isdigit() and len(cmd) == 5:
            self.trader.preview(int(cmd))
            self.preview_input.value = ""
        else:
            self._ui_status(f"[red]Unknown command[/]: {cmd}")
            self.preview_input.value = ""

    # ---------- Shutdown ----------
    async def on_shutdown_request(self) -> None:
        self.trader.stop()

    async def action_quit(self) -> None:
        self.trader.stop()
        self.app.exit()


class Final(App):
    selected_tuple = None
    trader_obj = []
    enable_sell = True
    def on_mount(self):
        self.push_screen(SelectionScreen())

if __name__ == "__main__":
    Final().run()

