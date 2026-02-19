from threading import Lock


class Replicator:
    def __init__(self,master,children,logger=None):
        self.master = master
        self.children = children
        self.lock = Lock()
        self.executed = False
        self.log = logger or (lambda msg: None)
    
    def _log(self,msg):
        self.log(msg)
    def execute(self,trade_signal):
        with self.lock:
            if self.executed:
                self._log("trade already executed Ignoring..")
                return
            self._log("Executing in master first")
            
            for leg in trade_signal['legs']:
                self.master.place_order(leg['symbol'],leg['token'])
                
            self.log("Master done")
            for child in self.children:
                for leg in trade_signal['legs']:
                    child.place_order(leg['symbol'],leg['token'])
            
            self.executed = True
        
    def test(self,trade_signal):
        with self.lock:
            if self.executed:
                self._log("trade already executed Ignoring..")
                return
            self._log("Executing in master first")
            
            for leg in trade_signal['legs']:
                self._log(f"Placing order in master with args:{leg['symbol']},{leg['token']},{leg['B_S']},{leg['quantity']}")
                
            self._log("Master done")
            for child in self.children:
                for leg in trade_signal['legs']:
                    self._log(f"Placing order in Child with args:{leg['symbol']},{leg['token']}")
                    
            self.executed = True