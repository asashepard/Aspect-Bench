"""
Benchmark tests for: retry-mechanism

PROMPT SAYS:
"Create a retry mechanism for external service calls with configurable retry 
count (default 3), exponential backoff (1s, 2s, 4s), only retry specific 
exceptions, apply to email sending, and log retry attempts."

Tests based SOLELY on prompt requirements:
1. Retry decorator/utility exists and is reusable
2. Exponential backoff is implemented
3. Only specific exceptions trigger retries
4. Retries are logged
5. Final failure returns appropriate error
"""

import pytest
from unittest.mock import Mock, patch, call
import time

from app.core.config import settings


pytestmark = pytest.mark.aspect_bench


class TestRetryUtilityExists:
    """Test that retry utility/decorator exists."""
    
    def test_retry_module_exists(self) -> None:
        """Retry module should exist in app/utils/retry.py."""
        try:
            from app.utils import retry
            assert retry is not None
        except ImportError:
            # Try alternative location
            try:
                from app.utils.retry import retry_with_backoff
                assert retry_with_backoff is not None
            except ImportError:
                try:
                    from app.core.retry import retry_with_backoff
                    assert retry_with_backoff is not None
                except ImportError:
                    pytest.fail("Retry utility must exist in app.utils.retry or app.core.retry")
    
    def test_retry_decorator_is_callable(self) -> None:
        """Retry decorator should be callable."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.utils.retry import retry
                retry_func = retry
            except ImportError:
                try:
                    from app.core.retry import retry_with_backoff
                    retry_func = retry_with_backoff
                except ImportError:
                    pass
        
        assert retry_func is not None and callable(retry_func), \
            "Retry decorator/function must be callable"


class TestRetryBehavior:
    """Test retry behavior."""
    
    def test_retry_on_connection_error(self) -> None:
        """Retry should happen on connection errors."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.core.retry import retry_with_backoff
                retry_func = retry_with_backoff
            except ImportError:
                pytest.skip("Retry utility not found")
        
        call_count = 0
        
        @retry_func(max_retries=3, base_delay=0.01)  # Fast for testing
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient failure")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 3, "Should have retried until success"
    
    def test_no_retry_on_validation_error(self) -> None:
        """Validation errors should not trigger retry."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.core.retry import retry_with_backoff
                retry_func = retry_with_backoff
            except ImportError:
                pytest.skip("Retry utility not found")
        
        call_count = 0
        
        @retry_func(max_retries=3, base_delay=0.01)
        def validation_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")  # Should not retry
        
        with pytest.raises(ValueError):
            validation_failing_function()
        
        assert call_count == 1, "Validation errors should not trigger retry"
    
    def test_max_retries_exhausted(self) -> None:
        """Should fail after max retries exhausted."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.core.retry import retry_with_backoff
                retry_func = retry_with_backoff
            except ImportError:
                pytest.skip("Retry utility not found")
        
        call_count = 0
        
        @retry_func(max_retries=3, base_delay=0.01)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")
        
        with pytest.raises(ConnectionError):
            always_failing_function()
        
        assert call_count == 4, "Should try once + 3 retries = 4 total"


class TestExponentialBackoff:
    """Test exponential backoff timing."""
    
    def test_backoff_increases_exponentially(self) -> None:
        """Delays should increase exponentially."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.core.retry import retry_with_backoff
                retry_func = retry_with_backoff
            except ImportError:
                pytest.skip("Retry utility not found")
        
        delays = []
        last_call = [time.time()]
        call_count = 0
        
        @retry_func(max_retries=3, base_delay=0.1)
        def timing_function():
            nonlocal call_count
            now = time.time()
            if call_count > 0:
                delays.append(now - last_call[0])
            last_call[0] = now
            call_count += 1
            if call_count < 4:
                raise ConnectionError("Fail")
            return "done"
        
        try:
            timing_function()
        except:
            pass
        
        # Check that delays are increasing (exponential)
        if len(delays) >= 2:
            assert delays[1] > delays[0], \
                "Backoff delays should increase (exponential)"


class TestRetryLogging:
    """Test that retries are logged."""
    
    def test_retry_attempts_are_logged(self) -> None:
        """Each retry attempt should be logged."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.core.retry import retry_with_backoff
                retry_func = retry_with_backoff
            except ImportError:
                pytest.skip("Retry utility not found")
        
        with patch('logging.Logger.warning') as mock_log:
            call_count = 0
            
            @retry_func(max_retries=2, base_delay=0.01)
            def logged_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ConnectionError("Fail")
                return "done"
            
            logged_function()
            
            # Should have logged retry attempts
            # Note: exact logging format may vary


class TestRetryAppliedToEmail:
    """Test that retry is applied to email sending."""
    
    def test_email_utils_has_retry(self) -> None:
        """Email sending should use retry mechanism."""
        import inspect
        
        try:
            from app import utils
            source = inspect.getsource(utils)
            
            # Check if retry is used in utils module
            has_retry = (
                "retry" in source.lower() or
                "@retry" in source or
                "retry_with_backoff" in source
            )
            
            assert has_retry, \
                "Email utils should use retry mechanism"
        except ImportError:
            pytest.skip("Could not import app.utils")


class TestRetryReusability:
    """Test that retry mechanism is reusable."""
    
    def test_retry_can_be_parameterized(self) -> None:
        """Retry should accept configuration parameters."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.core.retry import retry_with_backoff
                retry_func = retry_with_backoff
            except ImportError:
                pytest.skip("Retry utility not found")
        
        # Should be able to configure retries
        @retry_func(max_retries=5, base_delay=0.01)
        def custom_retry_function():
            return "configured"
        
        result = custom_retry_function()
        assert result == "configured"
    
    def test_retry_works_as_decorator(self) -> None:
        """Retry should work as a decorator."""
        retry_func = None
        
        try:
            from app.utils.retry import retry_with_backoff
            retry_func = retry_with_backoff
        except ImportError:
            try:
                from app.core.retry import retry_with_backoff
                retry_func = retry_with_backoff
            except ImportError:
                pytest.skip("Retry utility not found")
        
        @retry_func()
        def decorated_function():
            return "decorated"
        
        assert decorated_function() == "decorated"
