import os

if os.environ.get('DB_ENGINE') == 'mysql':
    import pymysql
    pymysql.install_as_MySQLdb()
