from docling_core.types.doc.document import DoclingDocument

from vector.core.models import ConvertedDocument

filename = r'data/converted_documents/bf9345120a19ee4110d3221c40a1636580e1c96429f2d12e2cd09dbc82429d85/docling_document.json'

converted_doc = ConvertedDocument.load_converted_document(filename)

#artifacts = converted_doc.get_chunks()


artifacts = converted_doc.doc.pictures

for artifact in artifacts:
    print(artifact.self_ref)
    print(artifact.caption_text(converted_doc.doc))
    print(artifact.get_image(converted_doc.doc))

    print("----")