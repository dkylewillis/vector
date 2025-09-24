from docling_core.types.doc.document import DoclingDocument

from vector.core.models import ConvertedDocument

from vector.core.pipeline import VectorPipeline


pipeline = VectorPipeline()
test_file = r'data/source_documents/Coweta/ordinances/APPENDIX_A___ZONING_AND_DEVELOPMENT.docx'
pipeline.run(test_file)


