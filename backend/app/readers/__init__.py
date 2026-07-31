from app.readers.csv_reader import CsvDocumentReader
from app.readers.docx_reader import DocxDocumentReader
from app.readers.eml_reader import EmlDocumentReader
from app.readers.html_reader import HtmlDocumentReader
from app.readers.pdf_reader import PdfDocumentReader
from app.readers.pptx_reader import PptxDocumentReader
from app.readers.registry import DocumentReaderRegistry
from app.readers.text_reader import TextDocumentReader
from app.readers.xlsx_reader import XlsxDocumentReader


def create_document_reader_registry() -> DocumentReaderRegistry:
    return DocumentReaderRegistry([
        PdfDocumentReader(), DocxDocumentReader(), XlsxDocumentReader(), CsvDocumentReader(),
        PptxDocumentReader(), TextDocumentReader(), HtmlDocumentReader(), EmlDocumentReader(),
    ])
