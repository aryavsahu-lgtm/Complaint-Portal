"""
Database Module - MongoDB Backend
Provides a MongoDB-backed database interface that mimics the SQLite Row/Cursor API.
All existing routes continue working without changes.
"""

import os
import re
import logging
import sqlite3
from datetime import datetime
from flask import g, current_app
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
import certifi

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global MongoDB client (reuse across requests) ---
_mongo_client = None
_mongo_db = None
_sqlite_conn = None
_mongo_connection_failed = False
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _get_sqlite_connection():
    """Get or create a local SQLite connection for offline/dev use."""
    global _sqlite_conn
    if _sqlite_conn is None:
        if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or not os.access(_BASE_DIR, os.W_OK):
            tmp_db = '/tmp/complaints.db'
            src_db = os.path.join(_BASE_DIR, 'complaints.db')
            if not os.path.exists(tmp_db) and os.path.exists(src_db):
                import shutil
                try:
                    shutil.copyfile(src_db, tmp_db)
                except Exception as e:
                    logger.warning(f"Could not copy seed DB to /tmp: {e}")
            db_path = tmp_db
        else:
            db_path = os.path.join(_BASE_DIR, 'complaints.db')
        _sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
        _sqlite_conn.row_factory = sqlite3.Row
        try:
            _sqlite_conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
    return _sqlite_conn


class SQLiteDBWrapper:
    """Lightweight wrapper that mimics the sqlite3 connection API for local development."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        return self.conn.execute(sql, params or [])

    def executemany(self, sql, params_list):
        return self.conn.executemany(sql, params_list)

    def commit(self):
        self.conn.commit()

    def close(self):
        # Keep the shared connection open for the life of the process.
        pass


def _get_mongo_connection():
    """Get or create a persistent MongoDB connection."""
    global _mongo_client, _mongo_db, _mongo_connection_failed
    
    if _mongo_connection_failed:
        raise ConnectionError("MongoDB connection previously failed; using SQLite fallback")
    
    if _mongo_db is not None:
        return _mongo_db
    
    mongo_uri = os.getenv('MONGO_URI')
    db_name = os.getenv('MONGO_DB_NAME', 'smart_complaint_system')
    
    if not mongo_uri:
        _mongo_connection_failed = True
        logger.info("No MONGO_URI configured; using SQLite fallback immediately.")
        raise ConnectionError("MONGO_URI not configured")

    use_sqlite_fallback = os.getenv('MONGO_USE_SQLITE_FALLBACK', 'false').lower() in {'1','true','yes','on'}
    if use_sqlite_fallback:
        _mongo_connection_failed = True
        logger.info("Local/dev SQLite fallback enabled in .env.")
        raise ConnectionError("SQLite fallback enabled")
    
    timeout_ms = int(os.getenv('MONGO_TIMEOUT_MS', '3000'))

    # Connection attempts
    attempts = [
        ("Standard Atlas (TLS with Certifi)", {
            'serverSelectionTimeoutMS': timeout_ms,
            'connectTimeoutMS': timeout_ms,
            'tlsCAFile': certifi.where()
        }),
        ("Standard Atlas (System TLS)", {
            'serverSelectionTimeoutMS': timeout_ms,
            'connectTimeoutMS': timeout_ms,
            'tls': True,
            'tlsAllowInvalidCertificates': True
        })
    ]

    last_error = None
    for name, args in attempts:
        try:
            logger.info(f"Attempting MongoDB connection: {name}")
            _mongo_client = MongoClient(mongo_uri, **args)
            _mongo_client.admin.command('ping')
            _mongo_db = _mongo_client[db_name]
            logger.info(f"✅ Connected to MongoDB database: {db_name} ({name})")
            return _mongo_db
        except Exception as e:
            msg = str(e)
            logger.warning(f"❌ {name} failed: {e}")
            last_error = e
            # If credentials are wrong, no need to retry with different TLS configs
            if "authentication failed" in msg.lower() or "bad auth" in msg.lower() or "auth failed" in msg.lower():
                logger.error("🚨 MongoDB Authentication Error: The username or password in MONGO_URI does not match your MongoDB Atlas Database User.")
                logger.error("👉 Please verify Database Access in MongoDB Atlas: https://cloud.mongodb.com")
                break
            continue
            
    _mongo_connection_failed = True
    logger.error(f"❌ MongoDB connection failed: {last_error}")
    raise last_error


def get_mongo_db():
    """Returns a MongoDB database instance (public API)."""
    return _get_mongo_connection()


# --- Auto-increment ID management ---
def _next_id(collection_name):
    """Generate auto-incrementing IDs like SQLite's AUTOINCREMENT."""
    db = _get_mongo_connection()
    result = db.counters.find_one_and_update(
        {'_id': collection_name},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=True
    )
    return result['seq']


# --- Row-like dictionary wrapper ---
class MongoRow(dict):
    """A dict subclass that supports both dict[key] and attribute access, mimicking sqlite3.Row."""
    def __getitem__(self, key):
        if isinstance(key, int):
            # Support positional index access like row[0]
            keys = list(self.keys())
            if key < len(keys):
                return super().__getitem__(keys[key])
            return None
        return super().__getitem__(key) if key in self else None
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)
    
    def keys(self):
        return super().keys()


# --- Cursor-like result wrapper ---
class MongoCursor:
    """Wraps MongoDB operation results to mimic sqlite3.Cursor."""
    def __init__(self, result=None, lastrowid=None):
        self._result = result if result is not None else []
        self.lastrowid = lastrowid
        self._iter = None
    
    def fetchone(self):
        if isinstance(self._result, list):
            return self._result[0] if self._result else None
        elif isinstance(self._result, MongoRow):
            return self._result
        return None
    
    def fetchall(self):
        if isinstance(self._result, list):
            return self._result
        elif isinstance(self._result, MongoRow):
            return [self._result]
        return []
    
    def __iter__(self):
        data = self.fetchall()
        return iter(data)


# --- SQL Parser & MongoDB Translator ---
class MongoDBWrapper:
    """
    Wraps a MongoDB database to accept SQL-like queries.
    Parses common SQL patterns used in this project and translates them to MongoDB operations.
    """
    
    def __init__(self, mongo_db):
        self.db = mongo_db
        self._pending_ops = []
    
    def execute(self, sql, params=None):
        """Parse SQL and execute equivalent MongoDB operation."""
        sql = sql.strip()
        params = list(params) if params else []
        
        # Replace ? placeholders with actual values for parsing
        sql_upper = sql.upper()
        
        try:
            if sql_upper.startswith('CREATE TABLE') or sql_upper.startswith('CREATE INDEX'):
                return MongoCursor()  # MongoDB doesn't need schema creation
            
            elif sql_upper.startswith('SELECT'):
                return self._handle_select(sql, params)
            
            elif sql_upper.startswith('INSERT'):
                return self._handle_insert(sql, params)
            
            elif sql_upper.startswith('UPDATE'):
                return self._handle_update(sql, params)
            
            elif sql_upper.startswith('DELETE'):
                return self._handle_delete(sql, params)
            
            else:
                logger.warning(f"Unhandled SQL: {sql[:100]}")
                return MongoCursor()
        
        except Exception as e:
            logger.error(f"MongoDB execute error: {e}\nSQL: {sql[:200]}\nParams: {params}")
            raise
    
    def executemany(self, sql, params_list):
        """Execute SQL for multiple parameter sets."""
        for params in params_list:
            self.execute(sql, params)
    
    def commit(self):
        """No-op for MongoDB (auto-commits)."""
        pass
    
    def close(self):
        """No-op - connection managed globally."""
        pass
    
    # --- SELECT Handler ---
    def _handle_select(self, sql, params):
        """Parse SELECT queries and convert to MongoDB find/aggregate."""
        sql_clean = sql.strip()
        
        # Handle SELECT last_insert_rowid()
        if 'last_insert_rowid' in sql_clean.lower():
            last_id = g.get('_last_insert_id', 0)
            return MongoCursor([MongoRow({'last_insert_rowid()': last_id})])
        
        # Handle SELECT COUNT(*) / aggregate queries
        if self._is_aggregate_query(sql_clean):
            return self._handle_aggregate(sql_clean, params)
        
        # Parse basic SELECT
        table = self._extract_table_from_select(sql_clean)
        if not table:
            logger.warning(f"Could not extract table from SELECT: {sql_clean[:100]}")
            return MongoCursor([])
        
        # Build MongoDB query filter
        mongo_filter = self._build_filter(sql_clean, params)
        
        # Build projection
        projection = self._build_projection(sql_clean, table)
        
        # Handle JOINs
        if ' JOIN ' in sql_clean.upper():
            return self._handle_join_select(sql_clean, params)
        
        # Handle ORDER BY
        sort = self._extract_sort(sql_clean)
        
        # Handle LIMIT
        limit = self._extract_limit(sql_clean)
        
        # Handle GROUP BY
        if 'GROUP BY' in sql_clean.upper():
            return self._handle_group_by(sql_clean, params, table)
        
        # Execute find
        cursor = self.db[table].find(mongo_filter, projection)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        
        results = [MongoRow(self._clean_doc(doc)) for doc in cursor]
        return MongoCursor(results)
    
    # --- INSERT Handler ---
    def _handle_insert(self, sql, params):
        """Parse INSERT queries and convert to MongoDB insert or upsert."""
        sql_clean = sql.strip().replace('\n', ' ')
        
        # Check for ON CONFLICT (SQLite/Postgres style upsert)
        on_conflict_match = re.search(r'ON\s+CONFLICT\s*\(([^)]+)\)', sql_clean, re.IGNORECASE)
        
        # Capture the main insert part, allowing for ON CONFLICT
        match = re.match(
            r'INSERT\s+(?:OR\s+REPLACE\s+)?INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)',
            sql_clean, re.IGNORECASE
        )
        
        if not match:
            logger.warning(f"Could not parse INSERT: {sql[:100]}")
            return MongoCursor()
        
        table = match.group(1)
        columns = [c.strip() for c in match.group(2).split(',')]
        values_part = match.group(3).split(',')
        
        # Build document
        doc = {}
        param_idx = 0
        for i, col in enumerate(columns):
            val_expr = values_part[i].strip() if i < len(values_part) else '?'
            if val_expr == '?':
                if param_idx < len(params):
                    doc[col] = params[param_idx]
                    param_idx += 1
                else:
                    doc[col] = None
            elif val_expr.upper() == 'CURRENT_TIMESTAMP':
                doc[col] = datetime.now()
            else:
                # Handle literals if any
                doc[col] = val_expr.strip("'\"")
        
        # Add ID if missing and not an upsert that might already have one
        if 'id' not in doc and not on_conflict_match:
             doc['id'] = _next_id(table)
        
        # Add timestamps if missing
        now = datetime.now()
        if 'created_at' not in doc:
            doc['created_at'] = now
        if 'updated_at' not in doc:
            doc['updated_at'] = now
        
        # Apply defaults
        doc = self._apply_defaults(table, doc)
        
        # Apply schema fixes for Atlas
        if table == 'complaints':
            if 'user_id' in doc:
                doc['user_id'] = str(doc['user_id'])
            if 'location' in doc and isinstance(doc['location'], str):
                doc['location'] = {'address': doc['location']}
            for k in ['is_escalated', 'is_authentic', 'gps_accuracy']:
                if k in doc:
                    try: doc[k] = bool(doc[k]) if k != 'gps_accuracy' else float(doc[k])
                    except: pass

        # Handle Upsert
        if on_conflict_match:
            conflict_col = on_conflict_match.group(1).strip()
            if conflict_col in doc:
                filter_val = doc[conflict_col]
                # For upserts, we usually don't want to overwrite the creation date if it exists
                # But for simplicity, we'll just set everything. 
                # Better: only set created_at if it's a new document
                self.db[table].update_one(
                    {conflict_col: filter_val},
                    {'$set': doc},
                    upsert=True
                )
                if 'id' in doc: g._last_insert_id = doc['id']
                return MongoCursor(lastrowid=doc.get('id'))

        self.db[table].insert_one(doc)
        if 'id' in doc: g._last_insert_id = doc['id']
        
        return MongoCursor(lastrowid=doc.get('id'))
    
    # --- UPDATE Handler ---
    def _handle_update(self, sql, params):
        """Parse UPDATE queries and convert to MongoDB update."""
        # Extract table name
        match = re.match(r'UPDATE\s+(\w+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?$', sql.strip(), re.IGNORECASE | re.DOTALL)
        if not match:
            logger.warning(f"Could not parse UPDATE: {sql[:100]}")
            return MongoCursor()
        
        table = match.group(1)
        set_clause = match.group(2).strip()
        where_clause = match.group(3).strip() if match.group(3) else None
        
        # Parse SET clause
        update_doc = {}
        inc_doc = {}
        param_idx = 0
        
        # Handle SET parts
        set_parts = self._split_set_clause(set_clause)
        for part in set_parts:
            part = part.strip()
            if '=' in part:
                col, val = part.split('=', 1)
                col = col.strip()
                val = val.strip()
                
                if val == '?':
                    update_doc[col] = params[param_idx] if param_idx < len(params) else None
                    param_idx += 1
                elif val == 'CURRENT_TIMESTAMP':
                    update_doc[col] = datetime.now()
                elif 'current_load + 1' in val.lower():
                    inc_doc['current_load'] = 1
                elif 'current_load - 1' in val.lower():
                    inc_doc['current_load'] = -1
                else:
                    update_doc[col] = val.strip("'\"")
        
        # Parse WHERE clause
        mongo_filter = {}
        if where_clause:
            remaining_params = params[param_idx:]
            mongo_filter = self._parse_where(where_clause, remaining_params)
        
        # Build update operation
        mongo_update = {}
        if update_doc:
            mongo_update['$set'] = update_doc
        if inc_doc:
            mongo_update['$inc'] = inc_doc
        
        if mongo_update:
            # Schema fix: Wrap location if updating it in complaints
            if table == 'complaints' and '$set' in mongo_update and 'location' in mongo_update['$set']:
                 if isinstance(mongo_update['$set']['location'], str):
                     mongo_update['$set']['location'] = {'address': mongo_update['$set']['location']}
            
            logger.info(f"UPDATE {table}: filter={mongo_filter}, update={mongo_update}")
            result = self.db[table].update_many(mongo_filter, mongo_update)
            logger.info(f"UPDATE result: matched={result.matched_count}, modified={result.modified_count}")
        
        return MongoCursor()
    
    # --- DELETE Handler ---
    def _handle_delete(self, sql, params):
        """Parse DELETE queries and convert to MongoDB delete."""
        match = re.match(r'DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+))?', sql.strip(), re.IGNORECASE)
        if not match:
            return MongoCursor()
        
        table = match.group(1)
        where_clause = match.group(2)
        
        mongo_filter = {}
        if where_clause:
            mongo_filter = self._parse_where(where_clause, params)
        
        self.db[table].delete_many(mongo_filter)
        return MongoCursor()
    
    # --- Helper: Parse WHERE clause ---
    def _parse_where(self, where_clause, params):
        """Convert SQL WHERE clause to MongoDB filter."""
        mongo_filter = {}
        param_idx = 0
        
        # Remove leading/trailing whitespace
        where_clause = where_clause.strip()
        
        # Remove trailing ORDER BY, LIMIT, GROUP BY
        for keyword in ['ORDER BY', 'LIMIT', 'GROUP BY']:
            idx = where_clause.upper().find(keyword)
            if idx != -1:
                where_clause = where_clause[:idx].strip()
        
        # Split by AND
        conditions = re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE)
        
        and_conditions = []
        for cond in conditions:
            cond = cond.strip()
            if not cond or cond == '1=1':
                continue
            
            # Handle OR within conditions
            if ' OR ' in cond.upper():
                or_parts = re.split(r'\s+OR\s+', cond, flags=re.IGNORECASE)
                or_conditions = []
                for op in or_parts:
                    op = op.strip().strip('()')
                    f, param_idx = self._parse_single_condition(op, params, param_idx)
                    if f:
                        or_conditions.append(f)
                if or_conditions:
                    and_conditions.append({'$or': or_conditions})
                continue
            
            # Handle IN subquery
            if 'IN (' in cond.upper() and 'SELECT' in cond.upper():
                # Complex subquery - skip for simplicity
                continue
            
            # Handle parenthesized conditions (e.g., "(title LIKE ? OR description LIKE ?)")
            if cond.startswith('(') and cond.endswith(')'):
                inner = cond[1:-1]
                if ' OR ' in inner.upper():
                    or_parts = re.split(r'\s+OR\s+', inner, flags=re.IGNORECASE)
                    or_conditions = []
                    for op in or_parts:
                        op = op.strip()
                        f, param_idx = self._parse_single_condition(op, params, param_idx)
                        if f:
                            or_conditions.append(f)
                    if or_conditions:
                        and_conditions.append({'$or': or_conditions})
                    continue
            
            f, param_idx = self._parse_single_condition(cond, params, param_idx)
            if f:
                and_conditions.append(f)
        
        if len(and_conditions) == 0:
            return {}
        elif len(and_conditions) == 1:
            return and_conditions[0]
        else:
            return {'$and': and_conditions}
    
    def _parse_single_condition(self, cond, params, param_idx):
        """Parse a single condition like 'col = ?' or 'col LIKE ?' or 'col IS NOT NULL'."""
        cond = cond.strip()
        
        # Remove table alias prefixes (c., u., s., ul., aa.)
        cond = re.sub(r'\b\w+\.(\w+)', r'\1', cond)
        
        # Handle IS NOT NULL
        match = re.match(r'(\w+)\s+IS\s+NOT\s+NULL', cond, re.IGNORECASE)
        if match:
            return {match.group(1): {'$ne': None}}, param_idx
        
        # Handle IS NULL
        match = re.match(r'(\w+)\s+IS\s+NULL', cond, re.IGNORECASE)
        if match:
            return {match.group(1): None}, param_idx
        
        # Handle LIKE
        match = re.match(r'(\w+)\s+LIKE\s+\?', cond, re.IGNORECASE)
        if match:
            col = match.group(1)
            val = params[param_idx] if param_idx < len(params) else ''
            param_idx += 1
            # Convert SQL LIKE to regex: %text% -> regex
            regex_val = val.replace('%', '.*')
            return {col: {'$regex': regex_val, '$options': 'i'}}, param_idx
        
        # Handle > or >=
        match = re.match(r'(\w+)\s*>\s*\?', cond, re.IGNORECASE)
        if match:
            col = match.group(1)
            val = params[param_idx] if param_idx < len(params) else None
            param_idx += 1
            return {col: {'$gt': val}}, param_idx
        
        match = re.match(r'(\w+)\s*>=\s*\?', cond, re.IGNORECASE)
        if match:
            col = match.group(1)
            val = params[param_idx] if param_idx < len(params) else None
            param_idx += 1
            return {col: {'$gte': val}}, param_idx
        
        # Handle = ?
        match = re.match(r'(\w+)\s*=\s*\?', cond, re.IGNORECASE)
        if match:
            col = match.group(1)
            val = params[param_idx] if param_idx < len(params) else None
            param_idx += 1
            
            # Application-specific fix for ID types
            if col in ('id', 'user_id', 'complaint_id'):
                if isinstance(val, str) and val.isdigit():
                    val = int(val)
                if col == 'user_id' and not isinstance(val, str):
                    val = str(val)
                
            return {col: val}, param_idx
        
        # Handle col = value (literal)
        match = re.match(r"(\w+)\s*=\s*'([^']*)'", cond, re.IGNORECASE)
        if match:
            return {match.group(1): match.group(2)}, param_idx
        
        match = re.match(r'(\w+)\s*=\s*(\d+)', cond, re.IGNORECASE)
        if match:
            return {match.group(1): int(match.group(2))}, param_idx
        
        return None, param_idx
    
    # --- Helper: Extract table name from SELECT ---
    def _extract_table_from_select(self, sql):
        """Extract the main table name from a SELECT statement."""
        # Handle "FROM table" or "FROM table alias"
        match = re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        return match.group(1) if match else None
    
    # --- Helper: Build projection ---
    def _build_projection(self, sql, table):
        """Build MongoDB projection from SELECT columns."""
        # For SELECT * or complex queries, return all fields
        match = re.match(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if match:
            cols = match.group(1).strip()
            if cols == '*' or '.*' in cols or '(' in cols:
                return {'_id': 0}
        return {'_id': 0}
    
    # --- Helper: Build filter from full SQL ---
    def _build_filter(self, sql, params):
        """Extract WHERE clause from full SQL and build filter."""
        match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|\s*$)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            where = match.group(1).strip()
            return self._parse_where(where, params)
        return {}
    
    # --- Helper: Extract ORDER BY ---
    def _extract_sort(self, sql):
        """Extract ORDER BY clause and convert to MongoDB sort."""
        match = re.search(r'ORDER\s+BY\s+(.+?)(?:\s+LIMIT|\s*$)', sql, re.IGNORECASE)
        if not match:
            return None
        
        sort_clause = match.group(1).strip()
        sort_list = []
        for part in sort_clause.split(','):
            part = part.strip()
            # Remove table alias
            part = re.sub(r'\w+\.', '', part)
            if ' DESC' in part.upper():
                col = part.upper().replace(' DESC', '').strip().lower()
                sort_list.append((col, DESCENDING))
            else:
                col = part.upper().replace(' ASC', '').strip().lower()
                sort_list.append((col, ASCENDING))
        return sort_list if sort_list else None
    
    # --- Helper: Extract LIMIT ---
    def _extract_limit(self, sql):
        """Extract LIMIT value from SQL."""
        match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        return int(match.group(1)) if match else None
    
    # --- Helper: Check if aggregate query ---
    def _is_aggregate_query(self, sql):
        """Check if query uses aggregate functions."""
        upper = sql.upper()
        # Check for aggregate functions not inside CASE WHEN (basic check)
        has_agg = any(func in upper for func in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN('])
        has_group = 'GROUP BY' in upper
        return has_agg and not has_group
    
    # --- Helper: Handle aggregate queries ---
    def _handle_aggregate(self, sql, params):
        """Handle SELECT with COUNT/SUM/AVG without GROUP BY."""
        table = self._extract_table_from_select(sql)
        if not table:
            return MongoCursor([MongoRow({'count': 0})])
        
        mongo_filter = self._build_filter(sql, params)
        
        # Parse what aggregates are needed
        select_match = re.match(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return MongoCursor([MongoRow({'count': 0})])
        
        select_clause = select_match.group(1)
        
        # Simple COUNT(*)
        if re.match(r'\s*COUNT\s*\(\s*\*\s*\)\s*$', select_clause, re.IGNORECASE):
            count = self.db[table].count_documents(mongo_filter)
            return MongoCursor([MongoRow({0: count, 'count': count})])
        
        # Complex aggregate with aliases
        pipeline = [{'$match': mongo_filter}] if mongo_filter else []
        
        group_stage = {'_id': None}
        result_fields = {}
        
        # Parse each aggregate expression
        parts = self._split_select_parts(select_clause)
        for part in parts:
            part = part.strip()
            alias_match = re.search(r'\s+as\s+(\w+)\s*$', part, re.IGNORECASE)
            alias = alias_match.group(1) if alias_match else None
            expr = part[:alias_match.start()].strip() if alias_match else part
            
            # COUNT(*)
            if re.match(r'COUNT\s*\(\s*\*\s*\)', expr, re.IGNORECASE):
                key = alias or 'total'
                group_stage[key] = {'$sum': 1}
            
            # COUNT(DISTINCT field)
            elif re.match(r'COUNT\s*\(\s*DISTINCT\s+(\w+)\s*\)', expr, re.IGNORECASE):
                m = re.match(r'COUNT\s*\(\s*DISTINCT\s+(\w+)\s*\)', expr, re.IGNORECASE)
                field = m.group(1)
                key = alias or 'count'
                group_stage[key] = {'$addToSet': f'${field}'}
                result_fields[key] = 'count_set'
            
            # SUM(CASE WHEN ... THEN 1 ELSE 0 END)
            elif 'CASE WHEN' in expr.upper():
                case_match = re.search(r"CASE\s+WHEN\s+(\w+)\s*=\s*'([^']+)'\s+THEN\s+1\s+ELSE\s+0\s+END", expr, re.IGNORECASE)
                if case_match:
                    field = case_match.group(1)
                    value = case_match.group(2)
                    key = alias or field
                    group_stage[key] = {'$sum': {'$cond': [{'$eq': [f'${field}', value]}, 1, 0]}}
            
            # AVG(CASE WHEN ... THEN field END)
            elif 'AVG(' in expr.upper() and 'CASE' in expr.upper():
                avg_match = re.search(r'AVG\s*\(\s*CASE\s+WHEN\s+(\w+)\s+IS\s+NOT\s+NULL\s+THEN\s+(\w+)\s+END\s*\)', expr, re.IGNORECASE)
                if avg_match:
                    cond_field = avg_match.group(1)
                    val_field = avg_match.group(2)
                    key = alias or 'avg'
                    group_stage[key] = {
                        '$avg': {
                            '$cond': [
                                {'$ne': [f'${cond_field}', None]},
                                f'${val_field}',
                                None
                            ]
                        }
                    }
            
            # AVG(field)
            elif re.match(r'AVG\s*\(\s*(\w+)\s*\)', expr, re.IGNORECASE):
                m = re.match(r'AVG\s*\(\s*(\w+)\s*\)', expr, re.IGNORECASE)
                field = m.group(1)
                key = alias or 'avg'
                group_stage[key] = {'$avg': f'${field}'}
        
        pipeline.append({'$group': group_stage})
        
        try:
            agg_result = list(self.db[table].aggregate(pipeline))
            if agg_result:
                row = agg_result[0]
                row.pop('_id', None)
                # Process special fields
                for key, ftype in result_fields.items():
                    if ftype == 'count_set' and key in row:
                        row[key] = len(row[key])
                return MongoCursor([MongoRow(row)])
            else:
                # Return zeros
                zero_row = {}
                for key in group_stage:
                    if key != '_id':
                        zero_row[key] = 0
                return MongoCursor([MongoRow(zero_row)])
        except Exception as e:
            logger.error(f"Aggregate error: {e}")
            return MongoCursor([MongoRow({})])
    
    # --- Helper: Handle GROUP BY ---
    def _handle_group_by(self, sql, params, table):
        """Handle SELECT with GROUP BY."""
        mongo_filter = self._build_filter(sql, params)
        
        # Extract GROUP BY field
        gb_match = re.search(r'GROUP\s+BY\s+(\w+)', sql, re.IGNORECASE)
        if not gb_match:
            return MongoCursor([])
        group_field = gb_match.group(1)
        
        # Extract select parts
        select_match = re.match(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return MongoCursor([])
        
        pipeline = []
        if mongo_filter:
            pipeline.append({'$match': mongo_filter})
        
        # Build group stage
        group_stage = {'_id': f'${group_field}'}
        select_clause = select_match.group(1)
        
        # Check for COUNT(*)
        if 'COUNT(*)' in sql.upper():
            count_alias = 'count'
            alias_match = re.search(r'COUNT\s*\(\s*\*\s*\)\s+as\s+(\w+)', sql, re.IGNORECASE)
            if alias_match:
                count_alias = alias_match.group(1)
            group_stage[count_alias] = {'$sum': 1}
        
        pipeline.append({'$group': group_stage})
        
        # Handle ORDER BY
        sort = self._extract_sort(sql)
        if sort:
            sort_stage = {}
            for col, direction in sort:
                if col == group_field:
                    sort_stage['_id'] = direction
                else:
                    sort_stage[col] = direction
            if sort_stage:
                pipeline.append({'$sort': sort_stage})
        
        # Handle LIMIT
        limit = self._extract_limit(sql)
        if limit:
            pipeline.append({'$limit': limit})
        
        try:
            results = list(self.db[table].aggregate(pipeline))
            rows = []
            for r in results:
                row = {group_field: r['_id']}
                for k, v in r.items():
                    if k != '_id':
                        row[k] = v
                rows.append(MongoRow(row))
            return MongoCursor(rows)
        except Exception as e:
            logger.error(f"GROUP BY error: {e}")
            return MongoCursor([])
    
    # --- Helper: Handle JOIN queries ---
    def _handle_join_select(self, sql, params):
        """Handle SELECT with JOIN by doing lookups."""
        # For this project, the main JOINs are:
        # 1. complaints JOIN users (admin dashboard)
        # 2. chat_sessions JOIN users
        # 3. user_locations JOIN users
        
        # Extract main table and joined table
        from_match = re.search(r'FROM\s+(\w+)\s+(\w+)?', sql, re.IGNORECASE)
        join_match = re.findall(r'(?:LEFT\s+)?JOIN\s+(\w+)\s+(\w+)?\s+ON\s+([^\s]+)\s*=\s*([^\s]+)', sql, re.IGNORECASE)
        
        if not from_match:
            return MongoCursor([])
        
        main_table = from_match.group(1)
        main_alias = from_match.group(2) if from_match.group(2) else main_table
        
        # Get main collection results first
        mongo_filter = self._build_filter(sql, params)
        sort = self._extract_sort(sql)
        limit = self._extract_limit(sql)
        
        cursor = self.db[main_table].find(mongo_filter, {'_id': 0})
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        
        main_docs = list(cursor)
        
        # For each join, lookup the related data
        results = []
        for doc in main_docs:
            row = self._clean_doc(doc)  # Use clean_doc to format dates/objects
            for join_table, join_alias, left_key, right_key in join_match:
                # Extract field names (remove table aliases)
                left_field = re.sub(r'\w+\.', '', left_key)
                right_field = re.sub(r'\w+\.', '', right_key)
                
                # Determine which field belongs to which table
                lookup_field = right_field if left_field in row else left_field
                local_value = row.get(left_field) or row.get(right_field)
                
                if local_value is not None:
                    joined_doc = self.db[join_table].find_one(
                        {lookup_field: local_value}, {'_id': 0}
                    )
                    # Fallback: Try int/str type conversion if not found
                    if not joined_doc:
                        if isinstance(local_value, str) and local_value.isdigit():
                             joined_doc = self.db[join_table].find_one({lookup_field: int(local_value)}, {'_id': 0})
                        elif isinstance(local_value, int):
                             joined_doc = self.db[join_table].find_one({lookup_field: str(local_value)}, {'_id': 0})
                    
                    if joined_doc:
                        joined_doc = self._clean_doc(joined_doc)  # Clean joined data too
                        # Add joined fields (with alias prefix removed)
                        for k, v in joined_doc.items():
                            if k not in row:  # Don't overwrite main table fields
                                row[k] = v
            
            results.append(MongoRow(row))
        
        return MongoCursor(results)
    
    # --- Helper: Split SET clause properly ---
    def _split_set_clause(self, set_clause):
        """Split SET clause by commas, handling nested expressions."""
        parts = []
        depth = 0
        current = ""
        for ch in set_clause:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 0:
                parts.append(current)
                current = ""
                continue
            current += ch
        if current.strip():
            parts.append(current)
        return parts
    
    # --- Helper: Split SELECT parts ---
    def _split_select_parts(self, select_clause):
        """Split SELECT clause by commas, handling nested expressions."""
        return self._split_set_clause(select_clause)
    
    # --- Helper: Clean MongoDB document ---
    def _clean_doc(self, doc):
        """Remove MongoDB _id and ensure standard field names."""
        if doc is None:
            return {}
        clean = {}
        for k, v in doc.items():
            if k == '_id':
                continue
            # Convert datetime back to string for SQLite compatibility
            if isinstance(v, datetime):
                clean[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            # Unwrap location object
            elif k == 'location' and isinstance(v, dict) and 'address' in v:
                clean[k] = v['address']
            else:
                clean[k] = v
        return clean
    
    # --- Helper: Apply default values ---
    def _apply_defaults(self, table, doc):
        """Apply default values for missing fields based on table schema."""
        defaults = {
            'users': {
                'is_admin': False,
                'tracking_consent': False,
            },
            'complaints': {
                'status': 'Pending',
                'priority': 'Low',
                'assigned_to': 'General Administration',
                'sentiment_score': 0.5,
                'is_escalated': False,
                'is_authentic': True,
                'city': 'Raipur',
            },
            'workers': {
                'current_load': 0,
                'avg_resolution_time': 0.0,
                'performance_rating': 5.0,
                'is_active': True,
            },
            'notifications': {
                'is_read': False,
            },
            'chat_sessions': {
                'current_state': 'idle',
            },
        }
        
        if table in defaults:
            for key, default_val in defaults[table].items():
                if key not in doc or doc[key] is None:
                    doc[key] = default_val
        
        return doc


# --- Flask Integration (drop-in replacements) ---

def get_db():
    """Returns a database wrapper that mimics sqlite3.Connection."""
    if 'db' not in g:
        try:
            if _mongo_connection_failed:
                raise ConnectionError("MongoDB fallback already active")
            mongo = _get_mongo_connection()
            g.db = MongoDBWrapper(mongo)
        except Exception as e:
            logger.info(f"Using SQLite fallback for fast local access: {e}")
            g.db = SQLiteDBWrapper(_get_sqlite_connection())
    return g.db


def close_db(e=None):
    """Remove wrapper from Flask g without closing the shared SQLite connection."""
    g.pop('db', None)


def init_db():
    """Initialize a local SQLite database for development when MongoDB is unavailable."""
    try:
        db = _get_mongo_connection()
    except Exception as e:
        logger.warning(f"MongoDB unavailable; using SQLite fallback for initialization: {e}")
        conn = _get_sqlite_connection()
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, email TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0, tracking_consent INTEGER DEFAULT 0, role TEXT DEFAULT 'Citizen', subsidiary TEXT DEFAULT 'SECL', created_at TEXT, updated_at TEXT)")
        conn.execute("""CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT DEFAULT '',
            category TEXT,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            priority TEXT DEFAULT 'Low',
            assigned_to TEXT DEFAULT 'General Administration',
            city TEXT DEFAULT 'Raipur',
            sentiment_score REAL DEFAULT 0.5,
            is_escalated INTEGER DEFAULT 0,
            is_authentic INTEGER DEFAULT 1,
            location TEXT,
            latitude FLOAT,
            longitude FLOAT,
            user_latitude FLOAT,
            user_longitude FLOAT,
            evidence_latitude FLOAT,
            evidence_longitude FLOAT,
            google_place_id TEXT,
            emotion_data TEXT,
            vision_data TEXT,
            authenticity_data TEXT,
            source TEXT,
            rating REAL,
            ref_no TEXT,
            created_at TEXT,
            updated_at TEXT
        )""")
        conn.execute("CREATE TABLE IF NOT EXISTS workers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, skill TEXT, current_load INTEGER DEFAULT 0, avg_resolution_time REAL DEFAULT 0.0, performance_rating REAL DEFAULT 5.0, is_active INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT)")
        conn.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_id INTEGER,
            role TEXT,
            message TEXT,
            response TEXT,
            intent TEXT DEFAULT 'general',
            emotion TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            user_id INTEGER,
            current_state TEXT DEFAULT 'idle',
            created_at TEXT,
            updated_at TEXT
        )""")
        conn.execute("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT, created_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS user_locations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, latitude REAL, longitude REAL, address TEXT, created_at TEXT)")
        # Seed Essential Demo Accounts if not present
        demo_accounts = [
            ('admin', 'admin@mineguard.gov.in', 'admin123', 1, 'Admin', 'Coal India HQ'),
            ('manager', 'manager@mineguard.gov.in', 'manager123', 1, 'Mine Manager', 'SECL'),
            ('safety', 'safety@mineguard.gov.in', 'safety123', 1, 'Safety Officer', 'SECL'),
            ('inspector', 'inspector@dgms.gov.in', 'inspector123', 1, 'Inspector', 'DGMS'),
            ('worker', 'worker@mineguard.gov.in', 'worker123', 0, 'Worker', 'SECL'),
        ]
        now_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for uname, uemail, upass, is_adm, urole, usub in demo_accounts:
            try:
                cur = conn.cursor()
                cur.execute("SELECT id FROM users WHERE username = ? OR email = ?", (uname, uemail))
                if not cur.fetchone():
                    hashed_pw = generate_password_hash(upass, method='pbkdf2:sha256')
                    cur.execute("""INSERT INTO users (username, email, password, is_admin, tracking_consent, role, subsidiary, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)""",
                                (uname, uemail, hashed_pw, is_adm, urole, usub, now_dt, now_dt))
            except Exception as user_seed_err:
                logger.warning(f"Could not seed demo user {uname}: {user_seed_err}")
        conn.commit()

        # Coal Mining Governance & Compliance Platform Core Tables
        conn.execute("""CREATE TABLE IF NOT EXISTS mines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            subsidiary TEXT,
            area TEXT,
            mine_type TEXT,
            lease_area_ha REAL,
            ec_capacity_mtpa REAL,
            latitude REAL,
            longitude REAL,
            safety_officer TEXT,
            colliery_manager TEXT,
            compliance_score REAL DEFAULT 85.0,
            safety_rating REAL DEFAULT 4.5,
            status TEXT DEFAULT 'Active',
            created_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS statutory_compliance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mine_id INTEGER,
            regulatory_body TEXT,
            regulation_ref TEXT,
            title TEXT,
            category TEXT,
            frequency TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'Compliant',
            risk_score REAL DEFAULT 20.0,
            responsible_officer TEXT,
            evidence_file TEXT,
            remarks TEXT,
            created_at TEXT,
            updated_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS field_inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mine_id INTEGER,
            inspector_name TEXT,
            shift TEXT,
            location_pit_seam TEXT,
            violation_category TEXT,
            violation_title TEXT,
            description TEXT,
            risk_level TEXT DEFAULT 'Medium',
            latitude REAL,
            longitude REAL,
            audio_attachment TEXT,
            photo_attachment TEXT,
            authenticity_score REAL DEFAULT 95.0,
            is_offline_synced INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            updated_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS capa_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id INTEGER,
            mine_id INTEGER,
            title TEXT,
            root_cause TEXT,
            corrective_action TEXT,
            preventive_action TEXT,
            assigned_engineer TEXT,
            target_date TEXT,
            completion_date TEXT,
            verification_evidence TEXT,
            sign_off_by TEXT,
            status TEXT DEFAULT 'In Progress',
            created_at TEXT,
            updated_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            license_no TEXT,
            subsidiary TEXT,
            mine_id INTEGER,
            contact_person TEXT,
            contact_phone TEXT,
            active_workers INTEGER DEFAULT 50,
            safety_rating REAL DEFAULT 4.5,
            compliance_score REAL DEFAULT 88.0,
            pf_esi_compliant INTEGER DEFAULT 1,
            vtc_training_pct REAL DEFAULT 92.0,
            form_o_medical_pct REAL DEFAULT 95.0,
            license_expiry TEXT,
            created_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS mine_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mine_id INTEGER,
            zone_name TEXT,
            ch4_percent REAL DEFAULT 0.15,
            co_ppm REAL DEFAULT 3.2,
            dust_pm10 REAL DEFAULT 85.0,
            dust_pm25 REAL DEFAULT 42.0,
            airflow_cfm REAL DEFAULT 65000.0,
            temperature_c REAL DEFAULT 28.5,
            slope_displacement_mm REAL DEFAULT 1.2,
            water_ph REAL DEFAULT 7.2,
            alert_level TEXT DEFAULT 'Normal',
            timestamp TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS escalation_matrix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT,
            entity_id INTEGER,
            current_level INTEGER DEFAULT 1,
            escalated_to TEXT,
            triggered_at TEXT,
            due_deadline TEXT,
            status TEXT DEFAULT 'Active',
            reason TEXT,
            created_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS audit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_index INTEGER,
            previous_hash TEXT,
            current_hash TEXT,
            timestamp TEXT,
            actor_id TEXT,
            actor_name TEXT,
            action_type TEXT,
            entity_affected TEXT,
            details TEXT,
            payload_json TEXT
        )""")

        conn.commit()

        # Seed Coal Mining Data if empty
        try:
            from ai_engine.crypto_audit import CryptoAuditLedger
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM mines")
            if cur.fetchone()[0] == 0:
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                mines_data = [
                    ('Gevra Mega Open Cast Project', 'SECL', 'Korba Area', 'Open Cast (OCP)', 4184.0, 70.0, 22.3385, 82.5925, 'S. K. Verma (First Class)', 'R. P. Mishra', 94.5, 4.8, 'Active', now_str),
                    ('Dipka Open Cast Mine', 'SECL', 'Dipka Area', 'Open Cast (OCP)', 2012.0, 40.0, 22.3168, 82.5510, 'A. K. Sharma (First Class)', 'V. B. Rao', 88.0, 4.4, 'Active', now_str),
                    ('Bhubaneswari OCP', 'MCL', 'Talcher Coalfields', 'Open Cast (OCP)', 1845.0, 30.0, 20.9500, 85.2167, 'P. K. Jena (First Class)', 'M. K. Sahoo', 91.2, 4.6, 'Active', now_str),
                    ('Moonidih Underground Mine', 'BCCL', 'Western Jharia', 'Underground (UG)', 1250.0, 5.0, 23.7431, 86.3458, 'B. N. Pandey (First Class)', 'S. Chatterjee', 82.4, 4.2, 'Active', now_str),
                    ('Ashok Open Cast Project', 'CCL', 'North Karanpura', 'Open Cast (OCP)', 1620.0, 20.0, 23.7500, 85.0500, 'D. K. Yadav (First Class)', 'T. N. Singh', 86.5, 4.3, 'Active', now_str),
                    ('Umrer Open Cast Mine', 'WCL', 'Umrer Area', 'Open Cast (OCP)', 980.0, 10.0, 20.8540, 79.3280, 'M. R. Joshi (First Class)', 'K. L. Patel', 89.0, 4.5, 'Active', now_str),
                    ('Rajmahal Open Cast Project', 'ECL', 'Rajmahal Area', 'Open Cast (OCP)', 2100.0, 25.0, 25.0489, 87.4125, 'S. Roy (First Class)', 'A. Mukherjee', 84.0, 4.1, 'Active', now_str),
                    ('Jayant Mega OCP', 'NCL', 'Singrauli Coalfield', 'Open Cast (OCP)', 3200.0, 30.0, 24.1167, 82.6833, 'R. K. Choubey (First Class)', 'A. K. Tiwari', 93.0, 4.7, 'Active', now_str),
                    ('PVK Underground Incline', 'SCCL', 'Kothagudem Area', 'Underground (UG)', 850.0, 3.5, 17.5500, 80.6167, 'V. Srinivas (First Class)', 'Ch. Ramana', 87.8, 4.4, 'Active', now_str)
                ]
                cur.executemany("""INSERT INTO mines (name, subsidiary, area, mine_type, lease_area_ha, ec_capacity_mtpa, latitude, longitude, safety_officer, colliery_manager, compliance_score, safety_rating, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", mines_data)

                # Seed Statutory Compliances
                compliances = [
                    (1, 'DGMS', 'CMR 2017 Reg 123', 'Scientific Strata Support Plan Approval', 'Safety', 'Annual', '2026-11-30', 'Compliant', 15.0, 'S. K. Verma', 'DGMS_Strata_Approval_2026.pdf', 'Approved by CIM Eastern Circle; roof bolting QA certified.', now_str, now_str),
                    (1, 'MoEFCC', 'EC-J-11015/2020-IA.II(M)', 'Six-Monthly Environmental Compliance Statement', 'Environment', 'Half-Yearly', '2026-09-30', 'Approaching Deadline', 45.0, 'Dr. Sunita (Env Head)', 'EC_Compliance_Q2_2026.pdf', 'CAQM station continuous uplink operational; topsoil conservation report attached.', now_str, now_str),
                    (1, 'DGMS', 'CMR 2017 Reg 169', 'Inflammable Gas & Ventilation Telemetry Audit', 'Safety', 'Quarterly', '2026-08-30', 'Compliant', 20.0, 'S. K. Verma', 'Ventilation_Survey_Report.pdf', 'Air quantity in main intake 82,000 CFM; Methane background < 0.12%.', now_str, now_str),
                    (2, 'CPCB/SPCB', 'Water Act Sec 25/26', 'Effluent Treatment & Acid Mine Drainage Compliance', 'Environment', 'Monthly', '2026-09-15', 'Compliant', 25.0, 'V. B. Rao', 'ETP_Water_Quality_Aug2026.pdf', 'ETP discharge pH 7.4, TSS 42 mg/L within CPCB standards.', now_str, now_str),
                    (4, 'DGMS', 'CMR 2017 Reg 144', 'Continuous Carbon Monoxide & Spontaneous Heating Scan', 'Safety', 'Daily', '2026-08-25', 'Critical Breach', 92.0, 'B. N. Pandey', 'CO_Sensor_Alert_Log.pdf', 'Sensor in Panel 4 return showed CO spike (14 ppm). Nitrogen flushing activated.', now_str, now_str),
                    (3, 'Labour Dept', 'Mines Rules 1955 Form O', 'Periodic Medical Examination (PME) Audit', 'Labour', 'Quarterly', '2026-10-15', 'Compliant', 10.0, 'P. K. Jena', 'Form_O_Summary_2026.pdf', '1,420 workers screened; 0 cases of pneumoconiosis detected.', now_str, now_str),
                    (5, 'DGMS', 'Mines Act Sec 22', 'Haul Road Slope & Overburden Berm Height Rectification', 'Safety', 'Monthly', '2026-09-05', 'Non-Compliant', 68.0, 'D. K. Yadav', 'DGMS_Inspection_Notice_Aug.pdf', 'Berm height along East Ramp below 3/4 tyre height of 100T dumper. CAPA underway.', now_str, now_str)
                ]
                cur.executemany("""INSERT INTO statutory_compliance (mine_id, regulatory_body, regulation_ref, title, category, frequency, due_date, status, risk_score, responsible_officer, evidence_file, remarks, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", compliances)

                # Seed Field Inspections
                inspections = [
                    (1, 'Inspector Rajesh Kumar (DGMS)', 'Shift A (Morning)', 'Face Bench No. 4 (East Section)', 'Safety', 'Berm height compliance inspection on primary coal haul road', 'Overburden haul road berm height inspected across 2.4 km stretch. Berm height found compliant at 2.6m (> 3/4 wheel height). Mist cannons active.', 'Low', 22.3390, 82.5930, None, None, 98.5, 0, 'Resolved', now_str, now_str),
                    (4, 'Safety Officer B. N. Pandey', 'Shift B (Afternoon)', 'Panel 4 Return Airway (Seam XV)', 'Ventilation', 'Carbon monoxide trace and air velocity check', 'CO concentration detected at 11 ppm during mid-shift walk-through. Suspected minor oxidation in old goaf seal #12. Immediate nitrogen foam injection ordered.', 'Critical', 23.7435, 86.3460, None, None, 96.0, 0, 'CAPA Assigned', now_str, now_str),
                    (2, 'Colliery Engineer A. K. Sharma', 'Shift C (Night)', 'Overburden Dump #2 (South)', 'Operations', 'Continuous Slope Stability Radar Check', 'Minor crest displacement of 3.4 mm recorded after heavy rainfall. Slope drainage channels cleared to prevent water saturation.', 'Medium', 22.3175, 82.5515, None, None, 94.0, 0, 'Open', now_str, now_str),
                    (5, 'DGMS Area Inspector V. Verma', 'Shift A (Morning)', 'East Ramp Haul Road', 'Equipment', 'HEMM Dumper blind-spot mirror and proximity sensor test', '3 out of 12 dumpers in Contractor fleet lacked operational audio-visual proximity radar. Work halted on East Ramp until certified.', 'High', 23.7510, 85.0515, None, None, 99.0, 0, 'Under Investigation', now_str, now_str)
                ]
                cur.executemany("""INSERT INTO field_inspections (mine_id, inspector_name, shift, location_pit_seam, violation_category, violation_title, description, risk_level, latitude, longitude, audio_attachment, photo_attachment, authenticity_score, is_offline_synced, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", inspections)

                # Seed CAPA Actions
                capas = [
                    (2, 4, 'Isolation stopping re-sealing & continuous N2 flushing in Panel 4', 'Atmospheric leakage through cracked masonry stopping #12', 'Re-plaster with fire-resistant sealant and inject inert nitrogen gas at 500 m3/hr.', 'Install automatic continuous CO/O2 telemetry sensors with SCADA alarm integration.', 'Er. Alok Ranjan (Ventilation)', '2026-08-28', '2026-08-27', 'N2_Flushing_Pressure_Log.pdf', 'Colliery Safety Officer Pandey', 'Verification Required', now_str, now_str),
                    (4, 5, 'Retrofit audio-visual proximity radar on all 12 contractor dumpers', 'Contractor maintenance lapse during fleet mobilization', 'Ground non-compliant dumpers immediately; fit DGMS-approved proximity sensors.', 'Mandatory pre-shift checklist sign-off by Electrical Supervisor before gate pass issuance.', 'Er. M. K. Chari (Excavation)', '2026-09-02', None, None, None, 'In Progress', now_str, now_str)
                ]
                cur.executemany("""INSERT INTO capa_actions (inspection_id, mine_id, title, root_cause, corrective_action, preventive_action, assigned_engineer, target_date, completion_date, verification_evidence, sign_off_by, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", capas)

                # Seed Contractors
                contractors = [
                    ('M/s Bharat Earthmovers & Mining Infra Ltd.', 'DGMS/CONTR/2024/7821', 'SECL', 1, 'Ramesh Jaiswal', '+91-9876543210', 320, 4.8, 96.5, 1, 98.0, 100.0, '2028-03-31', now_str),
                    ('Eastern Coal Haulers & Logistics Pvt. Ltd.', 'DGMS/CONTR/2023/4512', 'MCL', 3, 'Debabrata Das', '+91-9876543211', 180, 4.4, 91.0, 1, 92.5, 94.0, '2027-06-30', now_str),
                    ('Shree Ganesh Excavation & Mining Co.', 'DGMS/CONTR/2022/1908', 'CCL', 5, 'Ajit Agarwal', '+91-9876543212', 140, 3.8, 79.5, 1, 81.0, 85.0, '2026-12-31', now_str),
                    ('Deccan Underground Drilling & Blasting Consortium', 'DGMS/CONTR/2024/8910', 'BCCL', 4, 'K. V. Subbarao', '+91-9876543213', 210, 4.6, 94.0, 1, 95.0, 97.5, '2027-11-30', now_str)
                ]
                cur.executemany("""INSERT INTO contractors (company_name, license_no, subsidiary, mine_id, contact_person, contact_phone, active_workers, safety_rating, compliance_score, pf_esi_compliant, vtc_training_pct, form_o_medical_pct, license_expiry, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", contractors)

                # Seed Telemetry
                telemetry = [
                    (1, 'Face Bench No. 4 (East)', 0.08, 2.1, 78.5, 34.2, 72000.0, 27.8, 0.8, 7.3, 'Normal', now_str),
                    (2, 'South Pit Main Sump', 0.12, 3.0, 84.0, 39.0, 68000.0, 28.5, 1.4, 7.1, 'Normal', now_str),
                    (4, 'Panel 4 Return Airway (Seam XV)', 0.42, 11.8, 120.0, 55.0, 34000.0, 31.2, 0.2, 6.8, 'Critical', now_str),
                    (3, 'Coal Handling Plant (CHP) Transfer Point', 0.05, 1.8, 210.0, 95.0, 65000.0, 29.0, 0.5, 7.0, 'Warning', now_str),
                    (5, 'Overburden Dump West Flank', 0.02, 1.2, 65.0, 28.0, 80000.0, 26.5, 4.8, 7.4, 'Warning', now_str)
                ]
                cur.executemany("""INSERT INTO mine_telemetry (mine_id, zone_name, ch4_percent, co_ppm, dust_pm10, dust_pm25, airflow_cfm, temperature_c, slope_displacement_mm, water_ph, alert_level, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", telemetry)

                # Seed Genesis Block in Audit Ledger
                genesis_entry = CryptoAuditLedger.create_audit_entry(
                    previous_hash=CryptoAuditLedger.GENESIS_HASH,
                    block_index=1,
                    actor_id="SYS_INIT",
                    actor_name="National Coal Mine Governance Gateway",
                    action_type="GENESIS_INITIALIZATION",
                    entity_affected="MineGuard Compliance Command Platform",
                    details="Cryptographic SHA-256 genesis anchor initialized for Coal India & Subsidiaries statutory compliance ledger.",
                    payload={"platform": "MineGuard CoalGov v2.5", "framework": "DGMS & MoEFCC Certified"}
                )
                cur.execute("""INSERT INTO audit_ledger (block_index, previous_hash, current_hash, timestamp, actor_id, actor_name, action_type, entity_affected, details, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    genesis_entry['block_index'], genesis_entry['previous_hash'], genesis_entry['current_hash'],
                    genesis_entry['timestamp'], genesis_entry['actor_id'], genesis_entry['actor_name'],
                    genesis_entry['action_type'], genesis_entry['entity_affected'], genesis_entry['details'], genesis_entry['payload_json']
                ))

                conn.commit()
                logger.info("✅ Coal Mining Governance tables and seed data created successfully.")
        except Exception as seed_err:
            logger.warning(f"Seed data insertion skipped or already populated: {seed_err}")

        logger.info("✅ SQLite database initialized.")
        return

    # Create indexes
    logger.info("Initializing database indexes...")
    index_configs = [
        (db.users, 'email', {'unique': True}),
        (db.users, 'username', {}),
        (db.complaints, 'user_id', {}),
        (db.complaints, 'category', {}),
        (db.complaints, 'status', {}),
        (db.complaints, 'ref_no', {'unique': True, 'sparse': True}),
        (db.complaints, 'city', {}),
        (db.complaints, 'priority', {}),
        (db.complaints, [('user_id', ASCENDING), ('status', ASCENDING)], {}),
        (db.complaints, 'created_at', {}),
        (db.workers, 'is_active', {}),
        (db.workers, 'skill', {}),
        (db.notifications, 'user_id', {}),
        (db.notifications, 'created_at', {}),
        (db.notifications, [('user_id', ASCENDING), ('is_read', ASCENDING)], {}),
        (db.chat_history, 'session_id', {}),
        (db.chat_sessions, 'session_id', {'unique': True}),
        (db.audit_logs, 'user_id', {}),
        (db.user_locations, [('user_id', ASCENDING), ('created_at', DESCENDING)], {})
    ]

    # Pre-cleanup for unique indexes: chat_sessions
    try:
        # Check for duplicates in chat_sessions and remove them
        # (Useful when migrating or if previous failed logic created duplicates)
        pipeline = [
            {"$group": {"_id": "$session_id", "count": {"$sum": 1}, "ids": {"$push": "$_id"}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        dupes = list(db.chat_sessions.aggregate(pipeline))
        for dupe in dupes:
            # Keep only the latest entry (the one with the highest _id or last in the list)
            to_delete = dupe['ids'][:-1]
            db.chat_sessions.delete_many({"_id": {"$in": to_delete}})
            logger.info(f"Cleaned up {len(to_delete)} duplicate chat sessions for {dupe['_id']}")
    except Exception as e:
        logger.warning(f"Pre-indexing cleanup skipped: {e}")

    for collection, keys, options in index_configs:
        try:
            collection.create_index(keys, **options)
        except Exception as e:
            # Handle IndexKeySpecsConflict (code 86) or IndexOptionsConflict (code 85)
            error_code = getattr(e, 'code', None)
            if error_code in (85, 86):
                try:
                    logger.warning(f"Index conflict on {collection.name} for {keys}. Recreating...")
                    # If keys is a string like 'email', drop_index(keys) looks for index named 'email'.
                    # We need to pass the spec list [('email', 1)] or the name 'email_1'.
                    if isinstance(keys, str):
                        collection.drop_index([(keys, ASCENDING)])
                    else:
                        collection.drop_index(keys)
                    collection.create_index(keys, **options)
                except Exception as inner_e:
                    logger.error(f"Could not resolve index conflict for {keys}: {inner_e}")
            else:
                logger.warning(f"Could not create index {keys} on {collection.name}: {e}")

    logger.info("✅ Database indexes setup complete.")
    
    # Seed default demo users
    demo_accounts = [
        ('admin', 'admin@mineguard.gov.in', 'admin123', True, 'Admin', 'Coal India HQ'),
        ('manager', 'manager@mineguard.gov.in', 'manager123', True, 'Mine Manager', 'SECL'),
        ('safety', 'safety@mineguard.gov.in', 'safety123', True, 'Safety Officer', 'SECL'),
        ('inspector', 'inspector@dgms.gov.in', 'inspector123', True, 'Inspector', 'DGMS'),
        ('worker', 'worker@mineguard.gov.in', 'worker123', False, 'Worker', 'SECL'),
    ]
    for uname, uemail, upass, is_adm, urole, usub in demo_accounts:
        existing_user = db.users.find_one({'$or': [{'username': uname}, {'email': uemail}]})
        if not existing_user:
            u_id = _next_id('users')
            u_pw = generate_password_hash(upass, method='pbkdf2:sha256')
            db.users.insert_one({
                'id': u_id,
                'username': uname,
                'email': uemail,
                'password': u_pw,
                'is_admin': is_adm,
                'role': urole,
                'subsidiary': usub,
                'tracking_consent': False,
                'created_at': datetime.now()
            })
            logger.info(f"✅ Demo user {uname} ({urole}) created")
    
    # Seed workers
    if db.workers.count_documents({}) == 0:
        initial_workers = [
            ('Amit Sharma', 'Road & Infrastructure', 'Zone 1 (PWD)', 28.6139, 77.2090, 0, 45.0, 4.5, '011-2345678'),
            ('Sanjay Verma', 'Waste Management', 'Municipal Ward 5', 28.6150, 77.2100, 0, 30.0, 4.8, '011-2345679'),
            ('Rajesh Gupta', 'Electricity & Street Lighting', 'North Zone (Discom)', 28.6120, 77.2080, 0, 60.0, 4.2, '011-2345680'),
            ('Meera Nair', 'Water & Sanitation', 'District Water Board', 28.6145, 77.2110, 0, 20.0, 4.9, '011-2345681'),
            ('Inspector Vijay', 'Public Safety', 'Central District Police', 28.6100, 77.2000, 0, 15.0, 4.7, '100'),
            ('Dr. Sunita', 'Environmental Issues', 'State Pollution Control', 28.6200, 77.2200, 0, 50.0, 4.4, '011-2345682'),
            ('Dr. Kapoor', 'Health Services', 'Civic Hospital Admin', 28.6250, 77.2300, 0, 25.0, 4.6, '011-2345683'),
            ('Arun Singh', 'Government Service Delays', 'E-Governance Dept', 28.6300, 77.2400, 0, 40.0, 4.3, '011-2345684')
        ]
        for name, skill, zone, lat, lon, load, avg_time, rating, contact in initial_workers:
            worker_id = _next_id('workers')
            db.workers.insert_one({
                'id': worker_id,
                'name': name,
                'skill': skill,
                'location_zone': zone,
                'latitude': lat,
                'longitude': lon,
                'current_load': load,
                'avg_resolution_time': avg_time,
                'performance_rating': rating,
                'contact': contact,
                'is_active': True,
                'created_at': datetime.now()
            })
        logger.info("✅ Initial workers seeded")
    
    logger.info("✅ MongoDB initialization complete")
