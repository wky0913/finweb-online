#########为聚宽的文件引用功能而运行的代码##############
import io, os, sys, types
from IPython import get_ipython
from nbformat import read
from IPython.core.interactiveshell import InteractiveShell


def find_notebook(fullname, path=None):
    """find a notebook, given its fully qualified name and an optional path

    This turns "foo.bar" into "foo/bar.ipynb"
    and tries turning "Foo_Bar" into "Foo Bar" if Foo_Bar
    does not exist.
    """
    name = fullname.rsplit('.', 1)[-1]
    if not path:
        path = ['']
    for d in path:
        nb_path = os.path.join(d, name + ".ipynb")
        if os.path.isfile(nb_path):
            return nb_path
        # let import Notebook_Name find "Notebook Name.ipynb"
        nb_path = nb_path.replace("_", " ")
        if os.path.isfile(nb_path):
            return nb_path


class NotebookLoader(object):
    """Module Loader for Jupyter Notebooks"""
    def __init__(self, path=None):
        self.shell = InteractiveShell.instance()
        self.path = path

    def load_module(self, fullname):
        """import a notebook as a module"""
        path = find_notebook(fullname, self.path)

        print ("importing Jupyter notebook from %s" % path)

        # load the notebook object
        with io.open(path, 'r', encoding='utf-8') as f:
            nb = read(f, 4)


        # create the module and add it to sys.modules
        # if name in sys.modules:
        #    return sys.modules[name]
        mod = types.ModuleType(fullname)
        mod.__file__ = path
        mod.__loader__ = self
        mod.__dict__['get_ipython'] = get_ipython
        sys.modules[fullname] = mod

        # extra work to ensure that magics that would affect the user_ns
        # actually affect the notebook module's ns
        save_user_ns = self.shell.user_ns
        self.shell.user_ns = mod.__dict__

        try:
            for cell in nb.cells:
                if cell.cell_type == 'code':
                    # transform the input to executable Python
                    code = self.shell.input_transformer_manager.transform_cell(cell.source)
                    # run the code in themodule
                    exec(code, mod.__dict__)
        finally:
            self.shell.user_ns = save_user_ns
        return mod

class NotebookFinder(object):
    """Module finder that locates Jupyter Notebooks"""
    def __init__(self):
        self.loaders = {}

    def find_module(self, fullname, path=None):
        nb_path = find_notebook(fullname, path)
        if not nb_path:
            return

        key = path
        if path:
            # lists aren't hashable
            key = os.path.sep.join(path)

        if key not in self.loaders:
            self.loaders[key] = NotebookLoader(path)
        return self.loaders[key]
sys.meta_path.append(NotebookFinder())
#########################################################


import numpy as np
import pandas as pd
import bisect
import jqdata
import datetime
import os

from config import TODAY, YESTDAY, SDATE, EDATE
from config import DATES, FILEN, CODES
from operator import mod

WORDS = ['price','pe','pb','pee','pbe','pem','pbm']

# 数据加载类：获取数据，初步整理
class DataLoaderSingle(object):
    def __init__(self,code,date):
        stocks=get_index_stocks(code, date)
        dfn=len(stocks)
        if dfn<=0:
            df=pd.DataFrame()
        q=query(
            valuation.market_cap,valuation.pe_ratio,
            valuation.pb_ratio,              
            ).filter(valuation.code.in_(stocks))
        df=get_fundamentals(q, date)
        df=df.fillna(0)
        
        self.stocks = get_index_stocks(code, date)
        self.df = df
        self.dfn = len(stocks)
        self.code = code
        self.date = date
        
    def get_pe(self):
        if self.df.empty:
            return float('NaN')
        sum_p=sum(self.df.market_cap)
        sum_e=sum(self.df.market_cap/self.df.pe_ratio)    
        if sum_e > 0:
            pe=sum_p / sum_e
        else:
            pe=float('NaN') 
        return pe

    def get_pb(self):
        if self.df.empty:
            return float('NaN')
        sum_p=sum(self.df.market_cap)
        sum_b=sum(self.df.market_cap/self.df.pb_ratio)
        pb=sum_p/sum_b
        return pb

    def get_pee(self):
        if self.df.empty:
            return float('NaN')
        pee=len(self.df)/sum([1/p if p>0 else 0 for p in self.df.pe_ratio])
        return pee

    def get_pbe(self):
        if self.df.empty:
            return float('NaN')
        pbe=len(self.df)/sum([1/b if b>0 else 0 for b in self.df.pb_ratio])
        return pbe

    def get_pem(self):
        if self.df.empty:
            return float('NaN')
    
        pes=list(self.df.pe_ratio);pes.sort()    
        if mod(self.dfn,2)==0:
            pem=0.5*sum(pes[round(self.dfn/2-1):round(self.dfn/2+1)])
        else:
            pem=pes[round((self.dfn-1)/2)]
        return pem

    def get_pbm(self):
        if self.df.empty:
            return float('NaN')

        pbs=list(self.df.pb_ratio);pbs.sort()
        if mod(self.dfn,2)==0:
            pbm=0.5*sum(pbs[round(self.dfn/2-1):round(self.dfn/2+1)])
        else:
            pbm=pbs[round((self.dfn-1)/2)]
        return pbm
    
    def get_index_price(self):
        price = get_price(self.code, end_date=self.date, count=1, frequency='1d', fields=['close'])
        return price.ix[0,'close']


class DataLoaderSingleCode(object):
    def __init__(self, code, dates):
        s_date = get_all_securities(['index']).ix[code].start_date
        self.code = code
        self.dates = dates[dates>s_date]

    def get_pes(self):
        tmp = []
        for date in self.dates:
            dls = DataLoaderSingle(self.code,date)
            tmp.append(dls.get_pe())
        return pd.Series(tmp, index=self.dates)

    def get_pbs(self):
        tmp = []
        for date in self.dates:
            dls = DataLoaderSingle(self.code,date)
            tmp.append(dls.get_pb())
        return pd.Series(tmp, index=self.dates)

    def get_pees(self):
        tmp = []
        for date in self.dates:
            dls = DataLoaderSingle(self.code,date)
            tmp.append(dls.get_pee())
        return pd.Series(tmp, index=self.dates)

    def get_pbes(self):
        tmp = []
        for date in self.dates:
            dls = DataLoaderSingle(self.code,date)
            tmp.append(dls.get_pbe())
        return pd.Series(tmp, index=self.dates)

    def get_pems(self):
        tmp = []
        for date in self.dates:
            dls = DataLoaderSingle(self.code,date)
            tmp.append(dls.get_pem())
        return pd.Series(tmp, index=self.dates)

    def get_pbms(self):
        tmp = []
        for date in self.dates:
            dls = DataLoaderSingle(self.code,date)
            tmp.append(dls.get_pbm())
        return pd.Series(tmp, index=self.dates)

    def get_index_df(self):
        pes,pbs,pees,pbes,pems,pbms,prices = [],[],[],[],[],[],[]
        for date in self.dates:
            dls = DataLoaderSingle(self.code,date)
            pes.append(dls.get_pe())
            pbs.append(dls.get_pb())
            pees.append(dls.get_pee())
            pbes.append(dls.get_pbe())
            pems.append(dls.get_pem())
            pbms.append(dls.get_pbm())
            prices.append(dls.get_index_price())
        df = pd.DataFrame(index=self.dates) 
        for word in WORDS:
            df[word.upper()]=eval(word+'s')
        return df

    
class DataLoader(object):
    def __init__(self, codes, dates):
        self.codes = codes
        self.dates = dates
    def get_index_dic(self):
        dic = {}
        info = {}
        display_name=[]
        codes = []
        start_date = []
        end_date = []
        for code in self.codes:
            dl = DataLoaderSingleCode(code, self.dates)
            dic[code] = dl.get_index_df()
            raw_info = get_security_info(code)
            codes.append(raw_info.code)
            display_name.append(raw_info.display_name)
            start_date.append(raw_info.start_date)
            end_date.append(raw_info.end_date)
        info['code'] = codes
        info['display_name'] = display_name
        info['start_date'] = start_date
        info['end_date'] = end_date
        dic['info'] = pd.DataFrame(info)
        return dic
