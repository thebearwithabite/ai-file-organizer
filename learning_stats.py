#!/usr/bin/env python3
"""
Learning Statistics and Progress Tracking for AI File Organizer
Tracks classification accuracy, user corrections, and system improvement over time
Based on AudioAI learning patterns but focused on document organization
"""

import sys
import os
import sqlite3
from gdrive_integration import get_metadata_root
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from collections import defaultdict

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interaction_modes import InteractionMode

class LearningStatsTracker:
    """
    Tracks how well the AI classification system is learning and improving
    Like AudioAI but focused on document understanding and organization
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.stats_dir = get_metadata_root() / "learning_stats"
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for learning statistics
        self.db_path = self.stats_dir / "learning_tracking.db"
        self._init_learning_db()
        
        # Load metadata database path
        self.metadata_db = get_metadata_root() / "metadata_tracking.db"
        
        # Category mappings for analysis
        self.category_groups = {
            'Entertainment': ['Contracts', 'Scripts', 'Talent_Management', 'SAG_Documents'],
            'Creative': ['Creative_Writing', 'Research_Papers', 'Podcast_Content', 'AI_Research'],
            'Business': ['Invoices', 'Tax_Documents', 'Commissions', 'Legal_Documents'],
            'Personal': ['Personal_Notes', 'Ideas', 'Todo_Lists', 'Journals'],
            'Technical': ['Code', 'Documentation', 'Configuration', 'Debug_Logs']
        }
    
    def _init_learning_db(self):
        """Initialize SQLite database for learning statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS classification_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    original_category TEXT,
                    corrected_category TEXT,
                    original_confidence REAL,
                    correction_date TEXT,
                    correction_type TEXT,  -- 'user_correction', 'system_update', 'retroactive_fix'
                    interaction_mode TEXT,
                    file_type TEXT,
                    word_count INTEGER,
                    correction_reason TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accuracy_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    total_classifications INTEGER,
                    correct_predictions INTEGER,
                    user_corrections INTEGER,
                    accuracy_rate REAL,
                    average_confidence REAL,
                    interaction_mode TEXT,
                    category_group TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_milestones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    milestone_date TEXT,
                    milestone_type TEXT,  -- 'accuracy_improvement', 'confidence_increase', 'category_mastery'
                    description TEXT,
                    previous_value REAL,
                    new_value REAL,
                    files_processed INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    interaction_mode TEXT,
                    files_processed INTEGER,
                    questions_asked INTEGER,
                    time_spent_minutes REAL,
                    user_satisfaction_rating INTEGER,  -- 1-5 scale
                    most_common_categories TEXT  -- JSON array
                )
            """)
            
            conn.commit()
    
    def record_classification_correction(self, file_path: str, original_category: str, 
                                       corrected_category: str, original_confidence: float,
                                       correction_type: str = "user_correction", 
                                       interaction_mode: str = "smart",
                                       correction_reason: str = ""):
        """Record when a user corrects an AI classification"""
        
        file_path_obj = Path(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO classification_corrections
                (file_path, original_category, corrected_category, original_confidence,
                 correction_date, correction_type, interaction_mode, file_type, correction_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_path, original_category, corrected_category, original_confidence,
                datetime.now().isoformat(), correction_type, interaction_mode,
                file_path_obj.suffix.lower(), correction_reason
            ))
            conn.commit()
        
        # Check for learning milestones
        self._check_learning_milestones()
    
    def calculate_accuracy_metrics(self, days_back: int = 7) -> Dict[str, Any]:
        """Calculate accuracy metrics for recent classifications"""
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        # Get recent classifications from metadata
        with sqlite3.connect(self.metadata_db) as conn:
            df_metadata = pd.read_sql_query("""
                SELECT ai_category, confidence_score, classification_method, 
                       processing_mode, file_type, indexed_date, file_path
                FROM file_metadata
                WHERE indexed_date > ?
                AND ai_category != 'Classification_Failed'
                ORDER BY indexed_date DESC
            """, conn, params=[cutoff_date])
        
        # Get corrections in same period
        with sqlite3.connect(self.db_path) as conn:
            df_corrections = pd.read_sql_query("""
                SELECT file_path, original_category, corrected_category, 
                       original_confidence, correction_date, correction_type
                FROM classification_corrections
                WHERE correction_date > ?
            """, conn, params=[cutoff_date])
        
        if df_metadata.empty:
            return {
                'total_classifications': 0,
                'accuracy_rate': 0.0,
                'average_confidence': 0.0,
                'corrections': 0,
                'period_days': days_back
            }
        
        # Calculate metrics
        total_classifications = len(df_metadata)
        total_corrections = len(df_corrections)
        accuracy_rate = max(0, (total_classifications - total_corrections) / total_classifications) if total_classifications > 0 else 0
        avg_confidence = df_metadata['confidence_score'].mean()
        
        # Break down by category groups
        category_accuracy = {}
        for group_name, categories in self.category_groups.items():
            group_files = df_metadata[df_metadata['ai_category'].isin(categories)]
            if not group_files.empty:
                group_corrections = df_corrections[df_corrections['original_category'].isin(categories)]
                group_accuracy = max(0, (len(group_files) - len(group_corrections)) / len(group_files))
                category_accuracy[group_name] = {
                    'files': len(group_files),
                    'corrections': len(group_corrections),
                    'accuracy': group_accuracy,
                    'avg_confidence': group_files['confidence_score'].mean()
                }
        
        metrics = {
            'total_classifications': total_classifications,
            'accuracy_rate': accuracy_rate,
            'average_confidence': avg_confidence,
            'corrections': total_corrections,
            'period_days': days_back,
            'category_breakdown': category_accuracy,
            'confidence_distribution': {
                'high_90plus': len(df_metadata[df_metadata['confidence_score'] >= 0.9]),
                'medium_70_90': len(df_metadata[(df_metadata['confidence_score'] >= 0.7) & (df_metadata['confidence_score'] < 0.9)]),
                'low_below_70': len(df_metadata[df_metadata['confidence_score'] < 0.7])
            }
        }
        
        # Save to database
        self._save_accuracy_metrics(metrics)
        
        return metrics
    
    def _save_accuracy_metrics(self, metrics: Dict[str, Any]):
        """Save accuracy metrics to database"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO accuracy_metrics
                (date, total_classifications, correct_predictions, user_corrections,
                 accuracy_rate, average_confidence, interaction_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                metrics['total_classifications'],
                metrics['total_classifications'] - metrics['corrections'],
                metrics['corrections'],
                metrics['accuracy_rate'],
                metrics['average_confidence'],
                'mixed'  # Multiple modes in period
            ))
            conn.commit()
    
    def _check_learning_milestones(self):
        """Check if we've hit any learning milestones"""
        
        # Get current accuracy
        current_metrics = self.calculate_accuracy_metrics(days_back=30)
        current_accuracy = current_metrics['accuracy_rate']
        
        # Get previous accuracy from 30 days ago
        with sqlite3.connect(self.db_path) as conn:
            prev_accuracy = conn.execute("""
                SELECT accuracy_rate FROM accuracy_metrics
                WHERE date < datetime('now', '-30 days')
                ORDER BY date DESC LIMIT 1
            """).fetchone()
        
        if prev_accuracy and current_accuracy > prev_accuracy[0] + 0.1:  # 10% improvement
            self._record_milestone(
                'accuracy_improvement',
                f"Accuracy improved from {prev_accuracy[0]:.1%} to {current_accuracy:.1%}",
                prev_accuracy[0], 
                current_accuracy
            )
        
        # Check confidence improvements
        current_confidence = current_metrics['average_confidence']
        with sqlite3.connect(self.db_path) as conn:
            prev_confidence = conn.execute("""
                SELECT average_confidence FROM accuracy_metrics
                WHERE date < datetime('now', '-30 days')
                ORDER BY date DESC LIMIT 1
            """).fetchone()
        
        if prev_confidence and current_confidence > prev_confidence[0] + 0.05:  # 5% confidence boost
            self._record_milestone(
                'confidence_increase',
                f"Average confidence improved from {prev_confidence[0]:.1%} to {current_confidence:.1%}",
                prev_confidence[0],
                current_confidence
            )
    
    def _record_milestone(self, milestone_type: str, description: str, 
                         previous_value: float, new_value: float):
        """Record a learning milestone"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO learning_milestones
                (milestone_date, milestone_type, description, previous_value, new_value)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(), milestone_type, description,
                previous_value, new_value
            ))
            conn.commit()
        
        print(f"🎉 Learning Milestone: {description}")
    
    def generate_learning_report(self) -> str:
        """Generate comprehensive learning progress report"""
        
        print("📊 Generating Learning Progress Report")
        print("=" * 60)
        
        # Get recent metrics
        metrics_7d = self.calculate_accuracy_metrics(7)
        metrics_30d = self.calculate_accuracy_metrics(30)
        
        # Get correction patterns
        correction_patterns = self._analyze_correction_patterns()
        
        # Get usage trends
        usage_trends = self._analyze_usage_trends()
        
        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.stats_dir / f"learning_report_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write("# AI File Organizer - Learning Progress Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Overall Performance
            f.write("## 📈 Overall Performance\n\n")
            f.write("### Last 7 Days\n")
            f.write(f"- **Files Classified:** {metrics_7d['total_classifications']}\n")
            f.write(f"- **Accuracy Rate:** {metrics_7d['accuracy_rate']:.1%}\n")
            f.write(f"- **Average Confidence:** {metrics_7d['average_confidence']:.1%}\n")
            f.write(f"- **User Corrections:** {metrics_7d['corrections']}\n\n")
            
            f.write("### Last 30 Days\n")
            f.write(f"- **Files Classified:** {metrics_30d['total_classifications']}\n")
            f.write(f"- **Accuracy Rate:** {metrics_30d['accuracy_rate']:.1%}\n")
            f.write(f"- **Average Confidence:** {metrics_30d['average_confidence']:.1%}\n")
            f.write(f"- **User Corrections:** {metrics_30d['corrections']}\n\n")
            
            # Category Performance
            f.write("## 🎯 Category Performance\n\n")
            for category, stats in metrics_30d['category_breakdown'].items():
                f.write(f"### {category}\n")
                f.write(f"- Files: {stats['files']}\n")
                f.write(f"- Accuracy: {stats['accuracy']:.1%}\n")
                f.write(f"- Avg Confidence: {stats['avg_confidence']:.1%}\n")
                f.write(f"- Corrections: {stats['corrections']}\n\n")
            
            # Confidence Distribution
            f.write("## 🎯 Confidence Distribution\n\n")
            conf_dist = metrics_30d['confidence_distribution']
            f.write(f"- **High Confidence (90%+):** {conf_dist['high_90plus']} files\n")
            f.write(f"- **Medium Confidence (70-90%):** {conf_dist['medium_70_90']} files\n")
            f.write(f"- **Low Confidence (<70%):** {conf_dist['low_below_70']} files\n\n")
            
            # Correction Patterns
            f.write("## 🔄 Common Correction Patterns\n\n")
            for pattern in correction_patterns['most_common']:
                f.write(f"- **{pattern['from']}** → **{pattern['to']}** ({pattern['count']} times)\n")
            f.write("\n")
            
            # Problem Areas
            f.write("## ⚠️ Areas Needing Attention\n\n")
            for issue in correction_patterns['problem_categories']:
                f.write(f"- **{issue['category']}**: {issue['correction_rate']:.1%} correction rate\n")
            f.write("\n")
            
            # Usage Trends
            f.write("## 📊 Usage Trends\n\n")
            f.write(f"- **Most Used Mode:** {usage_trends['popular_mode']}\n")
            f.write(f"- **Files/Day Average:** {usage_trends['files_per_day']:.1f}\n")
            f.write(f"- **Questions/File Ratio:** {usage_trends['questions_per_file']:.1f}\n\n")
            
            # Recent Milestones
            f.write("## 🏆 Recent Milestones\n\n")
            recent_milestones = self._get_recent_milestones()
            for milestone in recent_milestones:
                f.write(f"- **{milestone['date']}**: {milestone['description']}\n")
            f.write("\n")
            
            # Recommendations
            f.write("## 💡 Recommendations\n\n")
            recommendations = self._generate_recommendations(metrics_30d, correction_patterns)
            for rec in recommendations:
                f.write(f"- {rec}\n")
        
        print(f"✅ Learning report saved: {report_path}")
        return str(report_path)
    
    def _analyze_correction_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in user corrections"""
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("""
                SELECT original_category, corrected_category, correction_date, 
                       file_type, original_confidence, correction_type
                FROM classification_corrections
                WHERE correction_date > datetime('now', '-30 days')
            """, conn)
        
        if df.empty:
            return {'most_common': [], 'problem_categories': []}
        
        # Most common correction patterns
        correction_pairs = df.groupby(['original_category', 'corrected_category']).size().reset_index(name='count')
        most_common = correction_pairs.nlargest(10, 'count').to_dict('records')
        most_common = [{'from': row['original_category'], 'to': row['corrected_category'], 'count': row['count']} for row in most_common]
        
        # Problem categories (high correction rates)
        problem_categories = df.groupby('original_category').agg({
            'corrected_category': 'count',
            'original_confidence': 'mean'
        }).reset_index()
        problem_categories.columns = ['category', 'corrections', 'avg_confidence']
        problem_categories['correction_rate'] = problem_categories['corrections'] / problem_categories['corrections'].sum()
        problem_categories = problem_categories.nlargest(5, 'corrections').to_dict('records')
        
        return {
            'most_common': most_common,
            'problem_categories': problem_categories
        }
    
    def _analyze_usage_trends(self) -> Dict[str, Any]:
        """Analyze usage patterns and trends"""
        
        # Get metadata for usage analysis
        with sqlite3.connect(self.metadata_db) as conn:
            df = pd.read_sql_query("""
                SELECT processing_mode, questions_asked, indexed_date
                FROM file_metadata
                WHERE indexed_date > datetime('now', '-30 days')
            """, conn)
        
        if df.empty:
            return {'popular_mode': 'Unknown', 'files_per_day': 0, 'questions_per_file': 0}
        
        # Most popular interaction mode
        popular_mode = df['processing_mode'].mode().iloc[0] if not df['processing_mode'].mode().empty else 'Smart'
        
        # Files per day
        df['date'] = pd.to_datetime(df['indexed_date']).dt.date
        files_per_day = df.groupby('date').size().mean()
        
        # Questions per file ratio
        questions_per_file = df['questions_asked'].mean()
        
        return {
            'popular_mode': popular_mode,
            'files_per_day': files_per_day,
            'questions_per_file': questions_per_file
        }
    
    def _get_recent_milestones(self) -> List[Dict]:
        """Get recent learning milestones"""
        
        with sqlite3.connect(self.db_path) as conn:
            milestones = pd.read_sql_query("""
                SELECT milestone_date, milestone_type, description
                FROM learning_milestones
                ORDER BY milestone_date DESC
                LIMIT 5
            """, conn)
        
        return [{
            'date': row['milestone_date'][:10], 
            'type': row['milestone_type'],
            'description': row['description']
        } for _, row in milestones.iterrows()]
    
    def _generate_recommendations(self, metrics: Dict, patterns: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        
        recommendations = []
        
        # Accuracy-based recommendations
        if metrics['accuracy_rate'] < 0.8:
            recommendations.append("Consider using 'always' interaction mode to provide more feedback for learning")
        
        # Confidence-based recommendations  
        if metrics['average_confidence'] < 0.7:
            recommendations.append("Focus on improving content extraction quality for better classification confidence")
        
        # Category-specific recommendations
        for category, stats in metrics['category_breakdown'].items():
            if stats['accuracy'] < 0.7:
                recommendations.append(f"Review {category} classification patterns - showing low accuracy")
        
        # Correction pattern recommendations
        if patterns['most_common']:
            top_correction = patterns['most_common'][0]
            recommendations.append(f"Consider updating classification rules: {top_correction['from']} → {top_correction['to']} is most common correction")
        
        return recommendations

def test_learning_stats():
    """Test the learning statistics system"""
    
    print("🧪 Testing Learning Statistics Tracking")
    print("=" * 50)
    
    tracker = LearningStatsTracker()
    
    # Simulate some corrections for testing
    print("📝 Recording sample corrections...")
    
    # Sample corrections that might happen
    test_corrections = [
        ("test_contract.pdf", "Business_Document", "Entertainment_Contract", 0.65, "user_correction"),
        ("script_draft.pdf", "Creative_Writing", "Script", 0.45, "user_correction"),
        ("invoice.pdf", "Personal_Document", "Business_Invoice", 0.78, "user_correction")
    ]
    
    for file_path, orig_cat, correct_cat, confidence, correction_type in test_corrections:
        tracker.record_classification_correction(
            file_path, orig_cat, correct_cat, confidence, correction_type,
            correction_reason="Testing learning system"
        )
        print(f"   ✅ Recorded: {orig_cat} → {correct_cat}")
    
    # Calculate current metrics
    print(f"\n📊 Calculating accuracy metrics...")
    metrics = tracker.calculate_accuracy_metrics(days_back=30)
    
    print(f"   Total classifications: {metrics['total_classifications']}")
    print(f"   Accuracy rate: {metrics['accuracy_rate']:.1%}")
    print(f"   Average confidence: {metrics['average_confidence']:.1%}")
    print(f"   Corrections: {metrics['corrections']}")
    
    # Generate learning report
    print(f"\n📋 Generating learning report...")
    report_path = tracker.generate_learning_report()
    
    if Path(report_path).exists():
        print(f"✅ Learning report generated successfully")
        print(f"📄 Report location: {report_path}")
    else:
        print(f"❌ Failed to generate learning report")

if __name__ == "__main__":
    test_learning_stats()