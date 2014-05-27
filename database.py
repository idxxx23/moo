#!/usr/bin/env python3

import os, re, sqlalchemy as sa
from multiprocessing import Pool
from multiprocessing.dummy import Pool
from multiprocessing.pool import ThreadPool as Pool # http://stackoverflow.com/questions/3033952/python-thread-pool-similar-to-the-multiprocessing-pool

# $$todo$$ ~> multiprocessing unexpectedly kill encfs mount-points

class Query():

    class mooError(Exception): pass

    def __init__(self, databases=None, *, config=None, script_directory='', parallel=None, debug=False):
        self.databases = self.get_databases(databases, config)
        self.script_directory = script_directory
        self.parallel = parallel
        self.debug = debug
        if self.debug:
            self.print_debug = print
        else:
            self.print_debug = self.nothing
        self.print_debug('$debug={}$'.format(self.debug))

    def nothing(*args, **kwargs): pass

    def get_databases(self, databases, config):
        if config and (databases is None):
            return self.read_file(config).splitlines()
        elif isinstance(databases, str) and (config is None):
            return [databases]
        elif databases and (config is None):
            return databases
        else:
            raise self.mooError('get_databases({}, {})'.format(databases, config))

    def get_query(self, query, script):
        if script and (query is None):
            return self.read_file(os.path.join(self.script_directory, script)).strip()
        elif query and (script is None):
            return query
        else:
            raise self.mooError('get_query({}, {})'.format(query, script))

    def read_file(self, filename):
        if os.path.exists(filename):
            with open(filename, mode='r', encoding='utf-8') as f:
                return f.read()
        else:
            raise self.mooError('file {} does not exist'.format(filename))

    def get_parallel(self, parallel):
        parallel = parallel or self.parallel or None
        self.print_debug('$parallel={}$'.format(parallel))
        return parallel

    def __call__(self, query=None, *, script=None, parallel=None): # functor
        self.query = self.get_query(query, script)
        print('[{}]'.format(self.query))
        with Pool(self.get_parallel(parallel)) as pool:
            pool.map_async(self.execute_query, self.databases, 1, self.r_print)
            pool.close()
            pool.join()
        print()

    def script(self, script=None, *, parallel=None):
        self.__call__(script=script, parallel=parallel)

    def hide_password(self, database):
        return re.sub(r':[^:]*@', r'@', database)

    def execute_query(self, database):
        r_queue = []
        r_queue.append('\n[{}] pid={}'.format(self.hide_password(database), os.getpid()))
        try:
            engine = sa.create_engine(database)
            connection = engine.connect()
            result = connection.execute(self.query)
            keys, rows = result.keys(), result.fetchall()
            result.close()
            connection.close()
            r_queue.append('{}'.format(keys))
            for row in rows:
                r_queue.append('{}'.format(row))
            if self.debug: r_queue.append('$num_rows={}$'.format(len(rows)))
            return r_queue
        except Exception as e:
            print('{}'.format(e))
            raise

    def r_print(self, r_queue):
        for rows in r_queue:
            for row in rows:
                print(row)

if __name__ == '__main__':
    Query('sqlite:///:memory:', debug=True)('select 23 as number union select 42 as number')
    Query('sqlite:///:memory:')('select 23 as number union select 42 as number')
