"""Event handlers for the Vector Gradio interface."""

import gradio as gr
from typing import Optional, Dict, List, Tuple
from .service import VectorWebService


def perform_search(web_service: VectorWebService, query, top_k, collection, selected_documents, search_type):
    """Handle search request."""
    if not query or not query.strip():
        return "Please enter a search query", []
    
    try:
        # Build metadata filter if documents are selected
        metadata_filter = build_metadata_filter(selected_documents)
        
        # Perform search
        result_text, thumbnails = web_service.search_with_thumbnails(
            query=query,
            collection=collection,
            top_k=top_k,
            metadata_filter=metadata_filter,
            search_type=search_type
        )
        
        return result_text, thumbnails
        
    except Exception as e:
        return f"Search error: {str(e)}", []


def ask_ai(web_service: VectorWebService, question, length, collection, selected_documents, search_type):
    """Handle AI question request."""
    if not question or not question.strip():
        return "Please enter a question", []
    
    try:
        # Build metadata filter if documents are selected
        metadata_filter = build_metadata_filter(selected_documents)
        
        # Ask AI
        response, thumbnails = web_service.ask_ai_with_thumbnails(
            question=question,
            collection=collection,
            length=length,
            metadata_filter=metadata_filter,
            search_type=search_type
        )
        
        return response, thumbnails
        
    except Exception as e:
        return f"AI error: {str(e)}", []


def build_metadata_filter(selected_documents):
    """Build metadata filter from selected documents."""
    if not selected_documents:
        return None
    
    # For now, return None as the filter implementation depends on how documents are stored
    # This can be enhanced later when document filtering is needed
    return None


def get_info(web_service: VectorWebService, collection):
    """Get collection info."""
    try:
        return web_service.get_collection_info(collection)
    except Exception as e:
        return f"Error getting collection info: {e}"


def create_new_collection(web_service: VectorWebService, display_name, description):
    """Create new collection."""
    if not display_name or not display_name.strip():
        return "Please enter a collection name"
    
    try:
        result = web_service.create_collection(display_name, description)
        return result
    except Exception as e:
        return f"Error creating collection: {e}"


def refresh_registry_documents(web_service: VectorWebService):
    """Refresh documents list from registry."""
    try:
        documents = web_service.get_registry_documents()
        return gr.update(choices=documents, value=[])
    except Exception as e:
        print(f"Error refreshing registry documents: {e}")
        return gr.update(choices=[], value=[])


def view_document_details(web_service: VectorWebService, selected_documents):
    """View document details."""
    if not selected_documents:
        return "Please select one or more documents to view details"
    
    try:
        return web_service.get_document_details(selected_documents)
    except Exception as e:
        return f"Error getting document details: {e}"


def connect_events(web_service, collection_dropdown, refresh_btn, search_components, 
                  upload_components, info_components, management_components, 
                  document_management_components, collection_documents_components, 
                  delete_components, documents_checkboxgroup):
    """Connect all event handlers."""
    
    # Documents refresh (collection_dropdown is now None, refresh_btn is now refresh_docs_btn)
    if refresh_btn:
        refresh_btn.click(
            fn=lambda: refresh_registry_documents(web_service),
            outputs=documents_checkboxgroup
        )
    
    # Search functionality - only connect if components exist
    if (search_components and 
        'search_btn' in search_components and 
        'search_query' in search_components and
        'num_results' in search_components and
        'search_search_type' in search_components and
        'search_results' in search_components and
        'search_thumbnails' in search_components):
        
        search_components['search_btn'].click(
            fn=lambda query, top_k, collection, selected_docs, search_type: perform_search(
                web_service, query, top_k, collection, selected_docs, search_type
            ),
            inputs=[
                search_components['search_query'],
                search_components['num_results'],
                search_components['search_search_type'],
                documents_checkboxgroup,
                search_components['search_search_type']
            ],
            outputs=[
                search_components['search_results'],
                search_components['search_thumbnails']
            ]
        )
    
    # AI Q&A functionality - only connect if components exist
    if (search_components and 
        'ask_btn' in search_components and 
        'ask_query' in search_components and
        'response_length' in search_components and
        'ask_search_type' in search_components and
        'ai_response' in search_components and
        'ai_thumbnails' in search_components):
        
        search_components['ask_btn'].click(
            fn=lambda question, length, collection, selected_docs, search_type: ask_ai(
                web_service, question, length, collection, selected_docs, search_type
            ),
            inputs=[
                search_components['ask_query'],
                search_components['response_length'],
                search_components['ask_search_type'],
                documents_checkboxgroup,
                search_components['ask_search_type']
            ],
            outputs=[
                search_components['ai_response'],
                search_components['ai_thumbnails']
            ]
        )
    
    # Info functionality - only connect if components exist
    if (info_components and 
        'info_btn' in info_components and 
        'info_output' in info_components):
        
        info_components['info_btn'].click(
            fn=lambda: get_info(web_service, "chunks"),  # Default to chunks collection
            outputs=info_components['info_output']
        )
    
    # Management functionality - only connect if components exist
    if (management_components and 
        'create_btn' in management_components and 
        'new_name_input' in management_components and
        'new_desc_input' in management_components and
        'management_output' in management_components):
        
        management_components['create_btn'].click(
            fn=lambda name, desc: create_new_collection(web_service, name, desc),
            inputs=[
                management_components['new_name_input'],
                management_components['new_desc_input']
            ],
            outputs=management_components['management_output']
        )
    
    # Document management - only connect if components exist
    if (document_management_components and 
        'refresh_docs_btn' in document_management_components and
        'all_documents_list' in document_management_components):
        
        document_management_components['refresh_docs_btn'].click(
            fn=lambda: refresh_registry_documents(web_service),
            outputs=document_management_components['all_documents_list']
        )
    
    if (document_management_components and 
        'view_details_btn' in document_management_components and
        'all_documents_list' in document_management_components and
        'document_details_output' in document_management_components):
        
        document_management_components['view_details_btn'].click(
            fn=lambda docs: view_document_details(web_service, docs),
            inputs=document_management_components['all_documents_list'],
            outputs=document_management_components['document_details_output']
        )