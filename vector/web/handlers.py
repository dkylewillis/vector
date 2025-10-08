"""Event handlers for the Vector Gradio interface."""

import gradio as gr
from typing import Optional, Dict, List, Tuple
from .service import VectorWebService
from .components import format_usage_metrics


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


# Chat handlers
def send_chat_message(
    web_service: VectorWebService,
    session_id: str,
    message: str,
    chat_history: List,
    response_length: str,
    search_type: str,
    top_k: int,
    selected_documents: List[str]
):
    """Send a message in chat session."""
    # Handle MultimodalTextbox input - extract text from dict if needed
    if isinstance(message, dict):
        message_text = message.get('text', '')
    else:
        message_text = message if message else ''
    
    if not message_text or not message_text.strip():
        return chat_history, [], "Please enter a message"
    
    try:
        # Use empty session_id to let service auto-create or manage sessions
        result = web_service.send_chat_message(
            session_id=session_id or "",
            message=message_text,
            response_length=response_length,
            search_type=search_type,
            top_k=top_k,
            documents=selected_documents
        )
        
        if result.get('success'):
            # Add user message and assistant response to chat history in messages format
            chat_history.append({"role": "user", "content": message_text})
            chat_history.append({"role": "assistant", "content": result['assistant']})
            thumbnails = result.get('thumbnails', [])
            
            # Get the session ID (may be newly created)
            new_session_id = result['session_id']
            
            # Build session info (without metrics)
            info_lines = [f"Session ID: {new_session_id}"]
            
            if result.get('auto_created'):
                info_lines.insert(0, "✨ New session started")
            
            info_lines.append(f"Messages: {result['message_count']} | Results used: {result['results_count']}")
            
            info = "\n".join(info_lines)
            
            # Format usage metrics separately
            usage_metrics = result.get('usage_metrics', {})
            metrics_display = format_usage_metrics(usage_metrics)
            
            return chat_history, thumbnails, info, metrics_display
        else:
            error_msg = f"Error: {result.get('error', 'Unknown error')}"
            return chat_history, [], error_msg, "No metrics available"
            
    except Exception as e:
        return chat_history, [], f"Chat error: {str(e)}", "No metrics available"


def get_info(web_service: VectorWebService, collection):
    """Get collection info."""
    try:
        return web_service.get_collection_info(collection)
    except Exception as e:
        return f"Error getting collection info: {e}"



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
    """Handle adding tags to selected documents.
    
    Returns:
        Tuple of (status_message, updated_tags_list)
    """
    try:
        result = web_service.add_document_tags(document_list, tags_input)
        
        # Get updated tags for refresh
        updated_tags = web_service.get_all_tags()
        
        return (
            result["message"],
            gr.update(choices=updated_tags)  # Refresh tags dropdown
        )
    except Exception as e:
        return f"Error adding tags: {str(e)}", gr.update()


def handle_remove_tags(web_service: VectorWebService, document_list: List[str], tags_input: str):
    """Handle removing tags from selected documents.
    
    Returns:
        Tuple of (status_message, updated_tags_list)
    """
    try:
        result = web_service.remove_document_tags(document_list, tags_input)
        
        # Get updated tags for refresh
        updated_tags = web_service.get_all_tags()
        
        return (
            result["message"],
            gr.update(choices=updated_tags)  # Refresh tags dropdown
        )
    except Exception as e:
        return f"Error removing tags: {str(e)}", gr.update()


def handle_show_current_tags(web_service: VectorWebService, document_list: List[str]):
    """Handle showing current tags for selected documents."""
    try:
        return web_service.get_document_tags(document_list)
    except Exception as e:
        return f"Error retrieving tags: {str(e)}"


def handle_rename_document(web_service: VectorWebService, selected_docs: List[str], new_name: str):
    """Handle renaming a single document.
    
    Args:
        web_service: VectorWebService instance
        selected_docs: List of selected document names
        new_name: New name for the document
        
    Returns:
        Tuple of (status_message, updated_document_list, updated_tags_list)
    """
    if not selected_docs:
        return "❌ Please select a document to rename", gr.update(), gr.update()
    
    if len(selected_docs) > 1:
        return "❌ Please select only ONE document to rename", gr.update(), gr.update()
    
    if not new_name or not new_name.strip():
        return "❌ Please enter a new name", gr.update(), gr.update()
    
    try:
        result = web_service.rename_document(selected_docs[0], new_name.strip())
        
        # Get updated documents and tags for refresh
        updated_documents = web_service.get_registry_documents()
        updated_tags = web_service.get_all_tags()
        
        return (
            result["message"],
            gr.update(choices=updated_documents, value=[]),  # Refresh documents list
            gr.update(choices=updated_tags)  # Refresh tags dropdown
        )
        
    except Exception as e:
        return f"❌ Error renaming document: {str(e)}", gr.update(), gr.update()


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


def process_uploaded_documents_with_refresh(web_service: VectorWebService, files, tags):
    """Handle document processing request and return refreshed document/tag lists."""
    if not files:
        return "Please select one or more documents to process", gr.update(), gr.update()
    
    try:
        # Call the service method to process documents
        result = web_service.process_documents(
            files=files,
            collection="chunks",  # Default collection
            tags=tags
        )
        
        # Get updated documents and tags for refresh
        updated_documents = web_service.get_registry_documents()
        updated_tags = web_service.get_all_tags()
        
        return (
            result,
            gr.update(choices=updated_documents, value=[]),  # Refresh documents list
            gr.update(choices=updated_tags)  # Refresh tags dropdown
        )
        
    except Exception as e:
        return f"Error during document processing: {str(e)}", gr.update(), gr.update()


def connect_events(web_service, search_components, 
                  upload_components, info_components, 
                  document_management_components, 
                  documents_checkboxgroup, tag_filter_dropdown=None):
    """Connect all event handlers."""
    
    # Tag filter functionality
    if tag_filter_dropdown:
        tag_filter_dropdown.change(
            fn=lambda selected_tags: filter_documents_by_tags(web_service, selected_tags),
            inputs=tag_filter_dropdown,
            outputs=documents_checkboxgroup
        )
    
    # Search functionality - only connect if components exist
    if (search_components and 
        'search_query' in search_components and
        'num_results' in search_components and
        'search_search_type' in search_components and
        'search_results' in search_components and
        'search_thumbnails' in search_components):
        
        search_components['search_query'].submit(
            fn=lambda query, top_k, search_type, selected_docs: perform_search(
                web_service, query, top_k, "chunks", selected_docs, search_type
            ),
            inputs=[
                search_components['search_query'],
                search_components['num_results'],
                search_components['search_search_type'],
                documents_checkboxgroup
            ],
            outputs=[
                search_components['search_results'],
                search_components['search_thumbnails']
            ]
        )
    
    # Chat functionality - only connect if components exist
    if (search_components and 
        'chat_message' in search_components):
        
        # Chat settings dialog toggle
        if 'chat_settings_btn' in search_components and 'chat_settings_dialog' in search_components:
            search_components['chat_settings_btn'].click(
                fn=lambda: gr.update(visible=True),
                outputs=search_components['chat_settings_dialog']
            )
        
        if 'chat_settings_close_btn' in search_components and 'chat_settings_dialog' in search_components:
            search_components['chat_settings_close_btn'].click(
                fn=lambda: gr.update(visible=False),
                outputs=search_components['chat_settings_dialog']
            )
        
        # Allow Enter key to send message (session will be auto-created)
        search_components['chat_message'].submit(
            fn=lambda msg, hist, rlen, stype, topk, docs: send_chat_message(
                web_service, "", msg, hist, rlen, stype, topk, docs
            ),
            inputs=[
                search_components['chat_message'],
                search_components['chat_history'],
                search_components['chat_response_length'],
                search_components['chat_search_type'],
                search_components['chat_top_k'],
                documents_checkboxgroup
            ],
            outputs=[
                search_components['chat_history'],
                search_components['chat_thumbnails'],
                search_components['chat_session_info'],
                search_components['chat_metrics']
            ]
        ).then(
            # Clear the message input after sending
            lambda: "",
            outputs=search_components['chat_message']
        )
        
        # Connect Chatbot clear button to end session
        search_components['chat_history'].clear(
            fn=lambda: ([], [], "Chat session ended - start typing to begin a new conversation", "No metrics yet. Send a message to see token usage."),
            outputs=[
                search_components['chat_history'],
                search_components['chat_thumbnails'],
                search_components['chat_session_info'],
                search_components['chat_metrics']
            ]
        )
    
    # Upload/Process functionality - only connect if components exist
    if (upload_components and 
        'process_btn' in upload_components and 
        'file_upload' in upload_components and
        'upload_tags_input' in upload_components and
        'processing_output' in upload_components):
        
        upload_components['process_btn'].click(
            fn=lambda files, tags: process_uploaded_documents_with_refresh(
                web_service, files, tags
            ),
            inputs=[
                upload_components['file_upload'],
                upload_components['upload_tags_input']
            ],
            outputs=[
                upload_components['processing_output'],
                documents_checkboxgroup,
                tag_filter_dropdown
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
            outputs=[
                document_management_components['tag_management_output'],
                tag_filter_dropdown  # Refresh tag dropdown
            ]
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
            outputs=[
                document_management_components['tag_management_output'],
                tag_filter_dropdown  # Refresh tag dropdown
            ]
        )
    
    # Show current tags when documents are selected
    if (document_management_components and 
        'current_tags_display' in document_management_components):
        
        documents_checkboxgroup.change(
            fn=lambda document_list: handle_show_current_tags(web_service, document_list),
            inputs=documents_checkboxgroup,
            outputs=document_management_components['current_tags_display']
        )
    
    # Rename document functionality
    if (document_management_components and 
        'rename_btn' in document_management_components and
        'rename_new_name' in document_management_components and
        'rename_output' in document_management_components):
        
        document_management_components['rename_btn'].click(
            fn=lambda docs, name: handle_rename_document(web_service, docs, name),
            inputs=[
                documents_checkboxgroup,
                document_management_components['rename_new_name']
            ],
            outputs=[
                document_management_components['rename_output'],
                documents_checkboxgroup,
                tag_filter_dropdown
            ]
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