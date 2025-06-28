"""
Script to directly check the SQLite database for PPM data.
"""
import sqlite3
from pathlib import Path

def check_database():
    """Check the SQLite database directly."""
    db_path = Path('instance/app.db')
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nTables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Check if ppm_equipment table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ppm_equipment';
        """)
        if not cursor.fetchone():
            print("\nppm_equipment table not found in database!")
            return
        
        # Get column info for ppm_equipment
        cursor.execute("PRAGMA table_info(ppm_equipment);")
        columns = cursor.fetchall()
        print("\nColumns in ppm_equipment:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        # Get sample data
        print("\nSample data from ppm_equipment (first 5 records):")
        cursor.execute("""
            SELECT id, serial, department, 
                   ppm_q1_engineer, ppm_q1_date, ppm_q1_status,
                   ppm_q2_engineer, ppm_q2_date, ppm_q2_status
            FROM ppm_equipment 
            LIMIT 5;
        """)
        
        # Print column headers
        column_names = [description[0] for description in cursor.description]
        print("\n" + " | ".join(column_names))
        print("-" * 100)
        
        # Print rows
        for row in cursor.fetchall():
            print(" | ".join(str(value) if value is not None else "NULL" for value in row))
        
        # Count records with quarterly data
        cursor.execute("""
            SELECT COUNT(*) FROM ppm_equipment 
            WHERE ppm_q1_engineer IS NOT NULL 
               OR ppm_q1_date IS NOT NULL 
               OR ppm_q1_status IS NOT NULL
               OR ppm_q2_engineer IS NOT NULL
               OR ppm_q2_date IS NOT NULL
               OR ppm_q2_status IS NOT NULL
               OR ppm_q3_engineer IS NOT NULL
               OR ppm_q3_date IS NOT NULL
               OR ppm_q3_status IS NOT NULL
               OR ppm_q4_engineer IS NOT NULL
               OR ppm_q4_date IS NOT NULL
               OR ppm_q4_status IS NOT NULL;
        """)
        with_data = cursor.fetchone()[0]
        
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM ppm_equipment;")
        total = cursor.fetchone()[0]
        
        print(f"\nTotal records: {total}")
        print(f"Records with quarterly data: {with_data} ({with_data/max(1, total)*100:.1f}%)")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("DATABASE DIRECT CHECK")
    print("="*80)
    check_database()
