import fitz

doc = fitz.open("modelo_gabarito_base.pdf")
page = doc[0]
pix = page.get_pixmap(dpi=72)
pix.save("pagina72dpi.png")
print("Imagem gerada em escala 1:1 (ponto = pixel)")
