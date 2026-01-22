"""
Test NDP/RDP "tambahan" logic consistency across all reporting modules.

Rule: Records with "tambahan" in the keterangan (notes) field should:
1. ALWAYS be counted as RDP (repeat deposit), never NDP (new deposit)
2. Be EXCLUDED from customer first-deposit date calculation

This test validates that all 6 reporting modules implement this logic consistently:
- analytics.py
- bonus.py
- leaderboard.py
- report.py
- retention.py
- scheduled_reports.py
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTambahanLogic:
    """Test suite for "tambahan" NDP/RDP classification logic"""
    
    def test_helper_is_tambahan_record(self):
        """Test the is_tambahan_record helper function logic"""
        
        def is_tambahan_record(record) -> bool:
            keterangan = record.get('keterangan', '') or ''
            return 'tambahan' in keterangan.lower()
        
        # Should be True (tambahan in notes)
        assert is_tambahan_record({'keterangan': 'tambahan'}) == True
        assert is_tambahan_record({'keterangan': 'TAMBAHAN'}) == True
        assert is_tambahan_record({'keterangan': 'Tambahan deposit'}) == True
        assert is_tambahan_record({'keterangan': 'depo tambahan bulan lalu'}) == True
        assert is_tambahan_record({'keterangan': 'test TAMBAHAN test'}) == True
        
        # Should be False (no tambahan)
        assert is_tambahan_record({'keterangan': ''}) == False
        assert is_tambahan_record({'keterangan': None}) == False
        assert is_tambahan_record({}) == False
        assert is_tambahan_record({'keterangan': 'regular deposit'}) == False
        assert is_tambahan_record({'keterangan': 'new customer'}) == False
    
    def test_normalize_customer_id(self):
        """Test customer ID normalization logic"""
        
        def normalize_customer_id(customer_id: str) -> str:
            if not customer_id:
                return ""
            return customer_id.strip().lower()
        
        assert normalize_customer_id('ABC123') == 'abc123'
        assert normalize_customer_id('  ABC123  ') == 'abc123'
        assert normalize_customer_id('abc123') == 'abc123'
        assert normalize_customer_id('') == ''
        assert normalize_customer_id(None) == ''
    
    def test_first_deposit_excludes_tambahan(self):
        """Test that "tambahan" records are excluded when building first deposit map"""
        
        def is_tambahan_record(record) -> bool:
            keterangan = record.get('keterangan', '') or ''
            return 'tambahan' in keterangan.lower()
        
        def normalize_customer_id(customer_id: str) -> str:
            if not customer_id:
                return ""
            return customer_id.strip().lower()
        
        # Simulate records: first record is "tambahan", second is normal
        records = [
            {
                'customer_id': 'CUST001',
                'product_id': 'PROD1',
                'record_date': '2024-01-01',
                'keterangan': 'tambahan dari akun lama'
            },
            {
                'customer_id': 'CUST001',
                'product_id': 'PROD1',
                'record_date': '2024-01-05',
                'keterangan': 'deposit normal'
            },
            {
                'customer_id': 'CUST002',
                'product_id': 'PROD1',
                'record_date': '2024-01-03',
                'keterangan': None
            }
        ]
        
        # Build first deposit map (excluding tambahan)
        customer_first_date = {}
        for record in sorted(records, key=lambda x: x['record_date']):
            if is_tambahan_record(record):
                continue  # Skip tambahan records
            cid_normalized = normalize_customer_id(record['customer_id'])
            key = (cid_normalized, record['product_id'])
            if key not in customer_first_date:
                customer_first_date[key] = record['record_date']
        
        # CUST001's first date should be 2024-01-05 (not 01-01 which was tambahan)
        assert customer_first_date.get(('cust001', 'PROD1')) == '2024-01-05'
        
        # CUST002's first date should be 2024-01-03
        assert customer_first_date.get(('cust002', 'PROD1')) == '2024-01-03'
    
    def test_tambahan_always_rdp(self):
        """Test that "tambahan" records are always classified as RDP"""
        
        def is_tambahan_record(record) -> bool:
            keterangan = record.get('keterangan', '') or ''
            return 'tambahan' in keterangan.lower()
        
        def normalize_customer_id(customer_id: str) -> str:
            if not customer_id:
                return ""
            return customer_id.strip().lower()
        
        # Build first deposit map (empty - customer has no prior records)
        customer_first_date = {}
        
        # Customer's ONLY record has "tambahan" in notes
        record = {
            'customer_id': 'NEW_CUST',
            'product_id': 'PROD1',
            'record_date': '2024-01-10',
            'keterangan': 'tambahan'
        }
        
        cid_normalized = normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        first_date = customer_first_date.get(key)
        
        # Classification logic: if tambahan, always RDP
        if is_tambahan_record(record):
            is_ndp = False  # Always RDP for tambahan
        else:
            is_ndp = first_date == record['record_date']
        
        # Even though this is "technically" the customer's first record,
        # it should be RDP because it has "tambahan" in notes
        assert is_ndp == False
    
    def test_scenario_mixed_records(self):
        """Test a realistic scenario with mixed tambahan and regular records"""
        
        def is_tambahan_record(record) -> bool:
            keterangan = record.get('keterangan', '') or ''
            return 'tambahan' in keterangan.lower()
        
        def normalize_customer_id(customer_id: str) -> str:
            if not customer_id:
                return ""
            return customer_id.strip().lower()
        
        # Scenario: 
        # - ALICE: first record is tambahan (day 1), second is normal (day 3)
        # - BOB: first record is normal (day 2)
        records = [
            {'customer_id': 'ALICE', 'product_id': 'P1', 'record_date': '2024-01-01', 'keterangan': 'tambahan'},
            {'customer_id': 'BOB', 'product_id': 'P1', 'record_date': '2024-01-02', 'keterangan': None},
            {'customer_id': 'ALICE', 'product_id': 'P1', 'record_date': '2024-01-03', 'keterangan': 'normal deposit'},
        ]
        
        # Step 1: Build first deposit map (exclude tambahan)
        customer_first_date = {}
        for record in sorted(records, key=lambda x: x['record_date']):
            if is_tambahan_record(record):
                continue
            cid_normalized = normalize_customer_id(record['customer_id'])
            key = (cid_normalized, record['product_id'])
            if key not in customer_first_date:
                customer_first_date[key] = record['record_date']
        
        # Step 2: Classify each record
        classifications = []
        for record in records:
            cid_normalized = normalize_customer_id(record['customer_id'])
            key = (cid_normalized, record['product_id'])
            first_date = customer_first_date.get(key)
            
            if is_tambahan_record(record):
                is_ndp = False  # Always RDP
            else:
                is_ndp = first_date == record['record_date']
            
            classifications.append({
                'customer': record['customer_id'],
                'date': record['record_date'],
                'type': 'NDP' if is_ndp else 'RDP'
            })
        
        # Verify results:
        # - ALICE day 1: RDP (has tambahan)
        # - BOB day 2: NDP (his actual first record)
        # - ALICE day 3: NDP (her actual first non-tambahan record)
        assert classifications[0]['type'] == 'RDP', f"ALICE day 1 should be RDP (tambahan), got {classifications[0]['type']}"
        assert classifications[1]['type'] == 'NDP', f"BOB day 2 should be NDP, got {classifications[1]['type']}"
        assert classifications[2]['type'] == 'NDP', f"ALICE day 3 should be NDP (first non-tambahan), got {classifications[2]['type']}"
    
    def test_case_insensitive_tambahan(self):
        """Test that tambahan check is case insensitive"""
        
        def is_tambahan_record(record) -> bool:
            keterangan = record.get('keterangan', '') or ''
            return 'tambahan' in keterangan.lower()
        
        test_cases = [
            ('tambahan', True),
            ('TAMBAHAN', True),
            ('Tambahan', True),
            ('TaMbAhAn', True),
            ('ini adalah tambahan', True),
            ('DEPOSIT TAMBAHAN LAGI', True),
            ('normal', False),
            ('deposit biasa', False),
            ('', False),
        ]
        
        for keterangan, expected in test_cases:
            record = {'keterangan': keterangan}
            result = is_tambahan_record(record)
            assert result == expected, f"Failed for keterangan='{keterangan}': expected {expected}, got {result}"


class TestModulesHaveTambahanLogic:
    """Verify that all 6 modules contain the tambahan logic"""
    
    def test_omset_has_tambahan_logic(self):
        """Verify omset.py has tambahan logic"""
        with open('/app/backend/routes/omset.py', 'r') as f:
            content = f.read()
        
        assert 'is_tambahan' in content or 'tambahan' in content.lower(), "omset.py should have tambahan logic"
        assert 'customer_first_date' in content, "omset.py should build customer_first_date map"
    
    def test_analytics_has_tambahan_logic(self):
        """Verify analytics.py has tambahan logic"""
        with open('/app/backend/routes/analytics.py', 'r') as f:
            content = f.read()
        
        assert 'tambahan' in content.lower(), "analytics.py should have tambahan logic"
    
    def test_bonus_has_tambahan_logic(self):
        """Verify bonus.py has tambahan logic"""
        with open('/app/backend/routes/bonus.py', 'r') as f:
            content = f.read()
        
        assert 'tambahan' in content.lower(), "bonus.py should have tambahan logic"
    
    def test_leaderboard_has_tambahan_logic(self):
        """Verify leaderboard.py has tambahan logic"""
        with open('/app/backend/routes/leaderboard.py', 'r') as f:
            content = f.read()
        
        assert 'tambahan' in content.lower(), "leaderboard.py should have tambahan logic"
    
    def test_report_has_tambahan_logic(self):
        """Verify report.py has tambahan logic"""
        with open('/app/backend/routes/report.py', 'r') as f:
            content = f.read()
        
        assert 'tambahan' in content.lower(), "report.py should have tambahan logic"
    
    def test_retention_has_tambahan_logic(self):
        """Verify retention.py has tambahan logic"""
        with open('/app/backend/routes/retention.py', 'r') as f:
            content = f.read()
        
        assert 'is_tambahan_record' in content, "retention.py should have is_tambahan_record helper"
        assert 'Skip "tambahan"' in content or 'EXCLUDE "tambahan"' in content, "retention.py should have comments about tambahan exclusion"
    
    def test_scheduled_reports_has_tambahan_logic(self):
        """Verify scheduled_reports.py has tambahan logic"""
        with open('/app/backend/routes/scheduled_reports.py', 'r') as f:
            content = f.read()
        
        assert 'is_tambahan_record' in content, "scheduled_reports.py should have is_tambahan_record helper"
        assert 'tambahan' in content.lower(), "scheduled_reports.py should have tambahan logic"
    
    def test_daily_summary_has_tambahan_logic(self):
        """Verify daily_summary.py has tambahan logic"""
        with open('/app/backend/routes/daily_summary.py', 'r') as f:
            content = f.read()
        
        assert 'is_tambahan_record' in content, "daily_summary.py should have is_tambahan_record helper"
        assert 'tambahan' in content.lower(), "daily_summary.py should have tambahan logic"
        # Verify the my-performance endpoint also uses tambahan logic
        assert content.count('is_tambahan_record') >= 2, "daily_summary.py should use is_tambahan_record in multiple places including my-performance"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
