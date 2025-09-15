"""Event handlers for the Vector Gradio interface."""

import gradio as gr
from typing import Optional, Dict, List, Tuple
from .service import VectorWebService

# Add these functions (replace the existing method versions)

def perform_search(web_service: VectorWebService, query, top_k, collection, selected_documents, search_type):
    """Handle search request with thumbnails."""
    metadata_filter = build_metadata_filter(selected_documents)
    
    # Debug info for the user
    if metadata_filter:
        filter_files = metadata_filter['filename']
        print(f"🔍 Filtering search to {len(filter_files)} selected documents: {filter_files}")
    else:
        print("🔍 No document filter applied - searching all documents in collection")
    
    print(f"🔍 Using search type: {search_type}")
    
    # Use the new method that returns (text, thumbnails)
    return web_service.search_with_thumbnails(query, collection, int(top_k), metadata_filter, search_type)

def ask_ai(web_service: VectorWebService, question, length, collection, selected_documents, search_type):
    """Handle AI question request with thumbnails."""
    metadata_filter = build_metadata_filter(selected_documents)
    
    # Debug info for the user
    if metadata_filter:
        filter_files = metadata_filter['filename']
        print(f"💬 Filtering AI context to {len(filter_files)} selected documents: {filter_files}")
    else:
        print("💬 No document filter applied - using all documents in collection for context")
    
    print(f"💬 Using search type: {search_type}")
    
    # Use the new method that returns (text, thumbnails)
    response_text, thumbnails = web_service.ask_ai_with_thumbnails(question, collection, length, metadata_filter, search_type)
    
    # Show which filters were applied
    filter_info = ""
    if metadata_filter:
        count = len(metadata_filter['filename'])
        filter_info = f" [Documents: {count} selected]"
    
    formatted_response = f"[Collection: {collection}]{filter_info}\n\n{response_text}"
    return formatted_response, thumbnails

def build_metadata_filter(selected_documents):
    """Build metadata filter from selected documents."""
    # If no documents are selected, return None (no filter)
    if not selected_documents:
        return None
    
    # Extract filenames from the document list (remove chunk count)
    # Format: "filename.pdf (15 chunks)" -> "filename.pdf"
    filenames = []
    for doc in selected_documents:
        if ' (' in doc and doc.endswith('chunks)'):
            # Handle format: "filename.pdf (15 chunks)"
            filename = doc.split(' (')[0]
            filenames.append(filename)
        elif ' (' in doc:
            # Handle other parenthetical formats
            filename = doc.split(' (')[0]
            filenames.append(filename)
        else:
            # No parentheses, use as-is
            filenames.append(doc)
    
    # Remove duplicates while preserving order
    unique_filenames = []
    for filename in filenames:
        if filename not in unique_filenames:
            unique_filenames.append(filename)
    
    # Build filter with filename list - VectorDatabase expects a simple list format
    # The _build_filter method will handle converting this to Qdrant filter format
    filters = {'filename': unique_filenames}
    return filters

def process_files(web_service: VectorWebService, files, current_collection, source, force):
    """Handle document processing."""
    if not files:
        return "No files selected."
    
    if not current_collection:
        return "❌ Please select a collection first."
    
    # Process documents
    source_value = None if source == "auto" else source
    result = web_service.process_documents(files, current_collection, source_value, force)
    
    # Add success message with collection info
    success_msg = f"✅ Documents processed successfully in collection '{current_collection}'!"
    
    return result + "\n" + success_msg if result else success_msg


def get_info(web_service: VectorWebService, collection):
    """Get collection information."""
    return web_service.get_collection_info(collection)


def get_metadata_summary(web_service: VectorWebService, collection):
    """Get metadata summary for collection."""
    return web_service.get_metadata_summary(collection)


def delete_documents(web_service: VectorWebService, selected_documents, collection):
    """Delete selected documents from the collection."""
    if not selected_documents:
        return "Please select documents to delete from the Documents in Collection section."
    
    # Extract filenames from the selected documents (remove chunk count)
    filenames = []
    for doc in selected_documents:
        if ' (' in doc and doc.endswith('chunks)'):
            # Handle format: "filename.pdf (15 chunks)"
            filename = doc.split(' (')[0]
            filenames.append(filename)
        elif ' (' in doc:
            # Handle other parenthetical formats
            filename = doc.split(' (')[0]
            filenames.append(filename)
        else:
            # No parentheses, use as-is
            filenames.append(doc)
    
    # Remove duplicates while preserving order
    unique_filenames = []
    for filename in filenames:
        if filename not in unique_filenames:
            unique_filenames.append(filename)
    
    result = web_service.delete_documents(unique_filenames, collection)
    return result


def update_collection_documents(web_service: VectorWebService, collection):
    """Update the documents list based on selected collection."""
    documents = web_service.get_collection_documents(collection)
    
    return (
        gr.CheckboxGroup(choices=documents, value=[])  # documents_checkboxgroup
    )


def refresh_collections(web_service: VectorWebService):
    """Refresh the collections dropdown."""
    return gr.Dropdown(choices=web_service.get_collections())


def list_all_collections(web_service: VectorWebService):
    """List all collections with their metadata."""
    return web_service.list_collections()


def create_new_collection(web_service: VectorWebService, display_name, description):
    """Create a new collection."""
    return web_service.create_collection(display_name, description)


def rename_collection(web_service: VectorWebService, old_name, new_name):
    """Rename a collection's display name."""
    return web_service.rename_collection(old_name, new_name)


def delete_collection(web_service: VectorWebService, collection_name, force_confirmed):
    """Delete a collection."""
    if not collection_name or not collection_name.strip():
        return "❌ Collection display name is required"
    
    if not force_confirmed:
        return "❌ Please confirm deletion by checking the checkbox"
    
    return web_service.delete_collection(collection_name)


# Document Management Handlers

def refresh_all_documents(web_service: VectorWebService):
    """Refresh the list of all available documents."""
    documents = web_service.get_all_documents()
    return gr.CheckboxGroup(choices=documents, value=[])


def view_document_details(web_service: VectorWebService, selected_documents):
    """View details for selected documents."""
    if not selected_documents:
        return "Please select documents to view details."
    
    return web_service.get_document_details(selected_documents)


def delete_documents_permanently(web_service: VectorWebService, selected_documents, confirmed):
    """Permanently delete documents from the system."""
    if not selected_documents:
        return "Please select documents to delete."
    
    if not confirmed:
        return "❌ Please confirm deletion by checking the checkbox."
    
    return web_service.delete_documents_permanently(selected_documents)


def get_documents_to_delete(web_service: VectorWebService):
    """Get list of documents that can be deleted."""
    documents = web_service.get_all_documents()
    return gr.CheckboxGroup(choices=documents, value=[])


# Collection Documents Handlers

def get_available_documents_for_collection(web_service: VectorWebService, collection):
    """Get documents that are not in the current collection."""
    available_documents = web_service.get_available_documents_for_collection(collection)
    return gr.CheckboxGroup(choices=available_documents, value=[])


def add_documents_to_collection(web_service: VectorWebService, selected_documents, collection):
    """Add selected documents to the current collection."""
    if not selected_documents:
        return "Please select documents to add to the collection."
    
    if not collection:
        return "❌ No collection selected."
    
    return web_service.add_documents_to_collection(selected_documents, collection)


def remove_documents_from_collection(web_service: VectorWebService, selected_documents, collection):
    """Remove selected documents from the current collection."""
    if not selected_documents:
        return "Please select documents to remove from the collection."
    
    if not collection:
        return "❌ No collection selected."
    
    return web_service.remove_documents_from_collection(selected_documents, collection)


def connect_events(web_service: VectorWebService, collection_dropdown, refresh_btn,
                  search_components, upload_components, info_components,
                  management_components, document_management_components,
                  collection_documents_components, delete_components,
                  documents_checkboxgroup):
    """Connect all event handlers to UI components."""
    
    # Collection refresh
    refresh_btn.click(
        fn=lambda: refresh_collections(web_service),
        outputs=collection_dropdown
    )
    
    # Update documents when collection changes
    collection_dropdown.change(
        fn=lambda c: update_collection_documents(web_service, c),
        inputs=[collection_dropdown],
        outputs=[documents_checkboxgroup]
    )
    
    # Search & Ask handlers
    search_components['search_btn'].click(
        fn=lambda q, k, c, docs, search_type: perform_search(web_service, q, k, c, docs, search_type),
        inputs=[search_components['search_query'], search_components['num_results'], 
               collection_dropdown, documents_checkboxgroup, search_components['search_search_type']],
        outputs=[search_components['search_results'], search_components['search_thumbnails']]  # Add thumbnails output
    )
    
    search_components['ask_btn'].click(
        fn=lambda q, l, c, docs, search_type: ask_ai(web_service, q, l, c, docs, search_type),
        inputs=[search_components['ask_query'], search_components['response_length'],
               collection_dropdown, documents_checkboxgroup, search_components['ask_search_type']],
        outputs=[search_components['ai_response'], search_components['ai_thumbnails']]  # Add thumbnails output
    )
    
    # Upload handlers
    upload_components['process_btn'].click(
        fn=lambda files, curr_coll, src, force: process_files(
            web_service, files, curr_coll, src, force),
        inputs=[upload_components['file_upload'], collection_dropdown, 
               upload_components['source_dropdown'], upload_components['force_reprocess']],
        outputs=upload_components['processing_output']
    )
    
    # Info handlers
    info_components['info_btn'].click(
        fn=lambda c: get_info(web_service, c),
        inputs=[collection_dropdown],
        outputs=info_components['collection_info']
    )
    
    info_components['metadata_btn'].click(
        fn=lambda c: get_metadata_summary(web_service, c),
        inputs=[collection_dropdown],
        outputs=info_components['metadata_summary']
    )
    
    # Delete documents handlers
    delete_components['delete_btn'].click(
        fn=lambda docs, c: delete_documents(web_service, docs, c),
        inputs=[documents_checkboxgroup, collection_dropdown],
        outputs=delete_components['delete_output']
    )
    
    # Collection management handlers
    management_components['list_collections_btn'].click(
        fn=lambda: list_all_collections(web_service),
        outputs=management_components['collections_list']
    )
    
    management_components['create_collection_btn'].click(
        fn=lambda name, desc: create_new_collection(web_service, name, desc),
        inputs=[management_components['create_display_name'], 
               management_components['create_description']],
        outputs=management_components['create_output']
    )
    
    management_components['rename_collection_btn'].click(
        fn=lambda old, new: rename_collection(web_service, old, new),
        inputs=[management_components['rename_old_name'], 
               management_components['rename_new_name']],
        outputs=management_components['rename_output']
    )
    
    management_components['delete_collection_btn'].click(
        fn=lambda name, confirmed: delete_collection(web_service, name, confirmed),
        inputs=[management_components['delete_collection_name'], 
               management_components['delete_force_checkbox']],
        outputs=management_components['delete_collection_output']
    )
    
    # Document Management handlers
    document_management_components['refresh_docs_btn'].click(
        fn=lambda: refresh_all_documents(web_service),
        outputs=document_management_components['all_documents_list']
    )
    
    document_management_components['view_doc_details_btn'].click(
        fn=lambda docs: view_document_details(web_service, docs),
        inputs=[document_management_components['all_documents_list']],
        outputs=document_management_components['document_details']
    )
    
    document_management_components['delete_documents_btn'].click(
        fn=lambda docs, confirmed: delete_documents_permanently(web_service, docs, confirmed),
        inputs=[document_management_components['documents_to_delete'], 
               document_management_components['confirm_delete_checkbox']],
        outputs=document_management_components['delete_documents_output']
    ).then(
        # After deletion, refresh all document lists
        fn=lambda: refresh_all_documents(web_service),
        outputs=document_management_components['all_documents_list']
    ).then(
        fn=lambda: refresh_all_documents(web_service),
        outputs=document_management_components['documents_to_delete']
    ).then(
        # Also refresh the collection documents list
        fn=lambda collection: update_collection_documents(web_service, collection),
        inputs=[collection_dropdown],
        outputs=documents_checkboxgroup
    ).then(
        # And refresh available documents for collection
        fn=lambda collection: get_available_documents_for_collection(web_service, collection),
        inputs=[collection_dropdown],
        outputs=collection_documents_components['available_documents']
    )
    
    # Auto-populate documents_to_delete when refresh button is clicked
    document_management_components['refresh_docs_btn'].click(
        fn=lambda: refresh_all_documents(web_service),
        outputs=document_management_components['documents_to_delete']
    )
    
    # Collection Documents handlers
    collection_documents_components['add_to_collection_btn'].click(
        fn=lambda docs, collection: add_documents_to_collection(web_service, docs, collection),
        inputs=[collection_documents_components['available_documents'], collection_dropdown],
        outputs=collection_documents_components['add_to_collection_output']
    )
    
    collection_documents_components['remove_from_collection_btn'].click(
        fn=lambda docs, collection: remove_documents_from_collection(web_service, docs, collection),
        inputs=[documents_checkboxgroup, collection_dropdown],
        outputs=collection_documents_components['remove_from_collection_output']
    )
    
    # Update available documents when collection changes
    collection_dropdown.change(
        fn=lambda collection: get_available_documents_for_collection(web_service, collection),
        inputs=[collection_dropdown],
        outputs=[collection_documents_components['available_documents']]
    )