# Claude Code Instructions for BTC Watcher

## Project Context
Read: ../../context.md

## Project Rules
Read: ../../rules.md

## Coding Standards
- Python: Follow PEP 8, use type hints
- Vue: Follow Vue 3 Composition API
- Tests: Required for all new features
- Async: Use async/await for all I/O operations

## Project-Specific Guidelines

### 1. Backend Development
- All API routes in `backend/api/v1/`
- Business logic in `backend/services/`
- Database models in `backend/models/`
- Use dependency injection for database sessions
- Always use async/await for database operations
- Handle exceptions gracefully with try-except

### 2. Frontend Development
- Components in `frontend/src/components/`
- Pages in `frontend/src/views/`
- API calls in `frontend/src/api/`
- Use Pinia for state management
- Use Composition API with `<script setup>`
- Handle errors with try-catch and user-friendly messages

### 3. Testing
- Unit tests: `backend/tests/unit/`
- Integration tests: `backend/tests/integration/`
- E2E tests: `frontend/tests/e2e/`
- Coverage requirement: > 80%
- Test naming: `test_{function}_{scenario}_{expected}`

### 4. Documentation
- New features: `docs/implementation/features/`
- Bug fixes: `docs/implementation/bug-fixes/`
- Architecture changes: `docs/adr/`
- API changes: Update `docs/architecture/api-design.md`

## Forbidden Actions
- ❌ No new .md files in root directory
- ❌ No deletion of existing docs (archive instead)
- ❌ No hardcoded credentials
- ❌ No synchronous I/O in async functions
- ❌ No SQL string concatenation (use ORM)
- ❌ No commits without tests for new features

## Common Patterns

### Creating a New API Endpoint
```python
# 1. Define route in backend/api/v1/module.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/items")
async def get_items(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get items with pagination"""
    pass

# 2. Implement service in backend/services/module.py
async def get_items_service(
    db: AsyncSession,
    skip: int,
    limit: int
) -> List[Item]:
    """Business logic for getting items"""
    pass

# 3. Write tests in backend/tests/integration/test_module.py
async def test_get_items_returns_200():
    """Test getting items returns 200"""
    pass
```

### Creating a Vue Component
```vue
<!-- frontend/src/views/ItemList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { getItems } from '@/api/item'

const items = ref([])
const loading = ref(false)

const fetchItems = async () => {
  loading.value = true
  try {
    const response = await getItems()
    items.value = response.data
  } catch (error) {
    console.error('Failed to fetch items:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchItems()
})
</script>

<template>
  <div v-loading="loading">
    <el-table :data="items">
      <!-- table columns -->
    </el-table>
  </div>
</template>
```

## Workflow

### Feature Development
1. Read requirements from `docs/analysis/requirements.md`
2. Design solution (create ADR if architecture change)
3. Implement code following patterns above
4. Write tests (unit + integration)
5. Update documentation
6. Create PR with clear description
7. Record implementation in `docs/implementation/features/`

### Bug Fixing
1. Reproduce the bug
2. Write failing test
3. Fix the bug
4. Verify test passes
5. Create PR
6. Record fix in `docs/implementation/bug-fixes/`

## Special Considerations

### FreqTrade Integration
- Port range: 8081-9080
- Each strategy runs on dedicated port
- Use async HTTP client (httpx) for API calls
- Handle strategy startup/shutdown gracefully

### WebSocket
- Use FastAPI's WebSocket support
- Implement heartbeat mechanism
- Handle reconnection on client side
- Send structured JSON messages

### Performance
- Database queries: Use indexes, avoid N+1
- Cache frequently accessed data in Redis
- Use background tasks for heavy operations
- Monitor with system metrics

## Quick Commands
```bash
# Run tests
pytest backend/tests/

# Run specific test
pytest backend/tests/unit/test_strategy.py -v

# Check code format
black backend/
flake8 backend/

# Run development server
cd backend && python main.py

# Check documentation structure
make docs-check
```

## Resources
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/)
- [Vue 3 Docs](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
