#!/usr/bin/env python3
"""
Command Line Interface for Learning Statistics
Easy-to-use commands for tracking AI classification improvements
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from learning_stats import LearningStatsTracker

def show_current_stats(days_back: int = 7):
    """Show current classification statistics"""

    print(f"📊 AI Classification Statistics - Last {days_back} Days")
    print("=" * 60)

    tracker = LearningStatsTracker()
    metrics = tracker.calculate_accuracy_metrics(days_back)

    if metrics['total_classifications'] == 0:
        print("❌ No classifications found in this period")
        return

    print(f"📁 Files Classified: {metrics['total_classifications']}")
    print(f"✅ Accuracy Rate: {metrics['accuracy_rate']:.1%}")
    print(f"🎯 Average Confidence: {metrics['average_confidence']:.1%}")
    print(f"🔄 User Corrections: {metrics['corrections']}")

    # Confidence breakdown
    conf_dist = metrics['confidence_distribution']
    print(f"\n📈 Confidence Distribution:")
    print(f"   High (90%+): {conf_dist['high_90plus']} files")
    print(f"   Medium (70-90%): {conf_dist['medium_70_90']} files")
    print(f"   Low (<70%): {conf_dist['low_below_70']} files")

    # Category breakdown
    if metrics['category_breakdown']:
        print(f"\n🎯 Category Performance:")
        for category, stats in metrics['category_breakdown'].items():
            if stats['files'] > 0:
                print(f"   {category}: {stats['accuracy']:.1%} accuracy ({stats['files']} files, {stats['corrections']} corrections)")

    return metrics

def record_correction(file_path: str, original_category: str, corrected_category: str,
                     confidence: float, reason: str = ""):
    """Record a classification correction"""

    print(f"📝 Recording Classification Correction")
    print("=" * 50)

    tracker = LearningStatsTracker()

    try:
        tracker.record_classification_correction(
            file_path, original_category, corrected_category, confidence,
            correction_type="user_correction", correction_reason=reason
        )

        print(f"✅ Correction recorded:")
        print(f"   File: {Path(file_path).name}")
        print(f"   {original_category} → {corrected_category}")
        print(f"   Original confidence: {confidence:.1%}")
        if reason:
            print(f"   Reason: {reason}")

    except Exception as e:
        print(f"❌ Error recording correction: {e}")

def generate_report():
    """Generate comprehensive learning report"""

    print("📋 Generating Comprehensive Learning Report")
    print("=" * 60)

    tracker = LearningStatsTracker()

    try:
        report_path = tracker.generate_learning_report()

        if Path(report_path).exists():
            print(f"✅ Report generated: {Path(report_path).name}")

            # Show quick summary
            print(f"\n📊 Quick Summary:")
            metrics_7d = tracker.calculate_accuracy_metrics(7)
            metrics_30d = tracker.calculate_accuracy_metrics(30)

            print(f"   Last 7 days: {metrics_7d['accuracy_rate']:.1%} accuracy ({metrics_7d['total_classifications']} files)")
            print(f"   Last 30 days: {metrics_30d['accuracy_rate']:.1%} accuracy ({metrics_30d['total_classifications']} files)")

            return report_path
        else:
            print(f"❌ Failed to generate report")
            return None

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return None

def show_correction_patterns():
    """Show common correction patterns"""

    print("🔄 Classification Correction Patterns")
    print("=" * 50)

    tracker = LearningStatsTracker()
    patterns = tracker._analyze_correction_patterns()

    if not patterns['most_common']:
        print("❌ No correction patterns found")
        return

    print("📊 Most Common Corrections:")
    for i, pattern in enumerate(patterns['most_common'][:10], 1):
        print(f"   {i}. {pattern['from']} → {pattern['to']} ({pattern['count']} times)")

    if patterns['problem_categories']:
        print(f"\n⚠️  Categories Needing Attention:")
        for category in patterns['problem_categories'][:5]:
            print(f"   {category['category']}: {category['correction_rate']:.1%} correction rate")

def show_milestones():
    """Show recent learning milestones"""

    print("🏆 Recent Learning Milestones")
    print("=" * 40)

    tracker = LearningStatsTracker()
    milestones = tracker._get_recent_milestones()

    if not milestones:
        print("❌ No milestones recorded yet")
        return

    for milestone in milestones:
        print(f"📅 {milestone['date']}: {milestone['description']}")

def compare_periods():
    """Compare learning performance across different time periods"""

    print("📈 Learning Performance Comparison")
    print("=" * 50)

    tracker = LearningStatsTracker()

    # Get metrics for different periods
    periods = [7, 14, 30]
    period_data = {}

    for days in periods:
        metrics = tracker.calculate_accuracy_metrics(days)
        period_data[days] = metrics

        print(f"\n📊 Last {days} Days:")
        print(f"   Files: {metrics['total_classifications']}")
        print(f"   Accuracy: {metrics['accuracy_rate']:.1%}")
        print(f"   Confidence: {metrics['average_confidence']:.1%}")
        print(f"   Corrections: {metrics['corrections']}")

    # Show trends
    if len(period_data) >= 2:
        print(f"\n📈 Trends:")

        # Compare 7-day vs 30-day
        recent = period_data[7]
        older = period_data[30]

        if recent['total_classifications'] > 0 and older['total_classifications'] > 0:
            acc_change = recent['accuracy_rate'] - older['accuracy_rate']
            conf_change = recent['average_confidence'] - older['average_confidence']

            if acc_change > 0:
                print(f"   ✅ Accuracy improving: +{acc_change:.1%}")
            elif acc_change < 0:
                print(f"   ⚠️  Accuracy declining: {acc_change:.1%}")
            else:
                print(f"   ➡️  Accuracy stable")

            if conf_change > 0:
                print(f"   ✅ Confidence improving: +{conf_change:.1%}")
            elif conf_change < 0:
                print(f"   ⚠️  Confidence declining: {conf_change:.1%}")
            else:
                print(f"   ➡️  Confidence stable")

def main():
    """Command line interface for learning statistics"""

    parser = argparse.ArgumentParser(
        description="AI File Organizer - Learning Statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  learning_cli.py stats --days 7           # Show 7-day statistics
  learning_cli.py stats --days 30          # Show 30-day statistics
  learning_cli.py report                   # Generate full report
  learning_cli.py patterns                 # Show correction patterns
  learning_cli.py milestones              # Show recent milestones
  learning_cli.py compare                 # Compare different periods
  learning_cli.py correct file.pdf Original_Cat Correct_Cat 0.75 "reason"
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show current statistics')
    stats_parser.add_argument('--days', type=int, default=7,
                             help='Number of days to analyze (default: 7)')

    # Report generation command
    subparsers.add_parser('report', help='Generate comprehensive learning report')

    # Correction recording command
    correct_parser = subparsers.add_parser('correct', help='Record a classification correction')
    correct_parser.add_argument('file_path', help='Path to corrected file')
    correct_parser.add_argument('original_category', help='Original AI classification')
    correct_parser.add_argument('corrected_category', help='Correct classification')
    correct_parser.add_argument('confidence', type=float, help='Original confidence score (0.0-1.0)')
    correct_parser.add_argument('reason', nargs='?', default='', help='Reason for correction')

    # Pattern analysis command
    subparsers.add_parser('patterns', help='Show correction patterns')

    # Milestones command
    subparsers.add_parser('milestones', help='Show recent learning milestones')

    # Comparison command
    subparsers.add_parser('compare', help='Compare performance across time periods')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    print("🧠 AI File Organizer - Learning Statistics")
    print("=" * 60)

    if args.command == 'stats':
        show_current_stats(args.days)

    elif args.command == 'report':
        generate_report()

    elif args.command == 'correct':
        record_correction(args.file_path, args.original_category,
                         args.corrected_category, args.confidence, args.reason)

    elif args.command == 'patterns':
        show_correction_patterns()

    elif args.command == 'milestones':
        show_milestones()

    elif args.command == 'compare':
        compare_periods()

if __name__ == "__main__":
    main()