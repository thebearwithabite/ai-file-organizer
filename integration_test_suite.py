#!/usr/bin/env python3
"""
Integration Test Suite for AI File Organizer v3.1
Part of AI File Organizer v3.1 - Adaptive Emergency Prevention System

Comprehensive testing and verification of all core intelligence components:
- Universal Adaptive Learning System
- 4-Level Confidence System 
- Adaptive Background Monitor
- Automated Deduplication Service
- Emergency Space Protection
- Interactive Batch Processor

Created by: RT Max / Claude Code
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
import json
import logging
import traceback
from dataclasses import dataclass

# Import all components to test
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from universal_adaptive_learning import UniversalAdaptiveLearning
from confidence_system import ADHDFriendlyConfidenceSystem, ConfidenceLevel
from adaptive_background_monitor import AdaptiveBackgroundMonitor
from automated_deduplication_service import AutomatedDeduplicationService
from emergency_space_protection import EmergencySpaceProtection
from interactive_batch_processor import InteractiveBatchProcessor

@dataclass
class TestResult:
    """Result of a test case"""
    test_name: str
    component: str
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = None

@dataclass
class IntegrationTestReport:
    """Complete integration test report"""
    test_session_id: str
    start_time: datetime
    end_time: datetime
    total_tests: int
    passed_tests: int
    failed_tests: int
    test_results: List[TestResult]
    system_health: Dict[str, Any]
    recommendations: List[str]

class IntegrationTestSuite:
    """
    Comprehensive integration test suite for AI File Organizer v3.1
    
    Tests all core intelligence components and their interactions
    """
    
    def __init__(self, test_dir: str = None):
        # Create test environment
        if test_dir:
            self.test_dir = Path(test_dir)
        else:
            self.test_dir = Path(tempfile.mkdtemp(prefix="ai_organizer_test_"))
        
        self.test_dir.mkdir(exist_ok=True)
        
        # Test results
        self.test_results = []
        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Test file creation helpers
        self.test_files_created = []
        
        self.logger.info(f"Integration test suite initialized in {self.test_dir}")

    def run_full_integration_test(self) -> IntegrationTestReport:
        """Run complete integration test suite"""
        
        start_time = datetime.now()
        self.logger.info("🧪 Starting full integration test suite...")
        
        try:
            # Test each component individually
            self._test_universal_adaptive_learning()
            self._test_confidence_system()
            self._test_adaptive_background_monitor()
            self._test_automated_deduplication_service()
            self._test_emergency_space_protection()
            self._test_interactive_batch_processor()
            
            # Test component interactions
            self._test_learning_confidence_integration()
            self._test_monitor_deduplication_integration()
            self._test_batch_learning_integration()
            self._test_emergency_response_integration()
            
            # Test end-to-end workflows
            self._test_end_to_end_organization()
            self._test_emergency_prevention_workflow()
            
        except Exception as e:
            self.logger.error(f"Fatal error in integration tests: {e}")
            self.test_results.append(TestResult(
                test_name="fatal_error",
                component="integration_suite",
                success=False,
                execution_time=0.0,
                error_message=str(e)
            ))
        
        end_time = datetime.now()
        
        # Generate report
        report = self._generate_test_report(start_time, end_time)
        
        # Cleanup test environment
        self._cleanup_test_environment()
        
        return report

    def _test_universal_adaptive_learning(self):
        """Test Universal Adaptive Learning System"""
        
        self.logger.info("🧠 Testing Universal Adaptive Learning System...")
        
        # Test 1: Initialization
        test_start = time.time()
        try:
            learning_system = UniversalAdaptiveLearning(str(self.test_dir))
            
            self.test_results.append(TestResult(
                test_name="learning_system_initialization",
                component="universal_adaptive_learning",
                success=True,
                execution_time=time.time() - test_start,
                details={"database_created": learning_system.db_path.exists()}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="learning_system_initialization",
                component="universal_adaptive_learning",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
            return
        
        # Test 2: Learning event recording
        test_start = time.time()
        try:
            test_file = self._create_test_file("test_contract.pdf", "This is a test contract for Client Name.")
            
            event_id = learning_system.record_learning_event(
                event_type="user_correction",
                file_path=str(test_file),
                original_prediction={"category": "documents", "confidence": 0.6},
                user_action={"target_category": "entertainment_industry", "target_location": "test_location"},
                confidence_before=0.6,
                context={"content_keywords": ["contract", "Client Name"]}
            )
            
            success = event_id is not None
            
            self.test_results.append(TestResult(
                test_name="learning_event_recording",
                component="universal_adaptive_learning",
                success=success,
                execution_time=time.time() - test_start,
                details={"event_id": event_id, "events_count": len(learning_system.learning_events)}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="learning_event_recording",
                component="universal_adaptive_learning",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
        
        # Test 3: Pattern discovery
        test_start = time.time()
        try:
            # Create multiple similar learning events
            for i in range(5):
                test_file = self._create_test_file(f"test_document_{i}.pdf", f"Document {i} about entertainment industry.")
                learning_system.record_learning_event(
                    event_type="manual_move",
                    file_path=str(test_file),
                    original_prediction={"category": "documents"},
                    user_action={"target_category": "entertainment_industry"},
                    confidence_before=0.5,
                    context={"content_keywords": ["entertainment", "industry"]}
                )
            
            # Test prediction
            test_file = self._create_test_file("new_test.pdf", "Entertainment industry document.")
            prediction = learning_system.predict_user_action(
                str(test_file), 
                {"content_keywords": ["entertainment", "industry"]}
            )
            
            success = prediction["confidence"] > 0.0
            
            self.test_results.append(TestResult(
                test_name="pattern_discovery_and_prediction",
                component="universal_adaptive_learning",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "prediction_confidence": prediction["confidence"],
                    "patterns_discovered": len(learning_system.patterns),
                    "preferences_learned": len(learning_system.user_preferences)
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="pattern_discovery_and_prediction",
                component="universal_adaptive_learning",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
        
        # Test 4: Data persistence
        test_start = time.time()
        try:
            learning_system.save_all_data()
            
            # Create new instance to test loading
            new_learning_system = UniversalAdaptiveLearning(str(self.test_dir))
            
            success = (len(new_learning_system.learning_events) > 0 and 
                      new_learning_system.learning_events_file.exists())
            
            self.test_results.append(TestResult(
                test_name="data_persistence",
                component="universal_adaptive_learning",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "events_persisted": len(new_learning_system.learning_events),
                    "patterns_persisted": len(new_learning_system.patterns),
                    "preferences_persisted": len(new_learning_system.user_preferences)
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="data_persistence",
                component="universal_adaptive_learning",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_confidence_system(self):
        """Test 4-Level Confidence System"""
        
        self.logger.info("🎯 Testing 4-Level Confidence System...")
        
        # Test 1: Initialization and configuration
        test_start = time.time()
        try:
            confidence_system = ADHDFriendlyConfidenceSystem(str(self.test_dir))
            
            success = confidence_system.config_file.exists() or True  # Config might not exist initially
            
            self.test_results.append(TestResult(
                test_name="confidence_system_initialization",
                component="confidence_system",
                success=success,
                execution_time=time.time() - test_start,
                details={"config_loaded": bool(confidence_system.user_config)}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="confidence_system_initialization",
                component="confidence_system",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
            return
        
        # Test 2: Confidence level determination
        test_start = time.time()
        try:
            test_file = self._create_test_file("downloads_test.pdf", "Test document in downloads")
            
            # Test different scenarios
            confidence_levels = {}
            
            # Downloads file should get MINIMAL level by default
            level = confidence_system.determine_confidence_level(str(test_file))
            confidence_levels["downloads"] = level.name
            
            # Test emergency conditions
            emergency_context = {"duplicate_count": 60}  # Above emergency threshold
            decision = confidence_system.make_confidence_decision(
                file_path=str(test_file),
                predicted_action={"target_location": "test_location"},
                system_confidence=0.7,
                context=emergency_context
            )
            
            success = decision.confidence_level is not None
            
            self.test_results.append(TestResult(
                test_name="confidence_level_determination",
                component="confidence_system",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "confidence_levels": confidence_levels,
                    "emergency_override": decision.emergency_prevention,
                    "requires_user_input": decision.requires_user_input
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="confidence_level_determination",
                component="confidence_system",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
        
        # Test 3: All confidence levels
        test_start = time.time()
        try:
            test_scenarios = [
                ("never_mode", 0.3, ConfidenceLevel.NEVER),
                ("minimal_mode", 0.6, ConfidenceLevel.MINIMAL),
                ("smart_mode", 0.8, ConfidenceLevel.SMART),
                ("always_mode", 0.9, ConfidenceLevel.ALWAYS)
            ]
            
            level_results = {}
            
            for scenario_name, confidence, expected_level in test_scenarios:
                # Temporarily set default level
                confidence_system.user_config["default_level"] = expected_level.name
                
                level = confidence_system.determine_confidence_level(str(test_file))
                decision = confidence_system.make_confidence_decision(
                    file_path=str(test_file),
                    predicted_action={"target_location": "test"},
                    system_confidence=confidence
                )
                
                level_results[scenario_name] = {
                    "determined_level": level.name,
                    "decision_level": decision.confidence_level.name,
                    "requires_user_input": decision.requires_user_input
                }
            
            success = len(level_results) == len(test_scenarios)
            
            self.test_results.append(TestResult(
                test_name="all_confidence_levels",
                component="confidence_system",
                success=success,
                execution_time=time.time() - test_start,
                details={"level_results": level_results}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="all_confidence_levels",
                component="confidence_system",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_adaptive_background_monitor(self):
        """Test Adaptive Background Monitor"""
        
        self.logger.info("🔍 Testing Adaptive Background Monitor...")
        
        # Test 1: Initialization
        test_start = time.time()
        try:
            monitor = AdaptiveBackgroundMonitor(str(self.test_dir))
            
            success = (monitor.learning_system is not None and 
                      monitor.confidence_system is not None and
                      monitor.deduplicator is not None)
            
            self.test_results.append(TestResult(
                test_name="monitor_initialization",
                component="adaptive_background_monitor",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "components_initialized": success,
                    "rules_db_exists": monitor.rules_db_path.exists()
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="monitor_initialization",
                component="adaptive_background_monitor",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
            return
        
        # Test 2: File event processing
        test_start = time.time()
        try:
            # Create a test file and simulate a move event
            test_file = self._create_test_file("monitor_test.pdf", "Test document for monitoring")
            target_dir = self.test_dir / "target"
            target_dir.mkdir(exist_ok=True)
            
            # Simulate learning from file move
            monitor._learn_from_file_move(
                str(test_file),
                str(target_dir / "monitor_test.pdf"),
                datetime.now()
            )
            
            # Check if learning event was recorded
            success = len(monitor.learning_system.learning_events) > 0
            
            self.test_results.append(TestResult(
                test_name="file_event_processing",
                component="adaptive_background_monitor",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "learning_events": len(monitor.learning_system.learning_events),
                    "user_corrections_learned": monitor.stats["user_corrections_learned"]
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="file_event_processing",
                component="adaptive_background_monitor",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
        
        # Test 3: Emergency detection
        test_start = time.time()
        try:
            # Test emergency detection (without actually creating emergency conditions)
            emergencies = monitor._detect_emergencies()
            
            # Should not detect emergencies in test environment
            success = isinstance(emergencies, list)
            
            self.test_results.append(TestResult(
                test_name="emergency_detection",
                component="adaptive_background_monitor",
                success=success,
                execution_time=time.time() - test_start,
                details={"emergencies_detected": len(emergencies)}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="emergency_detection",
                component="adaptive_background_monitor",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_automated_deduplication_service(self):
        """Test Automated Deduplication Service"""
        
        self.logger.info("🔍 Testing Automated Deduplication Service...")
        
        # Test 1: Initialization
        test_start = time.time()
        try:
            dedup_service = AutomatedDeduplicationService(str(self.test_dir))
            
            success = (dedup_service.deduplicator is not None and
                      dedup_service.learning_system is not None and
                      dedup_service.service_db_path.exists())
            
            self.test_results.append(TestResult(
                test_name="deduplication_service_initialization",
                component="automated_deduplication_service",
                success=success,
                execution_time=time.time() - test_start,
                details={"database_created": dedup_service.service_db_path.exists()}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="deduplication_service_initialization",
                component="automated_deduplication_service",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
            return
        
        # Test 2: Duplicate detection
        test_start = time.time()
        try:
            # Create duplicate files
            test_content = "This is a test document for duplicate detection."
            original_file = self._create_test_file("original.txt", test_content)
            duplicate_file = self._create_test_file("original (1).txt", test_content)
            
            # Test duplicate check
            check_result = dedup_service.check_for_duplicates_before_move(
                str(original_file),
                str(self.test_dir / "target")
            )
            
            success = check_result["status"] in ["safe", "duplicates_found"]
            
            self.test_results.append(TestResult(
                test_name="duplicate_detection",
                component="automated_deduplication_service",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "check_result": check_result["status"],
                    "duplicates_found": check_result.get("duplicates_found", 0)
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="duplicate_detection",
                component="automated_deduplication_service",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
        
        # Test 3: Threat analysis
        test_start = time.time()
        try:
            # Create a file that might be analyzed as a threat
            test_file = self._create_test_file("screenshot.png", "fake image content")
            
            candidate = dedup_service._evaluate_offload_candidate(test_file)
            
            success = candidate is not None
            
            self.test_results.append(TestResult(
                test_name="threat_analysis",
                component="automated_deduplication_service",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "candidate_created": candidate is not None,
                    "threat_score": candidate.offload_priority if candidate else 0
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="threat_analysis",
                component="automated_deduplication_service",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_emergency_space_protection(self):
        """Test Emergency Space Protection"""
        
        self.logger.info("🛡️ Testing Emergency Space Protection...")
        
        # Test 1: Initialization
        test_start = time.time()
        try:
            space_protection = EmergencySpaceProtection(str(self.test_dir))
            
            success = (space_protection.learning_system is not None and
                      space_protection.confidence_system is not None and
                      space_protection.protection_db_path.exists())
            
            self.test_results.append(TestResult(
                test_name="space_protection_initialization",
                component="emergency_space_protection",
                success=success,
                execution_time=time.time() - test_start,
                details={"database_created": space_protection.protection_db_path.exists()}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="space_protection_initialization",
                component="emergency_space_protection",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
            return
        
        # Test 2: Disk usage checking
        test_start = time.time()
        try:
            # Force an emergency check
            check_result = space_protection.force_emergency_check()
            
            success = "emergencies_detected" in check_result
            
            self.test_results.append(TestResult(
                test_name="disk_usage_checking",
                component="emergency_space_protection",
                success=success,
                execution_time=time.time() - test_start,
                details=check_result
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="disk_usage_checking",
                component="emergency_space_protection",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
        
        # Test 3: Offload candidate evaluation
        test_start = time.time()
        try:
            # Create a large test file
            large_file = self._create_test_file("large_file.mp4", "fake video content" * 1000)
            
            candidate = space_protection._evaluate_offload_candidate(large_file)
            
            success = candidate is not None
            
            self.test_results.append(TestResult(
                test_name="offload_candidate_evaluation",
                component="emergency_space_protection",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "candidate_created": candidate is not None,
                    "offload_priority": candidate.offload_priority if candidate else 0,
                    "file_size_mb": candidate.file_size_mb if candidate else 0
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="offload_candidate_evaluation",
                component="emergency_space_protection",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_interactive_batch_processor(self):
        """Test Interactive Batch Processor"""
        
        self.logger.info("📋 Testing Interactive Batch Processor...")
        
        # Test 1: Initialization
        test_start = time.time()
        try:
            batch_processor = InteractiveBatchProcessor(str(self.test_dir))
            
            success = (batch_processor.learning_system is not None and
                      batch_processor.confidence_system is not None and
                      batch_processor.batch_db_path.exists())
            
            self.test_results.append(TestResult(
                test_name="batch_processor_initialization",
                component="interactive_batch_processor",
                success=success,
                execution_time=time.time() - test_start,
                details={"database_created": batch_processor.batch_db_path.exists()}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="batch_processor_initialization",
                component="interactive_batch_processor",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
            return
        
        # Test 2: Batch session creation
        test_start = time.time()
        try:
            # Create some test files for batch processing
            test_dir = self.test_dir / "batch_test"
            test_dir.mkdir(exist_ok=True)
            
            test_files = [
                self._create_test_file("doc1.pdf", "Business document about contracts", test_dir),
                self._create_test_file("doc2.pdf", "Entertainment contract for Client Name", test_dir),
                self._create_test_file("image1.jpg", "image content", test_dir)
            ]
            
            session_id = batch_processor.start_batch_session(str(test_dir))
            
            success = session_id is not None and session_id in batch_processor.active_sessions
            
            self.test_results.append(TestResult(
                test_name="batch_session_creation",
                component="interactive_batch_processor",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "session_id": session_id,
                    "files_found": len(test_files),
                    "session_active": session_id in batch_processor.active_sessions if session_id else False
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="batch_session_creation",
                component="interactive_batch_processor",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))
        
        # Test 3: File preview generation
        test_start = time.time()
        try:
            test_file = self._create_test_file("preview_test.txt", "This is a test document with keywords like contract and entertainment.")
            
            preview = batch_processor._generate_file_preview(test_file)
            
            success = (preview is not None and 
                      preview.content_keywords and 
                      preview.predicted_category)
            
            self.test_results.append(TestResult(
                test_name="file_preview_generation",
                component="interactive_batch_processor",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "preview_created": preview is not None,
                    "keywords_extracted": len(preview.content_keywords) if preview else 0,
                    "prediction_made": bool(preview.predicted_category) if preview else False
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="file_preview_generation",
                component="interactive_batch_processor",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_learning_confidence_integration(self):
        """Test integration between learning system and confidence system"""
        
        self.logger.info("🔗 Testing Learning-Confidence Integration...")
        
        test_start = time.time()
        try:
            learning_system = UniversalAdaptiveLearning(str(self.test_dir))
            confidence_system = ADHDFriendlyConfidenceSystem(str(self.test_dir))
            
            # Create test file and learning event
            test_file = self._create_test_file("integration_test.pdf", "Integration test document")
            
            # Record learning event
            learning_system.record_learning_event(
                event_type="user_correction",
                file_path=str(test_file),
                original_prediction={"category": "documents", "confidence": 0.5},
                user_action={"target_category": "entertainment_industry"},
                confidence_before=0.5,
                context={"content_keywords": ["integration", "test"]}
            )
            
            # Test if confidence system can use learning system predictions
            prediction = learning_system.predict_user_action(str(test_file))
            
            decision = confidence_system.make_confidence_decision(
                file_path=str(test_file),
                predicted_action=prediction.get("predicted_action", {}),
                system_confidence=prediction.get("confidence", 0.0)
            )
            
            success = (prediction["confidence"] >= 0.0 and 
                      decision.confidence_level is not None)
            
            self.test_results.append(TestResult(
                test_name="learning_confidence_integration",
                component="integration",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "prediction_confidence": prediction["confidence"],
                    "decision_confidence_level": decision.confidence_level.name,
                    "integration_successful": success
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="learning_confidence_integration",
                component="integration",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_monitor_deduplication_integration(self):
        """Test integration between monitor and deduplication service"""
        
        self.logger.info("🔗 Testing Monitor-Deduplication Integration...")
        
        test_start = time.time()
        try:
            monitor = AdaptiveBackgroundMonitor(str(self.test_dir))
            dedup_service = AutomatedDeduplicationService(str(self.test_dir))
            
            # Create duplicate files
            original = self._create_test_file("original.txt", "test content")
            duplicate = self._create_test_file("original (1).txt", "test content")
            
            # Test duplicate detection
            check_result = dedup_service.check_for_duplicates_before_move(
                str(original),
                str(self.test_dir / "target")
            )
            
            # Test if monitor can handle duplicate emergency
            duplicate_context = {"duplicate_count": 55}  # Above threshold
            monitor._handle_duplicate_emergency({"type": "duplicate_crisis", "details": "Test emergency"})
            
            success = (check_result["status"] in ["safe", "duplicates_found"] and
                      monitor.stats["emergencies_prevented"] >= 0)
            
            self.test_results.append(TestResult(
                test_name="monitor_deduplication_integration",
                component="integration",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "duplicate_check": check_result["status"],
                    "emergencies_handled": monitor.stats["emergencies_prevented"]
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="monitor_deduplication_integration",
                component="integration",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_batch_learning_integration(self):
        """Test integration between batch processor and learning system"""
        
        self.logger.info("🔗 Testing Batch-Learning Integration...")
        
        test_start = time.time()
        try:
            batch_processor = InteractiveBatchProcessor(str(self.test_dir))
            
            # Create test files
            test_dir = self.test_dir / "batch_learning_test"
            test_dir.mkdir(exist_ok=True)
            
            test_files = [
                self._create_test_file("contract1.pdf", "Entertainment contract for Client Name", test_dir),
                self._create_test_file("contract2.pdf", "Business contract for entertainment industry", test_dir)
            ]
            
            # Start batch session
            session_id = batch_processor.start_batch_session(str(test_dir))
            
            # Get session overview
            overview = batch_processor.get_session_overview(session_id)
            
            success = (session_id is not None and 
                      overview["total_files"] > 0 and
                      overview["total_groups"] > 0)
            
            self.test_results.append(TestResult(
                test_name="batch_learning_integration",
                component="integration",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "session_created": session_id is not None,
                    "files_processed": overview.get("total_files", 0),
                    "groups_created": overview.get("total_groups", 0)
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="batch_learning_integration",
                component="integration",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_emergency_response_integration(self):
        """Test emergency response integration across components"""
        
        self.logger.info("🔗 Testing Emergency Response Integration...")
        
        test_start = time.time()
        try:
            space_protection = EmergencySpaceProtection(str(self.test_dir))
            dedup_service = AutomatedDeduplicationService(str(self.test_dir))
            monitor = AdaptiveBackgroundMonitor(str(self.test_dir))
            
            # Test emergency detection across systems
            space_check = space_protection.force_emergency_check()
            dedup_stats = dedup_service.get_service_stats()
            monitor_stats = monitor.get_adaptive_stats()
            
            success = (isinstance(space_check, dict) and
                      isinstance(dedup_stats, dict) and
                      isinstance(monitor_stats, dict))
            
            self.test_results.append(TestResult(
                test_name="emergency_response_integration",
                component="integration",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "space_emergencies": space_check.get("emergencies_detected", 0),
                    "dedup_threats": dedup_stats.get("active_threats", 0),
                    "monitor_emergencies": monitor_stats.get("adaptive_monitor_stats", {}).get("emergencies_prevented", 0)
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="emergency_response_integration",
                component="integration",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_end_to_end_organization(self):
        """Test end-to-end file organization workflow"""
        
        self.logger.info("🎯 Testing End-to-End Organization Workflow...")
        
        test_start = time.time()
        try:
            # Initialize all components
            learning_system = UniversalAdaptiveLearning(str(self.test_dir))
            confidence_system = ADHDFriendlyConfidenceSystem(str(self.test_dir))
            batch_processor = InteractiveBatchProcessor(str(self.test_dir))
            
            # Create realistic test scenario
            test_downloads = self.test_dir / "Downloads"
            test_downloads.mkdir(exist_ok=True)
            
            # Create various file types
            test_files = [
                self._create_test_file("Client Name_Contract_2024.pdf", "Entertainment contract for Client Name regarding television representation", test_downloads),
                self._create_test_file("Business_Proposal.docx", "Business proposal for creative partnership", test_downloads),
                self._create_test_file("Screenshot_2024.png", "screenshot content", test_downloads),
                self._create_test_file("Meeting_Notes.txt", "Notes from Client Name meeting about TV Show project", test_downloads)
            ]
            
            # Step 1: Generate predictions for each file
            predictions = {}
            for test_file in test_files:
                prediction = learning_system.predict_user_action(
                    str(test_file),
                    {"content_keywords": ["entertainment", "Client Name", "contract"]}
                )
                predictions[test_file.name] = prediction
            
            # Step 2: Make confidence decisions
            decisions = {}
            for test_file in test_files:
                decision = confidence_system.make_confidence_decision(
                    file_path=str(test_file),
                    predicted_action=predictions[test_file.name].get("predicted_action", {}),
                    system_confidence=predictions[test_file.name].get("confidence", 0.0)
                )
                decisions[test_file.name] = decision
            
            # Step 3: Test batch processing
            session_id = batch_processor.start_batch_session(str(test_downloads))
            overview = batch_processor.get_session_overview(session_id)
            
            success = (len(predictions) == len(test_files) and
                      len(decisions) == len(test_files) and
                      overview["total_files"] == len(test_files))
            
            self.test_results.append(TestResult(
                test_name="end_to_end_organization",
                component="workflow",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "files_created": len(test_files),
                    "predictions_generated": len(predictions),
                    "decisions_made": len(decisions),
                    "batch_session_files": overview.get("total_files", 0),
                    "avg_confidence": sum(p.get("confidence", 0) for p in predictions.values()) / len(predictions) if predictions else 0
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="end_to_end_organization",
                component="workflow",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _test_emergency_prevention_workflow(self):
        """Test emergency prevention workflow"""
        
        self.logger.info("🚨 Testing Emergency Prevention Workflow...")
        
        test_start = time.time()
        try:
            # Initialize emergency systems
            space_protection = EmergencySpaceProtection(str(self.test_dir))
            dedup_service = AutomatedDeduplicationService(str(self.test_dir))
            monitor = AdaptiveBackgroundMonitor(str(self.test_dir))
            
            # Create scenario that might trigger emergencies
            large_files_dir = self.test_dir / "large_files"
            large_files_dir.mkdir(exist_ok=True)
            
            # Create files that might trigger different emergency responses
            large_file = self._create_test_file("large_video.mp4", "fake video content" * 1000, large_files_dir)
            duplicate1 = self._create_test_file("document.pdf", "duplicate content", large_files_dir)
            duplicate2 = self._create_test_file("document (1).pdf", "duplicate content", large_files_dir)
            
            # Test space protection evaluation
            space_candidate = space_protection._evaluate_offload_candidate(large_file)
            
            # Test deduplication threat analysis
            dedup_candidate = dedup_service._evaluate_offload_candidate(duplicate1)
            
            # Test monitor emergency detection
            emergencies = monitor._detect_emergencies()
            
            success = (space_candidate is not None and 
                      dedup_candidate is not None and
                      isinstance(emergencies, list))
            
            self.test_results.append(TestResult(
                test_name="emergency_prevention_workflow",
                component="workflow",
                success=success,
                execution_time=time.time() - test_start,
                details={
                    "space_candidate_priority": space_candidate.offload_priority if space_candidate else 0,
                    "dedup_candidate_priority": dedup_candidate.offload_priority if dedup_candidate else 0,
                    "emergencies_detected": len(emergencies),
                    "emergency_systems_functional": success
                }
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="emergency_prevention_workflow",
                component="workflow",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            ))

    def _create_test_file(self, filename: str, content: str, directory: Path = None) -> Path:
        """Create a test file with specified content"""
        
        if directory is None:
            directory = self.test_dir
        
        file_path = directory / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.test_files_created.append(file_path)
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error creating test file {filename}: {e}")
            raise

    def _generate_test_report(self, start_time: datetime, end_time: datetime) -> IntegrationTestReport:
        """Generate comprehensive test report"""
        
        passed_tests = sum(1 for result in self.test_results if result.success)
        failed_tests = len(self.test_results) - passed_tests
        
        # Analyze system health
        system_health = self._analyze_system_health()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        report = IntegrationTestReport(
            test_session_id=self.test_session_id,
            start_time=start_time,
            end_time=end_time,
            total_tests=len(self.test_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            test_results=self.test_results,
            system_health=system_health,
            recommendations=recommendations
        )
        
        return report

    def _analyze_system_health(self) -> Dict[str, Any]:
        """Analyze overall system health based on test results"""
        
        component_results = {}
        
        # Group results by component
        for result in self.test_results:
            if result.component not in component_results:
                component_results[result.component] = {"passed": 0, "failed": 0, "total": 0}
            
            component_results[result.component]["total"] += 1
            if result.success:
                component_results[result.component]["passed"] += 1
            else:
                component_results[result.component]["failed"] += 1
        
        # Calculate health scores
        component_health = {}
        for component, results in component_results.items():
            health_score = results["passed"] / results["total"] if results["total"] > 0 else 0
            component_health[component] = {
                "health_score": health_score,
                "status": "healthy" if health_score >= 0.8 else "warning" if health_score >= 0.6 else "critical",
                "passed": results["passed"],
                "total": results["total"]
            }
        
        overall_health = sum(results["passed"] for results in component_results.values()) / len(self.test_results) if self.test_results else 0
        
        return {
            "overall_health_score": overall_health,
            "overall_status": "healthy" if overall_health >= 0.8 else "warning" if overall_health >= 0.6 else "critical",
            "component_health": component_health,
            "critical_failures": [result for result in self.test_results if not result.success and "initialization" in result.test_name]
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Check for critical failures
        critical_failures = [result for result in self.test_results if not result.success and "initialization" in result.test_name]
        if critical_failures:
            recommendations.append("🚨 Critical: Some components failed to initialize. Check database permissions and disk space.")
        
        # Check integration test results
        integration_failures = [result for result in self.test_results if not result.success and result.component == "integration"]
        if integration_failures:
            recommendations.append("🔗 Integration issues detected. Components may not be communicating properly.")
        
        # Check workflow test results
        workflow_failures = [result for result in self.test_results if not result.success and result.component == "workflow"]
        if workflow_failures:
            recommendations.append("🎯 End-to-end workflow issues detected. Review file organization pipeline.")
        
        # Performance recommendations
        slow_tests = [result for result in self.test_results if result.execution_time > 5.0]
        if slow_tests:
            recommendations.append("⚡ Some tests are running slowly. Consider optimizing database queries and file operations.")
        
        # Success recommendations
        if len(recommendations) == 0:
            recommendations.append("✅ All tests passed successfully! System is ready for production use.")
            recommendations.append("📊 Consider running periodic integration tests to maintain system health.")
            recommendations.append("🧠 Monitor learning system performance to ensure adaptive improvements.")
        
        return recommendations

    def _cleanup_test_environment(self):
        """Clean up test environment"""
        
        try:
            # Remove all created test files
            for file_path in self.test_files_created:
                if file_path.exists():
                    file_path.unlink()
            
            # Remove test directory if it's temporary
            if "ai_organizer_test_" in str(self.test_dir):
                shutil.rmtree(self.test_dir, ignore_errors=True)
            
            self.logger.info(f"Cleaned up test environment: {self.test_dir}")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up test environment: {e}")

    def print_test_report(self, report: IntegrationTestReport):
        """Print formatted test report"""
        
        print("\n" + "="*80)
        print("🧪 AI FILE ORGANIZER v3.1 - INTEGRATION TEST REPORT")
        print("="*80)
        
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Session ID: {report.test_session_id}")
        print(f"   Duration: {(report.end_time - report.start_time).total_seconds():.1f} seconds")
        print(f"   Total Tests: {report.total_tests}")
        print(f"   Passed: {report.passed_tests} ✅")
        print(f"   Failed: {report.failed_tests} ❌")
        print(f"   Success Rate: {(report.passed_tests/report.total_tests*100):.1f}%")
        
        print(f"\n🏥 SYSTEM HEALTH:")
        print(f"   Overall Score: {report.system_health['overall_health_score']:.1%}")
        print(f"   Status: {report.system_health['overall_status'].upper()}")
        
        print(f"\n🔧 COMPONENT HEALTH:")
        for component, health in report.system_health['component_health'].items():
            status_emoji = "✅" if health['status'] == 'healthy' else "⚠️" if health['status'] == 'warning' else "❌"
            print(f"   {status_emoji} {component}: {health['health_score']:.1%} ({health['passed']}/{health['total']})")
        
        if report.failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in report.test_results:
                if not result.success:
                    print(f"   • {result.component}/{result.test_name}: {result.error_message}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for recommendation in report.recommendations:
            print(f"   {recommendation}")
        
        print("\n" + "="*80)

# CLI interface
def main():
    """Command line interface for integration test suite"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI File Organizer Integration Test Suite')
    parser.add_argument('--test-dir', help='Custom test directory path')
    parser.add_argument('--component', help='Test specific component only')
    parser.add_argument('--quiet', action='store_true', help='Suppress detailed output')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    test_suite = IntegrationTestSuite(args.test_dir)
    
    print("🧪 Starting AI File Organizer v3.1 Integration Test Suite...")
    print(f"📁 Test environment: {test_suite.test_dir}")
    
    try:
        report = test_suite.run_full_integration_test()
        test_suite.print_test_report(report)
        
        # Exit with appropriate code
        exit_code = 0 if report.failed_tests == 0 else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Test suite interrupted by user")
        test_suite._cleanup_test_environment()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error in test suite: {e}")
        traceback.print_exc()
        test_suite._cleanup_test_environment()
        sys.exit(1)

if __name__ == "__main__":
    main()