# Cursor AI Development Rules

## Flask Application Development Rules

### 1. Flask Route Registration Issues

**Problem**: Flask BuildError "Could not build url for endpoint 'views.function_name'" even when route function exists

**Root Cause**: Flask development server doesn't always properly reload new routes, especially when:
- Background threads (schedulers) are running
- New services are added
- Template cache conflicts occur

**MANDATORY Fix Protocol**:
```bash
# 1. ALWAYS kill ALL Python processes (not just Ctrl+C)
taskkill /F /IM python.exe

# 2. Restart Flask completely
python app/main.py

# 3. Verify routes are registered (create test script if needed)
python -c "from app import create_app; app = create_app(); [print(rule) for rule in app.url_map.iter_rules() if 'target_route' in str(rule)]"
```

**Prevention Checklist**:
- [ ] Add new service imports to `app/services/__init__.py`
- [ ] Use complete process termination for route changes
- [ ] Never rely on auto-reload for new route additions
- [ ] Test route registration before debugging template issues
- [ ] Clear template cache with complete restart

### 2. Service Import Requirements

When adding new services (like AuditService):
```python
# MUST update app/services/__init__.py
from app.services.new_service import NewService
```

### 3. Flask Development Server Restart Protocol

**For New Routes/Services**:
- Complete process kill required
- Auto-reload is insufficient
- Background threads interfere with reload

**For Code Changes Only**:
- Ctrl+C restart usually sufficient
- Auto-reload works for logic changes

## General Development Rules

### 4. Error Debugging Hierarchy

1. **Complete Application Restart** - First step for route/import issues
2. **Check Service Imports** - Verify all services in `__init__.py`
3. **Route Registration Test** - Confirm Flask recognizes routes
4. **Template/Cache Issues** - Last resort, usually fixed by restart

### 5. Memory Management

- Always update memory when encountering new error patterns
- Document fix protocols for future reference
- Include prevention steps, not just solutions

### 6. Flask Application Architecture

**Route Organization**:
- Views in `app/routes/views.py`
- API endpoints in `app/routes/api.py`
- Services in `app/services/`
- Templates in `app/templates/`

**Service Integration**:
- Import in `app/services/__init__.py`
- Register routes in blueprint
- Complete restart for new integrations

## Testing Protocols

### 7. Route Testing

```python
# Quick route verification script
from app import create_app
app = create_app()
routes = [str(rule) for rule in app.url_map.iter_rules()]
target_routes = [r for r in routes if 'target_keyword' in r]
print(f"Found {len(target_routes)} matching routes")
```

### 8. Import Testing

```python
# Service import verification
try:
    from app.services.target_service import TargetService
    print("✅ Service imports successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

## Error Prevention

### 9. Common Flask Pitfalls

- **Route Registration**: Always complete restart for new routes
- **Service Imports**: Update `__init__.py` files
- **Template Cache**: Complete restart clears cache issues
- **Background Threads**: Kill processes, don't just interrupt

### 10. Development Workflow

1. Add new service/route
2. Update relevant `__init__.py` files
3. **Complete process termination** (`taskkill /F /IM python.exe`)
4. Restart Flask application
5. Test route registration
6. Verify functionality

## Memory Update Protocol

When encountering new error patterns:
1. Document the error and solution
2. Add to memory with prevention steps
3. Update this rules file
4. Include debugging hierarchy

---

**Remember**: Flask development server auto-reload is unreliable for structural changes (new routes, services, imports). Always use complete process termination and restart for these changes. 