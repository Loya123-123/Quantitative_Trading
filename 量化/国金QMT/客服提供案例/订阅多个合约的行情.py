from xtquant import xtdata

def on_data (datas):
    print(datas)

seq = xtdata.subscribe_whole_quote(code_list=['SA505.ZF'], callback=on_data)

xtdata.run()