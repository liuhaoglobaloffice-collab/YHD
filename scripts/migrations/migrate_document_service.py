#!/usr/bin/env python3
"""
Phase 4 Module 1: Migrate DocumentService to Database
This script modifies src/knowledge/documents.py to use Repository pattern
"""

import re


def migrate_document_service():
    """Migrate DocumentService from Dict to Repository"""
    
    with open('src/knowledge/documents.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Step 1: Add imports
    if 'from uuid import UUID' not in content:
        content = content.replace(
            'import hashlib',
            'import hashlib\nfrom uuid import UUID, uuid4'
        )
    
    # Step 2: Modify __init__ signature
    old_init = '''    def __init__(
        self,
        rbac_service: RBACService,
        policy_engine: PolicyEngine,
        audit_service: AuditService,
    ):
        self.rbac = rbac_service
        self.policy = policy_engine
        self.audit = audit_service
        
        # In-memory storage (will be replaced with database in production)
        self._documents: Dict[str, DocumentMetadata] = {}'''
    
    new_init = '''    def __init__(
        self,
        session,  # AsyncSession
        rbac_service: RBACService,
        policy_engine: PolicyEngine,
        audit_service: AuditService,
    ):
        # Phase 4: Database integration
        self.session = session
        from ..database.repositories.knowledge import DocumentRepository
        self.repository = DocumentRepository(session)
        
        self.rbac = rbac_service
        self.policy = policy_engine
        self.audit = audit_service'''
    
    content = content.replace(old_init, new_init)
    
    # Step 3: Add model converter
    converter = '''    
    def _model_to_metadata(self, model) -> DocumentMetadata:
        """Convert DocumentModel to DocumentMetadata"""
        return DocumentMetadata(
            id=str(model.id),
            filename=model.title or model.filename,
            file_type=model.content_type or "text/plain",
            size=model.size or 0,
            hash=model.content_hash or "",
            source=model.source or "upload",
            owner_id=model.owner_id or "system",
            status=DocumentStatus(model.status),
            version=1,
            created_at=model.created_at or datetime.now(UTC),
            updated_at=model.updated_at or datetime.now(UTC),
            metadata=model.metadata or {},
        )'''
    
    # Insert after compute_hash method
    content = content.replace(
        '    def compute_hash(self, content: bytes) -> str:\n        """Compute SHA-256 hash of file content"""\n        return hashlib.sha256(content).hexdigest()',
        '    def compute_hash(self, content: bytes) -> str:\n        """Compute SHA-256 hash of file content"""\n        return hashlib.sha256(content).hexdigest()' + converter
    )
    
    # Step 4: Replace upload_document database operations
    # Remove hash lookup and version creation
    content = re.sub(
        r'        # Check for duplicate by hash.*?return await self\._create_version\(user, existing, filename, metadata\)',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Replace document storage
    old_storage = '''        # Generate document ID
        doc_id = f"doc_{datetime.now(UTC).timestamp()}_{user.id}"
        
        # Create document metadata
        doc = DocumentMetadata(
            id=doc_id,
            filename=filename,
            file_type=file_type,
            size=size,
            hash=file_hash,
            source=source,
            owner_id=user.id,
            status=DocumentStatus.UPLOADED,
            metadata=metadata or {},
        )
        
        # Store document
        self._documents[doc_id] = doc'''
    
    new_storage = '''        # Phase 4: Store in database
        from ..database.models import DocumentModel
        
        doc_model = DocumentModel(
            id=uuid4(),
            title=filename,
            filename=filename,
            content=content.decode('utf-8', errors='ignore') if content else "",
            content_type=file_type,
            size=size,
            content_hash=file_hash,
            source=source,
            owner_id=user.id,
            status=DocumentStatus.UPLOADED.value,
            metadata=metadata or {},
        )
        
        created_doc = await self.repository.create(doc_model)
        await self.session.commit()'''
    
    content = content.replace(old_storage, new_storage)
    
    # Step 5: Replace upload_document return
    content = content.replace(
        '            resource_id=doc_id,',
        '            resource_id=str(created_doc.id),'
    )
    content = content.replace(
        '        return doc\n    \n    def _find_by_hash',
        '        return self._model_to_metadata(created_doc)\n    \n    async def get_document'
    )
    
    # Step 6: Remove _find_by_hash and _create_version methods
    content = re.sub(
        r'    def _find_by_hash.*?return new_version\n    \n',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Step 7: Replace get_document
    old_get = '''        # Find document
        doc = self._documents.get(document_id)
        if not doc:
            raise NotFoundError(f"Document not found: {document_id}")
        
        # Owner or admin can access
        if doc.owner_id != user.id and not self.rbac.is_admin(user):'''
    
    new_get = '''        # Phase 4: Query from database
        try:
            doc_uuid = UUID(document_id)
        except ValueError:
            raise NotFoundError(f"Document not found: {document_id}")
        
        doc_model = await self.repository.get_by_id(doc_uuid)
        if not doc_model:
            raise NotFoundError(f"Document not found: {document_id}")
        
        # Check ownership
        if doc_model.owner_id != user.id and not self.rbac.is_admin(user):'''
    
    content = content.replace(old_get, new_get)
    content = content.replace(
        '        return doc\n    \n    async def list_documents',
        '        return self._model_to_metadata(doc_model)\n    \n    async def list_documents'
    )
    
    # Step 8: Replace list_documents
    old_list = '''        # Filter documents
        docs = []
        for doc in self._documents.values():
            # Owner or admin can see
            if doc.owner_id != user.id and not self.rbac.is_admin(user):
                continue
            
            # Status filter
            if status and doc.status != status:
                continue
            
            # Owner filter
            if owner_id and doc.owner_id != owner_id:
                continue
            
            docs.append(doc)'''
    
    new_list = '''        # Phase 4: Query from database
        filters = {}
        if status:
            filters["status"] = status.value
        if owner_id:
            filters["owner_id"] = owner_id
        elif not self.rbac.is_admin(user):
            # Non-admin users can only see their own documents
            filters["owner_id"] = user.id
        
        doc_models = await self.repository.list(filters=filters)
        docs = [self._model_to_metadata(m) for m in doc_models]'''
    
    content = content.replace(old_list, new_list)
    
    # Step 9: Replace update_status
    old_update = '''        doc = self._documents.get(document_id)
        if not doc:
            raise NotFoundError(f"Document not found: {document_id}")
        
        doc.status = status
        doc.updated_at = datetime.now(UTC)'''
    
    new_update = '''        try:
            doc_uuid = UUID(document_id)
        except ValueError:
            raise NotFoundError(f"Document not found: {document_id}")
        
        doc_model = await self.repository.get_by_id(doc_uuid)
        if not doc_model:
            raise NotFoundError(f"Document not found: {document_id}")
        
        doc_model.status = status.value
        doc_model.updated_at = datetime.now(UTC)
        await self.repository.update(doc_model)
        await self.session.commit()'''
    
    content = content.replace(old_update, new_update)
    
    # Step 10: Replace delete_document
    old_delete_find = '''        # Find document
        doc = self._documents.get(document_id)
        if not doc:
            raise NotFoundError(f"Document not found: {document_id}")
        
        # Owner or admin can delete
        if doc.owner_id != user.id and not self.rbac.is_admin(user):'''
    
    new_delete_find = '''        # Phase 4: Query from database
        try:
            doc_uuid = UUID(document_id)
        except ValueError:
            raise NotFoundError(f"Document not found: {document_id}")
        
        doc_model = await self.repository.get_by_id(doc_uuid)
        if not doc_model:
            raise NotFoundError(f"Document not found: {document_id}")
        
        # Owner or admin can delete
        if doc_model.owner_id != user.id and not self.rbac.is_admin(user):'''
    
    content = content.replace(old_delete_find, new_delete_find)
    
    old_delete_op = '''        # Soft delete - archive
        doc.status = DocumentStatus.ARCHIVED
        doc.updated_at = datetime.now(UTC)'''
    
    new_delete_op = '''        # Soft delete - archive
        doc_model.status = DocumentStatus.ARCHIVED.value
        doc_model.updated_at = datetime.now(UTC)
        await self.repository.update(doc_model)
        await self.session.commit()'''
    
    content = content.replace(old_delete_op, new_delete_op)
    
    # Write modified content
    with open('src/knowledge/documents.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[OK] DocumentService migrated to database")
    print("  - Added AsyncSession + Repository")
    print("  - Removed Dict storage")
    print("  - Added model converter")
    print("  - Updated all CRUD operations")


if __name__ == "__main__":
    migrate_document_service()
