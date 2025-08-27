from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import uuid
from agents import PropertyAnalysisSystem
from models import AnalysisDepth, TaskStatus
from langsmith import Client

logger = logging.getLogger(__name__)

class PropertyAnalysisService:
    """
    Service layer for property analysis with simple progress tracking
    """
    
    def __init__(self):
        """Initialize service with LangSmith client and in-memory task storage"""
        self.langsmith_client = Client()
        self.task_storage = {}
    
    def _initialize_task(self, task_id: str, address: str):
        """Create a new task entry in storage with initial state"""
        self.task_storage[task_id] = TaskStatus(
            task_id=task_id,
            status="initializing",
            progress=0,
            current_step="Initializing analysis task...",
            result=None,
            error=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        logger.info(f"Initialized task {task_id} for address: {address}")
    
    def _progress_callback(self, task_id: str):
        """Return a callback function to update progress for a given task"""
        def callback(progress: int, message: str):
            self._update_task_status(task_id, progress=progress, current_step=message)
        return callback
    
    def get_active_tasks_count(self) -> int:
        """Return number of tasks currently active (initializing or processing)"""
        return sum(1 for task in self.task_storage.values() 
                  if task.status in ['initializing', 'processing'])
    
    async def analyze_with_task_id(
        self,
        task_id: str,
        address: str,
        depth: AnalysisDepth = AnalysisDepth.STANDARD
    ) -> Dict[str, Any]:
        """Run property analysis with an existing task ID and track progress"""
        try:
            logger.info(f"Starting analysis for task {task_id}: {address}")
            self._update_task_status(task_id, status="processing", progress=10, current_step="Initializing analysis system...")
            
            analysis_system = PropertyAnalysisSystem(
                progress_callback=self._progress_callback(task_id)
            )
            
            result = await analysis_system.analyze_property(address)
            
            result.update({
                'analysis_id': task_id,
                'analysis_depth': depth.value,
                'timestamp': datetime.now().isoformat(),
                'address': address
            })
            
            result_status = result.get('status', 'completed')
            
            if result_status == 'failed_zimas_search':
                self._update_task_status(
                    task_id, 
                    status="failed_zimas_search", 
                    progress=20,
                    current_step="Address not found in ZIMAS",
                    result=result
                )
            elif result_status == 'error_zimas_search':
                self._update_task_status(
                    task_id, 
                    status="error_zimas_search", 
                    progress=20,
                    current_step="ZIMAS search error occurred",
                    result=result
                )
            elif result_status == 'completed':
                self._update_task_status(
                    task_id, 
                    status="completed", 
                    progress=100, 
                    current_step="Analysis completed!",
                    result=result
                )
            else:
                self._update_task_status(
                    task_id, 
                    status="failed", 
                    progress=0, 
                    current_step="Analysis failed",
                    result=result
                )
            
            logger.info(f"Analysis completed for task {task_id}: {address} with status: {result_status}")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for task {task_id} ({address}): {e}", exc_info=True)
            self._update_task_status(
                task_id,
                status="failed",
                progress=0,
                current_step="Analysis failed",
                error=str(e)
            )
            raise
    
    async def analyze(
        self,
        address: str,
        depth: AnalysisDepth = AnalysisDepth.STANDARD
    ) -> Dict[str, Any]:
        """Run property analysis (wrapper that generates a new task ID)"""
        analysis_id = str(uuid.uuid4())
        self._initialize_task(analysis_id, address)
        return await self.analyze_with_task_id(analysis_id, address, depth)
    
    def _update_task_status(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Update an existing task in storage with new details"""
        if task_id in self.task_storage:
            task = self.task_storage[task_id]
            
            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = progress
            if current_step is not None:
                task.current_step = current_step
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            
            task.updated_at = datetime.now()
            self.task_storage[task_id] = task
            logger.debug(f"Updated task {task_id}: {progress}% - {current_step}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return current status dictionary for a given task ID"""
        if task_id in self.task_storage:
            task = self.task_storage[task_id]
            return {
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "result": task.result,
                "error": task.error,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        return None
    
    def cleanup_old_tasks(self, hours_old: int = 1):
        """Remove old completed/failed tasks older than given hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours_old)
        tasks_to_remove = []
        
        for task_id, task in self.task_storage.items():
            if task.updated_at < cutoff_time and task.status in ['completed', 'failed']:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.task_storage[task_id]
            logger.info(f"Cleaned up old task: {task_id}")
        
        return len(tasks_to_remove)
    
    async def log_to_langsmith(
        self,
        address: str,
        result: Dict[str, Any]
    ):
        """Send analysis run details to LangSmith for monitoring"""
        try:
            run_data = {
                "name": "property_analysis_complete",
                "inputs": {
                    "address": address,
                    "analysis_depth": result.get('analysis_depth', 'standard')
                },
                "outputs": {
                    "status": result.get('status', 'unknown'),
                    "analysis_completeness": result.get('summary', {}).get('analysis_completeness', 'unknown'),
                    "zimas_search_successful": result.get('summary', {}).get('zimas_search_successful', False),
                    "core_sections_found": len(result.get('summary', {}).get('core_sections_found', [])),
                    "key_findings_count": len(result.get('summary', {}).get('key_findings', []))
                },
                "run_type": "chain",
                "extra": {
                    "metadata": {
                        "analysis_id": result.get('analysis_id'),
                        "timestamp": result.get('timestamp'),
                        "data_sources": result.get('summary', {}).get('data_sources', [])
                    }
                }
            }
            
            self.langsmith_client.create_run(**run_data)
            logger.info(f"Successfully logged analysis for {address} to LangSmith")
            
        except Exception as e:
            logger.error(f"Failed to log to LangSmith: {e}")

    def analyze_sync(self, task_id: str, address: str, depth: str):
        """Synchronous wrapper around analyze_with_task_id (for thread pools)"""
        import asyncio
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            from models import AnalysisDepth
            if depth == "detailed":
                analysis_depth = AnalysisDepth.DETAILED
            elif depth == "basic":
                analysis_depth = AnalysisDepth.BASIC
            else:
                analysis_depth = AnalysisDepth.STANDARD
            
            result = loop.run_until_complete(
                self.analyze_with_task_id(task_id, address, analysis_depth)
            )
            
            import threading
            def delayed_cleanup():
                import time
                time.sleep(10)
                if task_id in self.task_storage:
                    task = self.task_storage[task_id]
                    if task.status in ['completed', 'failed']:
                        del self.task_storage[task_id]
                        logger.info(f"Auto-cleaned completed task: {task_id}")
            
            threading.Thread(target=delayed_cleanup, daemon=True).start()
            return result
            
        except Exception as e:
            logger.error(f"Sync analysis failed for task {task_id}: {e}", exc_info=True)
            if task_id in self.task_storage:
                self._update_task_status(
                    task_id,
                    status="failed", 
                    progress=0,
                    current_step="Analysis failed",
                    error=str(e)
                )
            raise