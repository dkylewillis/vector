from docling_core.types.doc.document import DoclingDocument

from vector.core.models import ConvertedDocument

from vector.core.pipeline import VectorPipeline

filename = r'data/converted_documents/gsmm_75_85_document.json'
converted_doc = ConvertedDocument.load_converted_document(filename)

#artifacts = converted_doc.get_chunks()


#artifacts = converted_doc.doc.pictures

artifacts = converted_doc.get_artifacts()

for artifact in artifacts:
    print(artifact.image)
    print("----")


# pipeline = VectorPipeline()
# test_file = r'data/source_documents/GSMM/gsmm_75_85.pdf'
# pipeline.convert(test_file)