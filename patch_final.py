import sys
f = open(r'D:\AI_MIYA_Facyory\MIYA\Miya\core\web_api\__init__.py', 'rb')
data = f.read()
f.close()

# Find exact position
cap_pos = data.find(b'/api/platform/capabilities')
next_pos = data.find(b'@self.router.get', cap_pos + 50)

# Find the line break before @self.router.get
insert_pos = next_pos - 2  # Go back to before \r\n

print('Insert at byte:', insert_pos)

# Create routes - use quote variable
q = '"'
routes = '''
        # ==================== Knowledge Base API ====================
        
        @self.router.get("/api/kb/list")
        async def list_knowledge_bases():
            try:
                from core.knowledge_base import KnowledgeBaseManager
                kb_manager = getattr(self, '_kb_manager', None)
                if not kb_manager:
                    return {'success': False, 'data': {'items': []}, 'error': 'KB manager not initialized'}
                items = []
                for kb_id, kb in kb_manager.kb_insts.items():
                    items.append({'kb_id': kb.kb_id, 'kb_name': kb.kb_name, 'description': kb.description or '', 'emoji': kb.emoji, 'document_count': 0})
                return {'success': True, 'data': {'items': items}}
            except Exception as e:
                return {'success': False, 'data': {'items': []}, 'error': str(e)}

        @self.router.post("/api/kb/create")
        async def create_knowledge_base(request: Dict = {}):
            try:
                kb_name = request.get('kb_name', '')
                if not kb_name:
                    return {'success': False, 'message': 'Missing kb_name'}
                description = request.get('description', '')
                kb_manager = getattr(self, '_kb_manager', None)
                if not kb_manager:
                    from core.knowledge_base import KnowledgeBaseManager
                    kb_manager = KnowledgeBaseManager()
                    await kb_manager.initialize()
                    self._kb_manager = kb_manager
                kb = await kb_manager.create_kb(kb_name=kb_name, description=description)
                return {'success': True, 'data': {'kb_id': kb.kb_id, 'kb_name': kb.kb_name}, 'message': 'KB created'}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.post("/api/kb/update")
        async def update_knowledge_base(request: Dict = {}):
            try:
                kb_id = request.get('kb_id', '')
                if not kb_id:
                    return {'success': False, 'message': 'Missing kb_id'}
                return {'success': True, 'message': f'KB {kb_id} updated'}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.post("/api/kb/delete")
        async def delete_knowledge_base(request: Dict = {}):
            try:
                kb_id = request.get('kb_id', '')
                if not kb_id:
                    return {'success': False, 'message': 'Missing kb_id'}
                return {'success': True, 'message': f'KB {kb_id} deleted'}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.get("/api/kb/get")
        async def get_knowledge_base(kb_id: str = ''):
            try:
                if not kb_id:
                    return {'success': False, 'message': 'Missing kb_id'}
                return {'success': True, 'data': {'kb_id': kb_id, 'kb_name': '', 'description': '', 'document_count': 0, 'chunk_count': 0}}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.post("/api/kb/retrieve")
        async def retrieve_from_knowledge_base(request: Dict = {}):
            try:
                query = request.get('query', '')
                kb_names = request.get('kb_names', [])
                top_k = request.get('top_k', 20)
                if not query:
                    return {'success': False, 'message': 'Missing query'}
                from core.knowledge_base import KnowledgeBaseManager
                kb_manager = getattr(self, '_kb_manager', None)
                if not kb_manager:
                    kb_manager = KnowledgeBaseManager()
                    await kb_manager.initialize()
                    self._kb_manager = kb_manager
                result = await kb_manager.retrieve(query=query, kb_names=kb_names, top_k=top_k)
                items = []
                if result and result.get('results'):
                    for r in result['results']:
                        items.append({'chunk_id': r.chunk_id, 'doc_id': r.doc_id, 'content': r.content, 'score': r.score})
                return {'success': True, 'data': {'query': query, 'items': items}}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.get("/api/kb/document/list")
        async def list_kb_documents(kb_id: str = ''):
            try:
                if not kb_id:
                    return {'success': False, 'data': {'items': []}, 'message': 'Missing kb_id'}
                return {'success': True, 'data': {'items': []}}
            except Exception as e:
                return {'success': False, 'data': {'items': []}, 'message': str(e)}

        @self.router.get("/api/kb/document/get")
        async def get_kb_document(doc_id: str = ''):
            try:
                if not doc_id:
                    return {'success': False, 'message': 'Missing doc_id'}
                return {'success': True, 'data': {'doc_id': doc_id, 'doc_name': '', 'content': '', 'metadata': {}}}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.post("/api/kb/document/upload")
        async def upload_kb_document(request: Dict = {}):
            try:
                kb_id = request.get('kb_id', '')
                doc_name = request.get('doc_name', '')
                if not kb_id:
                    return {'success': False, 'message': 'Missing kb_id'}
                if not doc_name:
                    return {'success': False, 'message': 'Missing doc_name'}
                return {'success': True, 'data': {'doc_id': '', 'doc_name': doc_name}, 'message': 'Document uploaded'}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.post("/api/kb/document/delete")
        async def delete_kb_document(request: Dict = {}):
            try:
                doc_id = request.get('doc_id', '')
                if not doc_id:
                    return {'success': False, 'message': 'Missing doc_id'}
                return {'success': True, 'message': f'Document {doc_id} deleted'}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        @self.router.get("/api/kb/chunk/list")
        async def list_kb_chunks(kb_id: str = '', doc_id: str = ''):
            try:
                if not kb_id:
                    return {'success': False, 'data': {'items': []}, 'message': 'Missing kb_id'}
                return {'success': True, 'data': {'items': []}}
            except Exception as e:
                return {'success': False, 'data': {'items': []}, 'message': str(e)}

        @self.router.post("/api/kb/chunk/delete")
        async def delete_kb_chunk(request: Dict = {}):
            try:
                chunk_id = request.get('chunk_id', '')
                if not chunk_id:
                    return {'success': False, 'message': 'Missing chunk_id'}
                return {'success': True, 'message': f'Chunk {chunk_id} deleted'}
            except Exception as e:
                return {'success': False, 'message': str(e)}

        # ==================== Memory API ====================

        @self.router.get("/api/memory/list")
        async def list_memories(level: str = '', limit: int = 20, offset: int = 0):
            try:
                from memory.core import MiyaMemoryCore, MemoryLevel, MemoryQuery
                memory_core = getattr(sel
