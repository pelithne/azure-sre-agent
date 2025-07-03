#!/usr/bin/env python3
"""
Memory Leak Test Application for Kubernetes Resource Testing

This application demonstrates controlled memory consumption with configurable leak behavior.
Designed for testing Kubernetes resource limits, monitoring, and autoscaling behavior.

Environment Variables:
- LEAK: Set to "TRUE" to enable memory leak behavior
- LEAK_RATE: Memory allocation rate in MB per second (default: 1)
- LEAK_INTERVAL: Interval between allocations in seconds (default: 1)
- MAX_MEMORY: Maximum memory to allocate in MB (default: 500)
- PORT: HTTP server port (default: 8080)

Security Features:
- Runs as non-root user
- Implements proper error handling
- Includes health check endpoints
- Structured logging for monitoring
"""

import os
import sys
import time
import threading
import logging
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import gc
import psutil

# Configure structured logging for Azure monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MemoryLeakApp:
    """
    Memory leak simulation application with configurable behavior.
    
    Features:
    - Controlled memory allocation/deallocation
    - HTTP health endpoints
    - Process monitoring
    - Graceful shutdown handling
    """
    
    def __init__(self):
        # Configuration from environment variables with secure defaults
        self.leak_enabled = os.getenv('LEAK', 'FALSE').upper() == 'TRUE'
        self.leak_rate_mb = max(1, min(100, int(os.getenv('LEAK_RATE', '1'))))  # Limit between 1-100 MB/s
        self.leak_interval = max(0.1, min(10, float(os.getenv('LEAK_INTERVAL', '1'))))  # Limit between 0.1-10 seconds
        self.max_memory_mb = max(10, min(2048, int(os.getenv('MAX_MEMORY', '500'))))  # Limit between 10-2048 MB
        self.port = int(os.getenv('PORT', '8080'))
        
        # Application state
        self.memory_chunks = []
        self.running = True
        self.start_time = datetime.now()
        self.current_memory_mb = 0
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"Memory Leak App initialized with config: "
                   f"leak_enabled={self.leak_enabled}, "
                   f"leak_rate={self.leak_rate_mb}MB/s, "
                   f"leak_interval={self.leak_interval}s, "
                   f"max_memory={self.max_memory_mb}MB, "
                   f"port={self.port}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def _allocate_memory_chunk(self, size_mb):
        """
        Allocate memory chunk of specified size.
        
        Args:
            size_mb (int): Size in megabytes to allocate
            
        Returns:
            bool: True if allocation successful, False otherwise
        """
        try:
            if self.current_memory_mb + size_mb > self.max_memory_mb:
                logger.warning(f"Memory allocation would exceed limit ({self.max_memory_mb}MB)")
                return False
            
            # Allocate memory chunk (1MB = 1024*1024 bytes)
            chunk = bytearray(size_mb * 1024 * 1024)
            # Fill with data to ensure actual memory allocation
            for i in range(0, len(chunk), 4096):
                chunk[i] = i % 256
            
            self.memory_chunks.append(chunk)
            self.current_memory_mb += size_mb
            
            logger.info(f"Allocated {size_mb}MB, total allocated: {self.current_memory_mb}MB")
            return True
            
        except MemoryError as e:
            logger.error(f"Memory allocation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during memory allocation: {e}")
            return False
    
    def _memory_leak_worker(self):
        """
        Background worker that simulates memory leak behavior.
        Runs in separate thread to allow HTTP server to remain responsive.
        """
        logger.info("Memory leak worker started")
        
        while self.running and self.leak_enabled:
            try:
                if not self._allocate_memory_chunk(self.leak_rate_mb):
                    logger.warning("Memory allocation failed or limit reached")
                    # Wait longer before retrying
                    time.sleep(self.leak_interval * 5)
                else:
                    time.sleep(self.leak_interval)
                    
            except Exception as e:
                logger.error(f"Error in memory leak worker: {e}")
                time.sleep(self.leak_interval)
        
        logger.info("Memory leak worker stopped")
    
    def get_memory_stats(self):
        """
        Get current memory usage statistics.
        
        Returns:
            dict: Memory statistics including system and process metrics
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "allocated_chunks": len(self.memory_chunks),
                "allocated_memory_mb": self.current_memory_mb,
                "process_memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "process_virtual_memory_mb": round(memory_info.vms / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2),
                "uptime_seconds": int((datetime.now() - self.start_time).total_seconds()),
                "leak_enabled": self.leak_enabled,
                "max_memory_mb": self.max_memory_mb
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}
    
    def cleanup_memory(self):
        """Clean up allocated memory chunks"""
        try:
            chunk_count = len(self.memory_chunks)
            self.memory_chunks.clear()
            self.current_memory_mb = 0
            gc.collect()  # Force garbage collection
            
            logger.info(f"Cleaned up {chunk_count} memory chunks")
            return True
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            return False

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks and monitoring endpoints"""
    
    def __init__(self, app, *args, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to use structured logging"""
        logger.info(f"HTTP {self.command} {self.path} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests for various endpoints"""
        try:
            if self.path == '/health':
                self._handle_health()
            elif self.path == '/ready':
                self._handle_readiness()
            elif self.path == '/metrics':
                self._handle_metrics()
            elif self.path == '/cleanup':
                self._handle_cleanup()
            elif self.path == '/':
                self._handle_root()
            else:
                self._send_response(404, {"error": "Not found"})
                
        except Exception as e:
            logger.error(f"Error handling request {self.path}: {e}")
            self._send_response(500, {"error": "Internal server error"})
    
    def _handle_health(self):
        """Liveness probe endpoint"""
        self._send_response(200, {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "running": self.app.running
        })
    
    def _handle_readiness(self):
        """Readiness probe endpoint"""
        ready = self.app.running
        status_code = 200 if ready else 503
        
        self._send_response(status_code, {
            "status": "ready" if ready else "not ready",
            "timestamp": datetime.now().isoformat()
        })
    
    def _handle_metrics(self):
        """Metrics endpoint for monitoring"""
        stats = self.app.get_memory_stats()
        self._send_response(200, stats)
    
    def _handle_cleanup(self):
        """Manual memory cleanup endpoint"""
        success = self.app.cleanup_memory()
        status_code = 200 if success else 500
        
        self._send_response(status_code, {
            "cleanup": "success" if success else "failed",
            "timestamp": datetime.now().isoformat()
        })
    
    def _handle_root(self):
        """Root endpoint with application info"""
        self._send_response(200, {
            "app": "Memory Leak Test Application",
            "version": "1.0",
            "endpoints": {
                "/health": "Liveness probe",
                "/ready": "Readiness probe", 
                "/metrics": "Memory metrics",
                "/cleanup": "Manual memory cleanup"
            },
            "config": {
                "leak_enabled": self.app.leak_enabled,
                "max_memory_mb": self.app.max_memory_mb,
                "leak_rate_mb": self.app.leak_rate_mb
            }
        })
    
    def _send_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

def create_handler(app):
    """Factory function to create handler with app reference"""
    def handler(*args, **kwargs):
        return HealthCheckHandler(app, *args, **kwargs)
    return handler

def main():
    """Main application entry point"""
    try:
        # Initialize application
        app = MemoryLeakApp()
        
        # Start memory leak worker in background thread
        if app.leak_enabled:
            leak_thread = threading.Thread(target=app._memory_leak_worker, daemon=True)
            leak_thread.start()
            logger.info("Memory leak simulation started")
        else:
            logger.info("Memory leak simulation disabled")
        
        # Start HTTP server
        handler = create_handler(app)
        server = HTTPServer(('0.0.0.0', app.port), handler)
        
        logger.info(f"HTTP server starting on port {app.port}")
        logger.info("Application ready to serve requests")
        
        # Run server until shutdown signal
        while app.running:
            server.timeout = 1.0
            server.handle_request()
        
        logger.info("Shutting down HTTP server...")
        server.server_close()
        
        # Cleanup resources
        app.cleanup_memory()
        logger.info("Application shutdown complete")
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
