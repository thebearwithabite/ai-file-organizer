#!/usr/bin/env python3
"""
Proactive Learning Hooks
Easy integration points for existing AI File Organizer workflows
"""

import sys
from pathlib import Path
from typing import Optional

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Global integration instance
_auto_integration = None

def get_integration():
    """Get or create the auto-proactive integration instance"""
    global _auto_integration
    if _auto_integration is None:
        try:
            from auto_proactive_integration import AutoProactiveIntegration
            _auto_integration = AutoProactiveIntegration()
        except ImportError:
            print("⚠️ Proactive learning integration not available")
            _auto_integration = None
    return _auto_integration

def on_file_organized(file_path: str = None, target_path: str = None, classification: str = None):
    """Hook: Call when a file has been organized"""
    integration = get_integration()
    if integration:
        integration.increment_file_organized_counter()
    
    # Learn from the file move
    if file_path and target_path:
        try:
            from video_project_trainer import VideoProjectTrainer
            from pathlib import Path
            
            file_path_obj = Path(file_path)
            target_path_obj = Path(target_path)
            
            # Learn from ALL file movements to improve organization patterns
            trainer = VideoProjectTrainer()  # Despite the name, it learns from all file types
            
            # Infer project from target folder structure
            target_parts = target_path_obj.parts
            inferred_project = None
            
            # Map folder names to projects (User's actual projects)
            folder_to_project = {
                'stranger_things': 'stranger_things',
                'netflix': 'stranger_things', 
                'finn': 'stranger_things',
                'demo_reel': 'demo_reels',
                'demo_materials': 'demo_reels',
                'multimedia_series': 'multimedia_series',
                'this_isnt_real': 'multimedia_series',
                'thebearwithabite': 'thebearwithabite',
                'bear_with_a_bite': 'thebearwithabite',
                'social_media': 'thebearwithabite',
                'papers_that_dream': 'papers_that_dream',
                'podcast': 'papers_that_dream',
                'ai_consciousness': 'papers_that_dream',
                'github': 'github_projects',
                'coding': 'github_projects',
                'development': 'github_projects',
                'ai_file_organizer': 'ai_file_organizer',
                'file_organizer': 'ai_file_organizer',
                'behind_scenes': 'behind_scenes',
                'bts': 'behind_scenes',
                'experiments': 'creative_experiments',
                'creative_test': 'creative_experiments',
                'business': 'business_content',
                'professional': 'business_content',
                # Additional patterns for other file types
                'contracts': 'business_content',
                'legal': 'business_content',
                'invoices': 'business_content',
                'tax': 'business_content',
                'scripts': 'creative_experiments',
                'music': 'creative_experiments',
                'audio': 'papers_that_dream',
                'emails': 'business_content',
                'documents': 'business_content',
                'creative': 'creative_experiments'
            }
            
            # Look through folder path to infer project
            for part in target_parts:
                part_lower = part.lower().replace('_', ' ').replace('-', ' ')
                for folder_key, project in folder_to_project.items():
                    if folder_key in part_lower:
                        inferred_project = project
                        break
                if inferred_project:
                    break
            
            # Also check filename for project clues
            if not inferred_project:
                filename_lower = file_path_obj.name.lower()
                for folder_key, project in folder_to_project.items():
                    if folder_key in filename_lower:
                        inferred_project = project
                        break
            
            if inferred_project:
                # Record this as a learning example for ALL file types
                trainer.learn_from_user_correction(
                    file_path_obj, 
                    classification or "unknown", 
                    inferred_project, 
                    f"Learned from user organizing {file_path_obj.suffix or 'file'} to {target_path_obj.parent.name}"
                )
                print(f"🧠 Learned: {file_path_obj.name} → {inferred_project}")
            else:
                # Even if we can't infer a project, learn the folder structure
                folder_name = target_path_obj.parent.name
                if folder_name.lower() not in ['downloads', 'desktop', 'documents', 'tmp']:
                    print(f"🧠 Learning: {file_path_obj.name} → folder pattern '{folder_name}'")
        except Exception as e:
            # Don't fail the file organization if learning fails
            if hasattr(integration, 'detailed_logging') and integration.detailed_logging:
                print(f"⚠️ Learning from file move failed: {e}")

def on_user_correction(from_category: str = None, to_category: str = None):
    """Hook: Call when user corrects a classification"""
    integration = get_integration()
    if integration:
        integration.increment_correction_counter()

def on_workflow_complete(workflow_name: str = "unknown", interactive: bool = False):
    """Hook: Call when a major workflow completes"""
    integration = get_integration()
    if integration:
        try:
            result = integration.check_and_maybe_trigger(interactive=interactive)
            if result:
                print(f"🤖 Proactive learning triggered after {workflow_name} workflow")
                return result
        except Exception as e:
            print(f"⚠️ Proactive learning check failed: {e}")
    return None

def on_bulk_operation_complete(files_processed: int, interactive: bool = False):
    """Hook: Call when a bulk operation completes"""
    integration = get_integration()
    if integration:
        # Increment counter for all files processed
        for _ in range(files_processed):
            integration.increment_file_organized_counter()
        
        # Check if we should trigger proactive learning
        return on_workflow_complete(f"bulk operation ({files_processed} files)", interactive)

def check_proactive_trigger(force: bool = False) -> Optional[dict]:
    """Manually check if proactive learning should trigger"""
    integration = get_integration()
    if integration:
        if force:
            return integration.trigger_proactive_learning(interactive=True)
        else:
            return integration.check_and_maybe_trigger(interactive=True)
    return None

def enable_proactive_learning():
    """Enable automatic proactive learning"""
    integration = get_integration()
    if integration:
        integration.enable_auto_proactive()

def disable_proactive_learning():
    """Disable automatic proactive learning"""
    integration = get_integration()
    if integration:
        integration.disable_auto_proactive()

# Decorator for easy integration
def with_proactive_learning(workflow_name: str = None):
    """Decorator to automatically add proactive learning to functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Trigger proactive learning after successful completion
                on_workflow_complete(workflow_name or func.__name__, interactive=False)
                return result
            except Exception as e:
                # Don't trigger proactive learning on errors
                raise e
        return wrapper
    return decorator

# Example usage in existing files:
"""
# In interactive_organizer.py, add at the top:
from proactive_hooks import on_file_organized, on_workflow_complete

# In the organize function, after successfully moving a file:
on_file_organized(str(file_path))

# At the end of the organize function:
on_workflow_complete("organize", interactive=True)

# In gdrive_librarian.py, add at the top:
from proactive_hooks import on_bulk_operation_complete

# In bulk_upload method, after processing all files:
on_bulk_operation_complete(len(successful_uploads), interactive=False)

# In interactive_classifier.py, when user corrects:
from proactive_hooks import on_user_correction
on_user_correction(original_category, corrected_category)
"""

if __name__ == '__main__':
    # Simple CLI for testing hooks
    import argparse
    
    parser = argparse.ArgumentParser(description='Test proactive learning hooks')
    parser.add_argument('action', choices=['check', 'trigger', 'enable', 'disable', 'test-hooks'])
    args = parser.parse_args()
    
    if args.action == 'check':
        result = check_proactive_trigger(force=False)
        print(f"Proactive trigger result: {result is not None}")
    elif args.action == 'trigger':
        result = check_proactive_trigger(force=True)
        print(f"Forced trigger result: {result is not None}")
    elif args.action == 'enable':
        enable_proactive_learning()
    elif args.action == 'disable':
        disable_proactive_learning()
    elif args.action == 'test-hooks':
        print("Testing proactive learning hooks...")
        on_file_organized("test_file.pdf")
        on_user_correction("old_category", "new_category") 
        print("✅ Hooks tested successfully")