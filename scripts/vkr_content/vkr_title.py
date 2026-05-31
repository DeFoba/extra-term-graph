from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

def get_content():
    blocks = []
    
    # Титульный лист — текстовые блоки с центровкой
    blocks.append({"type": "p", "text": "ЧАСТНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ ВЫСШЕГО ОБРАЗОВАНИЯ", "align": "CENTER", "indent": None, "font_size": 14})
    blocks.append({"type": "p", "text": "«МОСКОВСКИЙ УНИВЕРСИТЕТ ИМ. С.Ю. ВИТТЕ»", "align": "CENTER", "indent": None, "font_size": 14, "bold": True})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "Факультет информационных технологий", "align": "CENTER", "indent": None})
    blocks.append({"type": "p", "text": "Кафедра информационных систем", "align": "CENTER", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА", "align": "CENTER", "indent": None, "bold": True})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "на тему:", "align": "CENTER", "indent": None})
    blocks.append({"type": "p", "text": "«Построение графа терминов и аннотирование научных публикаций на основе статистического и нейросетевого анализа»", "align": "CENTER", "indent": None, "bold": True})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "Выполнил: студент группы _____________", "indent": None})
    blocks.append({"type": "p", "text": "ФИО: _________________________________", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "Научный руководитель: _________________", "indent": None})
    blocks.append({"type": "p", "text": "Ученая степень, звание: ________________", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "", "indent": None})
    blocks.append({"type": "p", "text": "Москва, 2026", "align": "CENTER", "indent": None})
    blocks.append({"type": "pb"})
    
    return blocks
