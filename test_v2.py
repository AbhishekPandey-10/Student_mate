import unittest
from unittest.mock import MagicMock, patch
import datetime
from scheduler import calculate_next_review, mark_done, create_subject_plan
from storage import init_db, add_subject

class TestStudyAgentV2(unittest.TestCase):

    def test_sm2_algorithm(self):
        # Test Case 1: First review, rating 5 (Perfect)
        # Interval 0 -> 1
        interval, ef = calculate_next_review(0, 2.5, 5)
        self.assertEqual(interval, 1)
        self.assertGreater(ef, 2.5) # EF should increase

        # Test Case 2: Second review, rating 4 (Good)
        # Interval 1 -> 6
        interval, ef = calculate_next_review(1, 2.6, 4)
        self.assertEqual(interval, 6)
        
        # Test Case 3: Third review, rating 3 (Hard)
        # Interval 6 -> 6 * EF
        interval, ef = calculate_next_review(6, 2.5, 3)
        self.assertEqual(interval, 15) # 6 * 2.5 = 15
        self.assertLess(ef, 2.5) # EF should decrease

        # Test Case 4: Fail (Rating < 3)
        interval, ef = calculate_next_review(100, 2.5, 1)
        self.assertEqual(interval, 1) # Reset to 1
        self.assertEqual(ef, 2.5) # EF unchanged on fail

    @patch('storage.mysql.connector.connect')
    def test_init_db(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        init_db()
        
        # Verify table creation queries were executed
        self.assertTrue(mock_cursor.execute.called)
        calls = [args[0] for args, _ in mock_cursor.execute.call_args_list]
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS subjects" in c for c in calls))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS topics" in c for c in calls))

    @patch('storage.get_connection')
    def test_add_subject(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 123
        
        sub_id = add_subject("Math", "2025-01-01")
        
        self.assertEqual(sub_id, 123)
        mock_cursor.execute.assert_called_with(
            "INSERT INTO subjects (name, exam_date) VALUES (%s, %s)", 
            ("Math", "2025-01-01")
        )

    @patch('scheduler.update_topic_review_data')
    @patch('scheduler.update_topic_status')
    def test_mark_done_flow(self, mock_update_status, mock_update_review):
        # Simulate marking a topic done with rating 5
        mark_done(topic_id=1, rating=5, current_interval=1, current_ease_factor=2.5)
        
        # Should update status to 'done'
        mock_update_status.assert_called_with(1, 'done')
        
        # Should schedule next review
        # Interval 1 -> 6
        mock_update_review.assert_called()
        args = mock_update_review.call_args[0]
        # args: topic_id, repetition_count, ease_factor, interval, next_date
        self.assertEqual(args[0], 1) # topic_id
        self.assertEqual(args[3], 6) # interval

if __name__ == '__main__':
    unittest.main()
