from pdf2image import convert_from_path
import logging

logger = logging.getLogger('GabaritoApp.Converter')

def converter_pdf_em_imagens(pdf_path, dpi=300):
    """
    Converte o PDF em uma lista de imagens usando o dpi informado.
    Assumimos que o Poppler está no PATH.
    """
    logger.info(f"Convertendo PDF: {pdf_path} (DPI: {dpi})")
    try:
        imagens = convert_from_path(pdf_path, dpi=dpi)
        logger.info(f"PDF convertido com sucesso. Páginas extraídas: {len(imagens)}")
        return imagens
    except Exception as e:
        logger.error(f"Erro na conversão do PDF: {e}")
        return []
