from threading import Lock


class Replicator:
    def __init__(self,master,children):
        self.master = master
        self.children = children
        self.lock = Lock()
        self.executed = False
        
    def execute(self,trade_signal):
        with self.lock:
            if self.executed:
                print("trade already executed Ignoring..")
                return
            print("Executing in master first")
            
            for leg in trade_signal['legs']:
                self.master.place_sell_order(leg['symbol'],leg['token'])
                
            print("Master done")
            for child in self.children:
                for leg in trade_signal['legs']:
                    child.place_sell_order(leg['symbol'],leg['token'])
            
            self.executed = True
        
    def test(self,trade_signal):
        with self.lock:
            if self.executed:
                print("trade already executed Ignoring..")
                return
            print("Executing in master first")
            
            for leg in trade_signal['legs']:
                print("Placing order in master with args:",leg['symbol'],leg['token'])
                
            print("Master done")
            for child in self.children:
                for leg in trade_signal['legs']:
                    print("Placing order in child with args:",leg['symbol'],leg['token'])

            
            self.executed = True