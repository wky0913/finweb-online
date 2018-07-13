# 为聚宽的文件引用功能而运行的代码##############
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


from data_loader import DataLoaderSingle
from data_loader import DataLoader
from config import TODAY, YESTDAY, SDATE, EDATE
from config import DATES, FILEN, CODES


#数据分析类：分析数据
#输入参数：
'''
输入参数：
1.dic：整体数据
2.code:要统计的指数
3.dates：分位差统计范围
4.date：分位差使用的估值日期
'''
class DataAnalyzerSingle(object):
    def __init__(self, dic, code, dates, date):
        df = dic[code]
        self.dates = dates
        self.df = df[df.index.isin(dates)]
        self.dls = DataLoaderSingle(code, date)
        
    def cal_single(self,df,word):
        val_q=list(df.quantile([ii/10 for ii in range(11)]))
        val_cur=eval('self.dls.get_'+word+'()')
        idx=bisect.bisect(val_q,val_cur)
        try:
            val_qt=10*(idx-(val_q[idx]-val_cur)/(val_q[idx]-val_q[idx-1]))
        except IndexError:
            val_qt=0
        return val_qt
    
    def get_pe_fwc(self):
        df = self.df.ix[self.dates,'PE'];
        return self.cal_single(df, 'pe')
    
    def get_pb_fwc(self):
        df = self.df.ix[self.dates,'PB'];
        return self.cal_single(df, 'pb')
    
    def get_pee_fwc(self):
        df = self.df.ix[self.dates,'PEE'];
        return self.cal_single(df, 'pee')
    
    def get_pbe_fwc(self):
        df = self.df.ix[self.dates,'PBE'];
        return self.cal_single(df, 'pbe')
    
    def get_pem_fwc(self):
        df = self.df.ix[self.dates,'PEM'];
        return self.cal_single(df, 'pem')
    
    def get_pbm_fwc(self):
        df = self.df.ix[self.dates,'PBM'];
        return self.cal_single(df, 'pbm')

    
class DataAnalyzer(object):
    def __init__(self, dic, codes, dates, date):
        self.dic = dic
        self.codes = codes
        self.dates = dates
        self.date = date

    def get_summary(self):
        columns=[u'名称',u'加权PE',u'分位点%',u'等权PE',u'分位点%',u'中位数PE',u'分位点%',
         u'加权PB',u'分位点%',u'等权PB',u'分位点%',u'中位数PB',u'分位点%']
        df_summary=pd.DataFrame(index=[code for code in self.codes],columns=columns)
        for code in self.codes:
            dls = DataLoaderSingle(code, self.date)
            pe = dls.get_pe()
            pb = dls.get_pb()
            pee = dls.get_pee()
            pbe = dls.get_pbe()
            pem = dls.get_pem()
            pbm = dls.get_pbm()
            
            das = DataAnalyzerSingle(self.dic, code, self.dates, self.date)
            pe_qt=das.get_pe_fwc()
            pb_qt=das.get_pb_fwc()
            pee_qt=das.get_pee_fwc()
            pbe_qt=das.get_pbe_fwc()
            pem_qt=das.get_pem_fwc()
            pbm_qt=das.get_pbm_fwc()
            
            all_index=get_all_securities(['index'])
            index_name=all_index.ix[code].display_name
            
            df_summary.ix[code]=[index_name,\
                '%.1f' % pe,'%.1f' % pe_qt,'%.1f' % pee,'%.1f' % pee_qt,\
                '%.1f' % pem,'%.1f' % pem_qt,'%.1f' % pb,'%.1f' % pb_qt,\
                '%.1f' % pbe,'%.1f' % pbe_qt,'%.1f' % pbm,'%.1f' % pbm_qt]
            
        return df_summary
