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
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
import bisect
import jqdata
import datetime
import os

from data_loader import DataLoaderSingle
from data_loader import DataLoader
from file_operator import FileOperator
from data_analyzer import DataAnalyzer
from config import TODAY, YESTDAY, SDATE, EDATE
from config import DATES, FILEN, CODES


class Ploter(object):
    def __init__(self, dic, code, dates, date, fig_type, method='pee'):
        self.dic = dic
        self.code = code
        self.dates = dates
        self.date = date
        self.fig_type = fig_type
        self.method = method
        df=self.dic[self.code]
        self.df = df[df.index.isin(self.dates)]
    
    def get_fig_name(self):
        df = self.dic['info']
        return df[df['code']==self.code].display_name.iloc[0]
    
    def get_fig_cal_cur_val(self):
        return self.df.ix[self.date.date(),self.method.upper()]
    
    def get_fig_cal_price(self):
        cal_val = self.get_fig_cal_cur_val()
        cal_price = self.df['PRICE']*(cal_val/self.df[self.method.upper()])
        
        return cal_price
        
    def display_single(self, fig_data):
        plt.figure(figsize=(15,8))
        plt.title(fig_data['name']+fig_data['desc'])
        for d in fig_data['data']:
            #plt.plot(self.dates, d['data'], label=d['label'])
            plt.plot(d['data'].index, d['data'], label=d['label'])
        plt.legend()
        plt.grid(True)
        plt.show()



'''
fig_data={
         'name':'中证500',
         'desc':'中证500估值图',
         'data':[{'data':[], 'label':u'指数'},
                 {'data':[], 'label':u'指数'}]
 }
'''
class TdFigPloter(Ploter):
    def assemble_fig_data(self):
        data1 = {'data':self.df['PRICE'],
                 'label':u'指数'
                }
        data2 = {'data':self.get_fig_cal_price(),
                 'label':u'当前估值线'
                }
        fig_data={'name':self.get_fig_name(),
                  'desc':u'通道图',
                  'data':[data1,data2]
                 }
        return fig_data

    def display(self):
        fig_data = self.assemble_fig_data()
        self.display_single(fig_data)
    

    
class GzFigPloter(Ploter):
    def assemble_fig_data(self):
        data1 = {'data':self.df[self.method.upper()],
                 'label':self.method.upper()
                }
        data2 = {'data':pd.Series(self.get_fig_cal_cur_val(), index=self.df[self.method.upper()].index),
                 'label':u'当前'+self.method.upper()
                }
        fig_data={'name':self.get_fig_name(),
                  'desc':u'估值图',
                  'data':[data1,data2]
                 }
        return fig_data

    def display(self):
        fig_data = self.assemble_fig_data()
        self.display_single(fig_data)    


