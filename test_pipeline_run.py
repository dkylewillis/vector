from docling_core.types.doc.document import DoclingDocument

from vector.core.models import ConvertedDocument

from vector.core.pipeline import VectorPipeline


pipeline = VectorPipeline()
test_file = r'data/source_documents/GSMM/gsmm_75_85.pdf'
pipeline.run(test_file)


