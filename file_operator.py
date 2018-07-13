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

from data_loader import DataLoaderSingleCode
from config import TODAY, YESTDAY, SDATE, EDATE
from config import DATES, FILEN, CODES

class FileOperator(object):
    def __init__(self,fileN,dic={}):
        self.dic = dic
        self.fileN = fileN
    def save_file(self, dic):
        try:
            writer=pd.ExcelWriter(self.fileN)
            for code in dic:
                df=dic[code]
                df.to_excel(writer,code)
            writer.save()
            writer.close()
        except Exception as e:
            print("[save_file]:Save file failed!")
            print(e)

    def read_file(self):
        try:
            if not os.path.exists(self.fileN):
                return {}
            info=pd.read_excel(self.fileN,'info')
            dic={}
            for code in list(set(CODES+list(info.ix[:,'code']))):
                if code in info['code'].values:
                    dic[code]=pd.read_excel(self.fileN,code)
            dic['info'] = info
            return dic
        except FileNotFoundError:
            return {}

    def flush_file(self, dic, dates):
        # 获取要更新的日期
        for code in dic:
            if code != 'info':
                old_dates=dic[code].index
                break
        old_dates = [d.date() for d in old_dates]
        new_dates=pd.Series(list(set(dates)-set(old_dates))).sort_index(ascending=True)
        
        # 更新旧指数中的日期数据
        if not new_dates.empty:
            tmp={}
            for code in dic:
                if code != 'info':
                    dlsc = DataLoaderSingleCode(code, new_dates)
                    tmp[code] = dlsc.get_index_df()
                    dic[code] = dic[code].reindex(index=[d.date() for d in dic[code].index])
                    dic[code] = pd.concat([dic[code],tmp[code]]).sort_index(ascending=True)

        # 增加旧dic中的指数
        new_codes=set(CODES)-set(dic)
        info = {}
        display_name=[]
        codes = []
        start_date = []
        end_date = []
        if new_codes:
            for code in new_codes:
                if code != 'info':
                    dl = DataLoaderSingleCode(code, dates[:])
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
            info=pd.DataFrame(info)
            dic['info']=pd.concat([dic['info'],info],axis=0,ignore_index=True)
        return dic

