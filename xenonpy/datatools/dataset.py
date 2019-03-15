#  Copyright (c) 2019. TsumiNa. All rights reserved.
#  Use of this source code is governed by a BSD-style
#  license that can be found in the LICENSE file.


import glob
import re
from collections import defaultdict
from pathlib import Path
from warnings import warn

import pandas as pd
import requests
from sklearn.externals import joblib


class Dataset(object):
    __extension__ = dict(
        dataframe=('pkl.pd_', pd.read_pickle),
        csv=('csv', pd.read_csv),
        excel=('xlsx', pd.read_excel),
        pickle=('pkl.z_', joblib.load)
    )

    __re__ = re.compile(r'[\s\-.]')

    def __init__(self, *paths, backend='dataframe'):
        self._backend = backend
        self._files = None
        self._paths = paths

        self.make_index()

    def make_index(self):
        def _make_index(path_):
            patten = self.__extension__[self._backend][0]
            files = glob.glob(path_ + '/*.' + patten)

            def _nest(_f):
                f_ = _f
                return lambda s: s.__extension__[s._backend][1](f_)

            for f in files:
                # select data
                f = Path(f).absolute()
                parent = str(f.parent).split('/')[-1]
                fn = f.name[:-(1 + len(patten))]
                fn = self.__re__.sub('_', fn)
                fn = '_'.join([parent, fn])

                if fn in self._files:
                    warn("file %s with name %s already bind to %s and will be ignored" %
                         (str(f), fn, self._files[fn]), RuntimeWarning)
                else:
                    self._files[fn] = str(f)
                    setattr(self.__class__, fn, property(_nest(str(f))))

        self._files = defaultdict(str)
        for path in self._paths:
            _make_index(path)

    @classmethod
    def from_http(cls, url, save_to, *, filename=None, chunk_size=256 * 1024, params=None,
                  **kwargs):
        """
        Get file object via a http request.

        Parameters
        ----------
        url: str
            The resource url.
        save_to: str
            The path of a dir to save the downloaded object into it.
        filename: str, optional
            Specific the file name when saving.
            Set to ``None`` (default) to use a inferred name from http header.
        chunk_size: int, optional
            Chunk size.
        params: any, optional
            Parameters will be passed to ``requests.get`` function.
            See Also: `requests <http://docs.python-requests.org/>'_
        kwargs: dict, optional
            Pass to ``requests.get`` function as the ``kwargs`` parameters.

        Returns
        -------
        str
            File path contains file name.
        """
        r = requests.get(url, params, **kwargs)
        r.raise_for_status()

        if not filename:
            if 'filename' in r.headers:
                filename = r.headers['filename']
            else:
                filename = url.split('/')[-1]

        if isinstance(save_to, str):
            save_to = Path(save_to)
        if not isinstance(save_to, Path) or not save_to.is_dir():
            raise RuntimeError('%s is not a legal path or not point to a dir' % save_to)

        file_ = str(save_to / filename)
        with open(file_, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        return file_

    @property
    def csv(self):
        return Dataset(*self._paths, backend='csv')

    @property
    def dataframe(self):
        return Dataset(*self._paths, backend='dataframe')

    @property
    def pickle(self):
        return Dataset(*self._paths, backend='pickle')

    @property
    def excel(self):
        return Dataset(*self._paths, backend='excel')

    def __call__(self, *args, **kwargs):
        return self.__extension__[self._backend][1](*args, **kwargs)

    def __getattr__(self, name):
        """
        Returns sub-dataset.

        Parameters
        ----------
        name: str
            Dataset name.

        Returns
        -------
        self
        """
        if name in self.__extension__:
            return self.__class__(*self._paths, backend=name)
        raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
