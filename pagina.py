import fitz

doc = fitz.open("AVALIAÇÃO DIAGNÓSTICA - MATEMÁTICA 9º ANO - 10 questões.pdf")
page = doc[0]
pix = page.get_pixmap(dpi=300)
pix.save("pagina72dpi.png")
print("Imagem gerada em escala 1:1 (ponto = pixel)")
