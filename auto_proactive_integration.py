#!/usr/bin/env python3
"""
Automatic Proactive Learning Integration
Hooks into the existing workflow to trigger proactive learning automatically
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from gdrive_integration import get_metadata_root

from proactive_learning_engine import ProactiveLearningEngine

class AutoProactiveIntegration:
    """
    Automatic integration that triggers proactive learning at appropriate times
    Designed to be ADHD-friendly with minimal disruption
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        
        # Integration settings
        self.integration_dir = get_metadata_root() / "auto_proactive"
        self.integration_dir.mkdir(parents=True, exist_ok=True)
        
        self.settings_file = self.integration_dir / "integration_settings.json"
        self.last_run_file = self.integration_dir / "last_proactive_run.json"
        
        # Load or create settings
        self.settings = self._load_settings()
        
        # Initialize proactive engine
        self.proactive_engine = None
        
    def _load_settings(self) -> dict:
        """Load integration settings"""
        
        default_settings = {
            'enabled': True,
            'trigger_conditions': {
                'min_files_organized_since_last_run': 10,
                'min_days_since_last_run': 3,
                'min_corrections_since_last_run': 2,
                'trigger_on_folder_overflow': True,
                'overflow_threshold': 15
            },
            'auto_implementation': {
                'enabled': False,  # Conservative default
                'min_confidence_for_auto': 0.9,
                'max_auto_folders_per_day': 2,
                'require_user_approval_for_major_changes': True
            },
            'adhd_settings': {
                'show_notifications': True,
                'batch_suggestions': True,
                'max_suggestions_per_session': 3,
                'prefer_incremental_changes': True
            },
            'notification_settings': {
                'show_system_notifications': True,
                'show_cli_messages': True,
                'notification_frequency': 'smart'  # 'never', 'daily', 'weekly', 'smart'
            }
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                # Merge with defaults (in case new settings were added)
                default_settings.update(loaded_settings)
                return default_settings
            except:
                pass
        
        # Save default settings
        self._save_settings(default_settings)
        return default_settings
    
    def _save_settings(self, settings: dict):
        """Save integration settings"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"⚠️ Warning: Could not save integration settings: {e}")
    
    def _get_last_run_info(self) -> dict:
        """Get information about the last proactive run"""
        
        if self.last_run_file.exists():
            try:
                with open(self.last_run_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'last_run_date': None,
            'files_organized_since': 0,
            'corrections_since': 0,
            'folders_created_since': 0
        }
    
    def _update_last_run_info(self, info: dict):
        """Update last run information"""
        try:
            with open(self.last_run_file, 'w') as f:
                json.dump(info, f, indent=2)
        except Exception as e:
            print(f"⚠️ Warning: Could not save last run info: {e}")
    
    def should_trigger_proactive_learning(self) -> tuple[bool, str]:
        """Check if proactive learning should be triggered"""
        
        if not self.settings['enabled']:
            return False, "Auto-proactive learning is disabled"
        
        last_run = self._get_last_run_info()
        triggers = self.settings['trigger_conditions']
        
        # Check time-based trigger
        if last_run['last_run_date']:
            last_date = datetime.fromisoformat(last_run['last_run_date'])
            days_since = (datetime.now() - last_date).days
            
            if days_since < triggers['min_days_since_last_run']:
                return False, f"Only {days_since} days since last run (minimum: {triggers['min_days_since_last_run']})"
        
        # Check activity-based triggers
        reasons = []
        
        # Files organized threshold
        if last_run['files_organized_since'] >= triggers['min_files_organized_since_last_run']:
            reasons.append(f"{last_run['files_organized_since']} files organized since last run")
        
        # Corrections threshold
        if last_run['corrections_since'] >= triggers['min_corrections_since_last_run']:
            reasons.append(f"{last_run['corrections_since']} corrections made since last run")
        
        # Check folder overflow
        if triggers['trigger_on_folder_overflow']:
            overflow_folders = self._check_folder_overflow(triggers['overflow_threshold'])
            if overflow_folders:
                reasons.append(f"Folder overflow detected: {', '.join(overflow_folders[:3])}")
        
        if reasons:
            return True, "; ".join(reasons)
        else:
            return False, "No trigger conditions met"
    
    def _check_folder_overflow(self, threshold: int) -> list:
        """Check for folders with too many files"""
        
        overflow_folders = []
        
        # Check common temporary/staging folders
        folders_to_check = [
            Path.home() / "Downloads",
            Path.home() / "Desktop", 
            self.base_dir / "99_TEMP_PROCESSING",
        ]
        
        for folder in folders_to_check:
            if folder.exists() and folder.is_dir():
                try:
                    file_count = len([f for f in folder.iterdir() if f.is_file()])
                    if file_count >= threshold:
                        overflow_folders.append(f"{folder.name} ({file_count} files)")
                except:
                    continue
        
        return overflow_folders
    
    def trigger_proactive_learning(self, interactive: bool = True) -> dict:
        """Trigger proactive learning analysis"""
        
        print("🤖 Auto-triggering proactive learning analysis...")
        
        # Initialize proactive engine if needed
        if not self.proactive_engine:
            self.proactive_engine = ProactiveLearningEngine(str(self.base_dir))
        
        try:
            # Run proactive analysis
            results = self.proactive_engine.run_proactive_analysis(interactive=interactive)
            
            # Update last run info
            last_run_info = {
                'last_run_date': datetime.now().isoformat(),
                'files_organized_since': 0,  # Reset counter
                'corrections_since': 0,      # Reset counter
                'folders_created_since': len(results.get('implementation_results', {}).get('implemented', [])),
                'insights_found': len(results['analysis']['insights']),
                'suggestions_made': len(results['analysis']['folder_suggestions'])
            }
            
            self._update_last_run_info(last_run_info)
            
            # Show notification if enabled
            if self.settings['notification_settings']['show_system_notifications']:
                self._show_completion_notification(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error during proactive learning: {e}")
            return {'error': str(e)}
    
    def _show_completion_notification(self, results: dict):
        """Show system notification about proactive learning completion"""
        
        try:
            insights_count = len(results['analysis']['insights'])
            suggestions_count = len(results['analysis']['folder_suggestions'])
            
            if 'implementation_results' in results:
                impl = results['implementation_results']
                folders_created = len(impl.get('implemented', []))
                
                if folders_created > 0:
                    message = f"🎉 Proactive Learning: Created {folders_created} new folders"
                else:
                    message = f"🤖 Proactive Learning: Found {insights_count} insights, {suggestions_count} suggestions"
            else:
                message = f"🧠 Proactive Learning: Analyzed system, found {insights_count} improvement opportunities"
            
            # Use macOS notification (you can adapt for other platforms)
            import subprocess
            subprocess.run([
                'osascript', '-e',
                f'display notification "{message}" with title "AI File Organizer" subtitle "Learning Complete"'
            ], check=False)
            
        except Exception as e:
            print(f"⚠️ Could not show notification: {e}")
    
    def increment_file_organized_counter(self):
        """Increment counter when files are organized"""
        last_run = self._get_last_run_info()
        last_run['files_organized_since'] += 1
        self._update_last_run_info(last_run)
    
    def increment_correction_counter(self):
        """Increment counter when user makes corrections"""
        last_run = self._get_last_run_info()
        last_run['corrections_since'] += 1
        self._update_last_run_info(last_run)
    
    def check_and_maybe_trigger(self, interactive: bool = True) -> Optional[dict]:
        """Check conditions and maybe trigger proactive learning"""
        
        should_trigger, reason = self.should_trigger_proactive_learning()
        
        if should_trigger:
            print(f"🎯 Triggering proactive learning: {reason}")
            return self.trigger_proactive_learning(interactive=interactive)
        else:
            if self.settings['notification_settings']['show_cli_messages']:
                print(f"📝 Proactive learning not triggered: {reason}")
            return None
    
    def enable_auto_proactive(self):
        """Enable automatic proactive learning"""
        self.settings['enabled'] = True
        self._save_settings(self.settings)
        print("✅ Auto-proactive learning enabled")
    
    def disable_auto_proactive(self):
        """Disable automatic proactive learning"""
        self.settings['enabled'] = False
        self._save_settings(self.settings)
        print("❌ Auto-proactive learning disabled")
    
    def configure_settings(self, **kwargs):
        """Configure integration settings"""
        
        # Update nested settings
        for key, value in kwargs.items():
            if '.' in key:
                # Handle nested keys like 'trigger_conditions.min_days_since_last_run'
                parts = key.split('.')
                current = self.settings
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                self.settings[key] = value
        
        self._save_settings(self.settings)
        print(f"⚙️ Settings updated: {', '.join(kwargs.keys())}")


# Integration hooks for existing workflow
def hook_file_organized(integration: AutoProactiveIntegration):
    """Hook to call when a file is organized"""
    integration.increment_file_organized_counter()

def hook_user_correction(integration: AutoProactiveIntegration):
    """Hook to call when user makes a correction"""
    integration.increment_correction_counter()

def hook_workflow_complete(integration: AutoProactiveIntegration, interactive: bool = True):
    """Hook to call when a major workflow completes"""
    return integration.check_and_maybe_trigger(interactive=interactive)


# CLI for managing integration
def main():
    """CLI for auto-proactive integration management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-Proactive Learning Integration Manager')
    parser.add_argument('--base-dir', help='Base directory for AI organizer')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status
    subparsers.add_parser('status', help='Show integration status')
    
    # Enable/disable
    subparsers.add_parser('enable', help='Enable auto-proactive learning')
    subparsers.add_parser('disable', help='Disable auto-proactive learning')
    
    # Check
    check_parser = subparsers.add_parser('check', help='Check if proactive learning should trigger')
    check_parser.add_argument('--trigger', action='store_true', help='Actually trigger if conditions are met')
    
    # Configure
    config_parser = subparsers.add_parser('configure', help='Configure integration settings')
    config_parser.add_argument('--min-files', type=int, help='Minimum files organized before trigger')
    config_parser.add_argument('--min-days', type=int, help='Minimum days between runs')
    config_parser.add_argument('--auto-implement', action='store_true', help='Enable auto-implementation')
    
    args = parser.parse_args()
    
    if not args.command:
        args.command = 'status'
    
    # Initialize integration
    integration = AutoProactiveIntegration(args.base_dir)
    
    if args.command == 'status':
        print("🤖 Auto-Proactive Learning Integration Status")
        print("=" * 50)
        print(f"Enabled: {'✅' if integration.settings['enabled'] else '❌'}")
        
        should_trigger, reason = integration.should_trigger_proactive_learning()
        print(f"Should trigger now: {'✅' if should_trigger else '❌'}")
        print(f"Reason: {reason}")
        
        last_run = integration._get_last_run_info()
        print(f"\nLast run: {last_run['last_run_date'] or 'Never'}")
        print(f"Files organized since: {last_run['files_organized_since']}")
        print(f"Corrections since: {last_run['corrections_since']}")
        
    elif args.command == 'enable':
        integration.enable_auto_proactive()
        
    elif args.command == 'disable':
        integration.disable_auto_proactive()
        
    elif args.command == 'check':
        result = integration.check_and_maybe_trigger(interactive=True) if args.trigger else None
        if result:
            print("🎉 Proactive learning was triggered!")
        else:
            should_trigger, reason = integration.should_trigger_proactive_learning()
            print(f"Trigger result: {should_trigger} - {reason}")
    
    elif args.command == 'configure':
        updates = {}
        if args.min_files:
            updates['trigger_conditions.min_files_organized_since_last_run'] = args.min_files
        if args.min_days:
            updates['trigger_conditions.min_days_since_last_run'] = args.min_days
        if args.auto_implement:
            updates['auto_implementation.enabled'] = True
        
        if updates:
            integration.configure_settings(**updates)
        else:
            print("No configuration changes specified")


if __name__ == '__main__':
    main()