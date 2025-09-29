"""Event handlers for the Vector Gradio interface."""

import gradio as gr
from typing import Optional, Dict, List, Tuple
from .service import VectorWebService


def perform_search(web_service: VectorWebService, query, top_k, collection, selected_documents, search_type):
    """Handle search request."""
    if not query or not query.strip():
        return "Please enter a search query", []
    
    try:
        
        # Perform search
        result_text, thumbnails = web_service.search_with_thumbnails(
            query=query,
            collection=collection,
            top_k=top_k,
            search_type=search_type,
            documents=selected_documents
        )
        
        return result_text, thumbnails
        
    except Exception as e:
        return f"Search error: {str(e)}", []


def ask_ai(web_service: VectorWebService, question, length, collection, selected_documents, search_type):
    """Handle AI question request."""
    if not question or not question.strip():
        return "Please enter a question", []
    
    try:

        # Ask AI
        response, thumbnails = web_service.ask_ai_with_thumbnails(
            question=question,
            collection=collection,
            length=length,
            search_type=search_type,
            documents=selected_documents
        )
        
        return response, thumbnails
        
    except Exception as e:
        return f"AI error: {str(e)}", []


def get_info(web_service: VectorWebService, collection):
    """Get collection info."""
    try:
        return web_service.get_collection_info(collection)
    except Exception as e:
        return f"Error getting collection info: {e}"



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


def delete_selected_documents(web_service: VectorWebService, selected_documents, confirm_delete):
    """Handle document deletion request."""
    if not selected_documents:
        return "Please select one or more documents to delete"
    
    if not confirm_delete:
        return "Please check the confirmation box to proceed with deletion"
    
    try:
        # Call the service method to delete documents
        result = web_service.delete_documents(selected_documents, "chunks")  # Default collection
        
        # Provide more detailed feedback
        deleted_count = len(selected_documents)
        success_message = f"Deletion request processed for {deleted_count} document(s):\n"
        for doc in selected_documents:
            success_message += f"• {doc}\n"
        
        return f"{success_message}\n{result}"
        
    except Exception as e:
        return f"Error during document deletion: {str(e)}"


def handle_add_tags(web_service: VectorWebService, document_list: List[str], tags_input: str):
    """Handle adding tags to selected documents."""
    try:
        result = web_service.add_document_tags(document_list, tags_input)
        return result["message"]
    except Exception as e:
        return f"Error adding tags: {str(e)}"


def handle_remove_tags(web_service: VectorWebService, document_list: List[str], tags_input: str):
    """Handle removing tags from selected documents."""
    try:
        result = web_service.remove_document_tags(document_list, tags_input)
        return result["message"]
    except Exception as e:
        return f"Error removing tags: {str(e)}"


def handle_show_current_tags(web_service: VectorWebService, document_list: List[str]):
    """Handle showing current tags for selected documents."""
    try:
        return web_service.get_document_tags(document_list)
    except Exception as e:
        return f"Error retrieving tags: {str(e)}"


def refresh_tags_and_documents(web_service: VectorWebService, selected_tags: Optional[List[str]] = None):
    """Refresh both tags dropdown and document list based on tag filter."""
    try:
        # Get all available tags
        all_tags = web_service.get_all_tags()
        
        # Get filtered documents based on selected tags
        if selected_tags:
            filtered_documents = web_service.get_documents_by_tags(selected_tags)
        else:
            filtered_documents = web_service.get_registry_documents()
        
        # Return updates for both components
        return (
            gr.update(choices=all_tags),  # Update tag dropdown choices
            gr.update(choices=filtered_documents, value=[])  # Update documents and clear selection
        )
    except Exception as e:
        print(f"Error refreshing tags and documents: {e}")
        return (
            gr.update(choices=[]),
            gr.update(choices=[], value=[])
        )


def filter_documents_by_tags(web_service: VectorWebService, selected_tags: Optional[List[str]] = None):
    """Filter documents based on selected tags."""
    try:
        if selected_tags:
            filtered_documents = web_service.get_documents_by_tags(selected_tags)
        else:
            filtered_documents = web_service.get_registry_documents()
        
        return gr.update(choices=filtered_documents, value=[])
    except Exception as e:
        print(f"Error filtering documents by tags: {e}")
        return gr.update(choices=[], value=[])


def process_uploaded_documents(web_service: VectorWebService, files, tags):
    """Handle document processing request."""
    if not files:
        return "Please select one or more documents to process"
    
    try:
        # Call the service method to process documents
        result = web_service.process_documents(
            files=files,
            collection="chunks",  # Default collection
            tags=tags
        )
        
        return result
        
    except Exception as e:
        return f"Error during document processing: {str(e)}"


def connect_events(web_service, refresh_btn, search_components, 
                  upload_components, info_components, 
                  document_management_components, 
                  documents_checkboxgroup, tag_filter_dropdown=None):
    """Connect all event handlers."""
    
    # Documents refresh (collection_dropdown is now None, refresh_btn is now refresh_docs_btn)
    if refresh_btn:
        if tag_filter_dropdown:
            refresh_btn.click(
                fn=lambda selected_tags: refresh_tags_and_documents(web_service, selected_tags),
                inputs=tag_filter_dropdown,
                outputs=[tag_filter_dropdown, documents_checkboxgroup]
            )
        else:
            refresh_btn.click(
                fn=lambda: refresh_registry_documents(web_service),
                outputs=documents_checkboxgroup
            )
    
    # Tag filter functionality
    if tag_filter_dropdown:
        tag_filter_dropdown.change(
            fn=lambda selected_tags: filter_documents_by_tags(web_service, selected_tags),
            inputs=tag_filter_dropdown,
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
                search_components['search_search_type'],
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
    
    # Upload/Process functionality - only connect if components exist
    if (upload_components and 
        'process_btn' in upload_components and 
        'file_upload' in upload_components and
        'upload_tags_input' in upload_components and
        'processing_output' in upload_components):
        
        upload_components['process_btn'].click(
            fn=lambda files, tags: process_uploaded_documents(
                web_service, files, tags
            ),
            inputs=[
                upload_components['file_upload'],
                upload_components['upload_tags_input']
            ],
            outputs=upload_components['processing_output']
        )
    
    # Info functionality - only connect if components exist
    if (info_components and 
        'info_btn' in info_components and 
        'info_output' in info_components):
        
        info_components['info_btn'].click(
            fn=lambda: get_info(web_service, "chunks"),  # Default to chunks collection
            outputs=info_components['info_output']
        )
    
    # Document management - only connect if components exist
    if (document_management_components and 
        'view_details_btn' in document_management_components and
        'document_details_output' in document_management_components):
        
        document_management_components['view_details_btn'].click(
            fn=lambda docs: view_document_details(web_service, docs),
            inputs=documents_checkboxgroup,  # Use main selected documents from left panel
            outputs=document_management_components['document_details_output']
        )
    
    # Tag management functionality - only connect if components exist
    if (document_management_components and 
        'add_tags_btn' in document_management_components and
        'add_tags_input' in document_management_components and
        'tag_management_output' in document_management_components):
        
        document_management_components['add_tags_btn'].click(
            fn=lambda tags_input, document_list: handle_add_tags(web_service, document_list, tags_input),
            inputs=[
                document_management_components['add_tags_input'],
                documents_checkboxgroup
            ],
            outputs=document_management_components['tag_management_output']
        )
    
    if (document_management_components and 
        'remove_tags_btn' in document_management_components and
        'remove_tags_input' in document_management_components and
        'tag_management_output' in document_management_components):
        
        document_management_components['remove_tags_btn'].click(
            fn=lambda tags_input, document_list: handle_remove_tags(web_service, document_list, tags_input),
            inputs=[
                document_management_components['remove_tags_input'],
                documents_checkboxgroup
            ],
            outputs=document_management_components['tag_management_output']
        )
    
    # Show current tags when documents are selected
    if (document_management_components and 
        'current_tags_display' in document_management_components):
        
        documents_checkboxgroup.change(
            fn=lambda document_list: handle_show_current_tags(web_service, document_list),
            inputs=documents_checkboxgroup,
            outputs=document_management_components['current_tags_display']
        )
    
    # Delete functionality - now part of document management
    if (document_management_components and 
        'delete_selected_btn' in document_management_components and
        'confirm_delete_checkbox' in document_management_components and
        'delete_output' in document_management_components):
        
        document_management_components['delete_selected_btn'].click(
            fn=lambda selected_docs, confirm: delete_selected_documents(
                web_service, selected_docs, confirm
            ),
            inputs=[
                documents_checkboxgroup,  # Selected documents from main panel
                document_management_components['confirm_delete_checkbox']
            ],
            outputs=document_management_components['delete_output']
        )