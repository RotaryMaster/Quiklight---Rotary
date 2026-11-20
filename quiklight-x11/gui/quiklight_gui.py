#!/usr/bin/env python3
# Quiklight GUI (Qt / PySide6) — janela de configurações + ícone na bandeja
#   quiklight-gui            abre a janela
#   quiklight-gui --tray     inicia só o ícone da bandeja
import copy, json, os, shutil, subprocess, sys, threading, time, tomllib
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QRect, QRectF, QPoint, QPointF, QSize, QStandardPaths, QAbstractNativeEventFilter, qVersion
from PySide6.QtGui import QAction, QColor, QConicalGradient, QIcon, QPainter, QPalette, QPen, QPixmap, QBrush, QGuiApplication, QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import (
    QApplication, QLayout, QCheckBox, QColorDialog, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget, QListWidgetItem,
)

APP_ID = "quiklight-gui-qt"
APP_VERSION = "29-adaptive-exp1"
APP_YEAR = "2026"
CHANGES = "Detecção de barras pretas reescrita: varre as bordas, ignora letras e objetos no centro da tela e volta ao normal quando a imagem reaparece."
IS_WIN = os.name == "nt"
NOWIN = 0x08000000 if IS_WIN else 0   # CREATE_NO_WINDOW

LANG = "pt"
TR = {'Natural': ('Natural', 'Natural'), 'Vívido': ('Vivid', 'Vívido'), 'Neon': ('Neon', 'Neón'), 'Cinema (quente suave)': ('Cinema (soft warm)', 'Cine (cálido suave)'), 'Quente': ('Warm', 'Cálido'), 'Frio': ('Cool', 'Frío'), 'Escuro': ('Dark', 'Oscuro'), 'Claro': ('Light', 'Claro'), 'Meia-noite': ('Midnight', 'Medianoche'), 'Floresta': ('Forest', 'Bosque'), 'Pôr do sol': ('Sunset', 'Atardecer'), 'Cores das bordas': ('Edge colors', 'Colores de los bordes'), 'Cor dominante': ('Dominant color', 'Color dominante'), 'Cor dominante esquerda/direita': ('Dominant color left/right', 'Color dominante izquierda/derecha'), 'Cor dominante nas bordas': ('Dominant color on edges', 'Color dominante en los bordes'), 'Cores selecionadas': ('Selected colors', 'Colores seleccionados'), 'Breathing (respiração suave)': ('Breathing (soft)', 'Breathing (respiración suave)'), 'Pulsing suave': ('Soft pulsing', 'Pulso suave'), 'Rainbow (espectro completo)': ('Rainbow (full spectrum)', 'Arcoíris (espectro completo)'), 'Fade entre as cores da paleta': ('Fade between palette colors', 'Fundido entre los colores de la paleta'), 'Cometa': ('Comet', 'Cometa'), 'Aurora (paleta em movimento)': ('Aurora (moving palette)', 'Aurora (paleta en movimiento)'), 'Fogo': ('Fire', 'Fuego'), 'Esquerda': ('Left', 'Izquierda'), 'Topo': ('Top', 'Arriba'), 'Direita': ('Right', 'Derecha'), 'Embaixo': ('Bottom', 'Abajo'), 'Home': ('Home', 'Inicio'), 'Iluminação': ('Lighting', 'Iluminación'), 'Cores': ('Colors', 'Colores'), 'Captura': ('Capture', 'Captura'), 'LEDs e fitas': ('LEDs and strips', 'LEDs y cintas'), 'Ao vivo': ('Live', 'En vivo'), 'Presets': ('Presets', 'Preajustes'), 'Hardware': ('Hardware', 'Hardware'), 'Sistema': ('System', 'Sistema'), 'Estático': ('Static', 'Estático'), 'Efeitos': ('Effects', 'Efectos'), 'Dinâmico': ('Dynamic', 'Dinámico'), 'Dinâmico (captura de tela)': ('Dynamic (screen capture)', 'Dinámico (captura de pantalla)'), 'Custo do aplicativo': ('App cost', 'Costo de la aplicación'), 'Modo de iluminação': ('Lighting mode', 'Modo de iluminación'), 'Respeitar o brilho da cena': ('Respect scene brightness', 'Respetar el brillo de la escena'), 'Preferência por cores vibrantes': ('Preference for vibrant colors', 'Preferencia por colores vibrantes'), 'Fidelidade da cor': ('Color fidelity', 'Fidelidad del color'), 'Suavidade da troca': ('Change smoothness', 'Suavidad del cambio'), 'Profundidade das áreas (%)': ('Area depth (%)', 'Profundidad de las áreas (%)'), 'Velocidade': ('Speed', 'Velocidad'), 'Brilho mínimo %': ('Minimum brightness %', 'Brillo mínimo %'), 'Completar slots vazios com cores aleatórias': ('Fill empty slots with random colors', 'Completar espacios vacíos con colores aleatorios'), 'Brilho e proteção': ('Brightness and protection', 'Brillo y protección'), 'Brilho (%)': ('Brightness (%)', 'Brillo (%)'), 'Limite de potência (%)': ('Power limit (%)', 'Límite de potencia (%)'), 'Limite de variação (0 = desligado)': ('Change-rate limit (0 = off)', 'Límite de variación (0 = apagado)'), 'Cores (modos dinâmicos)': ('Colors (dynamic modes)', 'Colores (modos dinámicos)'), 'Melhor acurácia de cores (balanço de branco, gamma por canal e proteção de neutros)': ('Better color accuracy (white balance, per-channel gamma and neutral protection)', 'Mejor precisión de color (balance de blancos, gamma por canal y protección de neutros)'), 'Saturação': ('Saturation', 'Saturación'), 'Contraste': ('Contrast', 'Contraste'), 'Gamma': ('Gamma', 'Gamma'), 'Quadros por segundo': ('Frames per second', 'Fotogramas por segundo'), 'Limitar a captura ao fps': ('Limit capture to fps', 'Limitar la captura al fps'), 'Acurácia (ative a caixa acima)': ('Accuracy (enable the box above)', 'Precisión (active la casilla de arriba)'), 'Área de captura da tela': ('Screen capture area', 'Área de captura de pantalla'), 'Espessura da faixa': ('Band thickness', 'Grosor de la franja'), 'Hardware da fita': ('Strip hardware', 'Hardware de la cinta'), 'Preset carregado. Clique em Aplicar para usar.': ('Preset loaded. Click Apply to use it.', 'Preajuste cargado. Haga clic en Aplicar para usarlo.'), 'Relatório e backup': ('Report and backup', 'Informe y copia de seguridad'), 'Registro do programa': ('Program log', 'Registro del programa'), 'Relatório copiado. Cole na conversa (Ctrl+V).': ('Report copied. Paste it in the chat (Ctrl+V).', 'Informe copiado. Péguelo en la conversación (Ctrl+V).'), 'Valores padrão carregados (LEDs e fitas mantidos). Clique em Aplicar.': ('Default values loaded (LEDs and strips kept). Click Apply.', 'Valores predeterminados cargados (LEDs y cintas se mantienen). Haga clic en Aplicar.'), 'Ligar': ('Start', 'Encender'), 'Desligar': ('Stop', 'Apagar'), 'Reiniciar': ('Restart', 'Reiniciar'), 'Resetar valores': ('Reset values', 'Restablecer valores'), 'Tempo real': ('Real time', 'Tiempo real'), 'Aplicar': ('Apply', 'Aplicar'), 'Nenhum (valores personalizados)': ('None (custom values)', 'Ninguno (valores personalizados)'), 'Suavização entre cores (0 = instantâneo)': ('Smoothing between colors (0 = instant)', 'Suavizado entre colores (0 = instantáneo)'), 'Uma só cor para toda a fita: a cor mais marcante da área capturada.': ('One color for the whole strip: the most striking color of the captured area.', 'Un solo color para toda la cinta: el color más marcado del área capturada.'), 'escolher um tema...': ('choose a theme...', 'elegir un tema...'), 'Modo vívido': ('Vivid mode', 'Modo vívido'), 'Escolher outra tela': ('Choose another screen', 'Elegir otra pantalla'), 'Borda': ('Edge', 'Borde'), 'Um pouco para dentro': ('A bit inward', 'Un poco hacia adentro'), 'Centro': ('Center', 'Centro'), 'Escolha a tela da fita na janela do KDE.': ("Pick the strip's screen in the KDE window.", 'Elija la pantalla de la cinta en la ventana de KDE.'), 'Esquerda + topo + direita': ('Left + top + right', 'Izquierda + arriba + derecha'), 'Moldura completa (com embaixo)': ('Full frame (with bottom)', 'Marco completo (con abajo)'), 'Adicionar trecho': ('Add segment', 'Añadir tramo'), 'Adicionar trecho em outra fita (Fita 2)': ('Add segment on another strip (Strip 2)', 'Añadir tramo en otra cinta (Cinta 2)'), 'Mostra o que está sendo enviado à fita agora. Apagado = LED desligado.': ('Shows what is being sent to the strip now. Dark = LED off.', 'Muestra lo que se envía a la cinta ahora. Oscuro = LED apagado.'), 'Atualizar': ('Refresh', 'Actualizar'), 'O controlador não informa a quantidade real de LEDs; confira pelo teste ao vivo.': ('The controller does not report the real LED count; check it in the live view.', 'El controlador no informa la cantidad real de LEDs; compruébela en la vista en vivo.'), 'Referência: USB 2.0 entrega 500 mA e USB 3.x entrega 900 mA por porta.': ('Reference: USB 2.0 delivers 500 mA and USB 3.x delivers 900 mA per port.', 'Referencia: USB 2.0 entrega 500 mA y USB 3.x entrega 900 mA por puerto.'), 'Excluir': ('Delete', 'Eliminar'), 'Nome do novo preset': ('New preset name', 'Nombre del nuevo preajuste'), 'Salvar preset': ('Save preset', 'Guardar preajuste'), '(escolha um preset)': ('(choose a preset)', '(elija un preajuste)'), 'Digite um nome para o preset.': ('Type a name for the preset.', 'Escriba un nombre para el preajuste.'), "Preset '{n}' salvo.": ("Preset '{n}' saved.", "Preajuste '{n}' guardado."), 'Copiar relatório para suporte': ('Copy report (to send to Claude)', 'Copiar informe (para enviar a Claude)'), 'Exportar backup (pasta Downloads)': ('Export backup (Downloads folder)', 'Exportar copia (carpeta Descargas)'), 'Cole aqui o backup (Ctrl+V)': ('Paste the backup here (Ctrl+V)', 'Pegue aquí la copia (Ctrl+V)'), 'Importar texto colado': ('Import pasted text', 'Importar texto pegado'), 'Atualizar registro': ('Refresh log', 'Actualizar registro'), 'Aplicado.': ('Applied.', 'Aplicado.'), 'Abrir configurações': ('Open settings', 'Abrir configuración'), 'Sair do ícone': ('Quit icon', 'Salir del icono'), 'alterações pendentes': ('pending changes', 'cambios pendientes'), 'CPU, memória e GPU do app = só os processos do Quiklight. A cópia de tela feita pelo KDE não entra nesses números.': ("CPU, memory and GPU of the app = only Quiklight's processes. The screen copy made by KDE is not included.", 'CPU, memoria y GPU de la app = solo los procesos de Quiklight. La copia de pantalla hecha por KDE no está incluida.'), 'Cor:': ('Color:', 'Color:'), 'Efeito:': ('Effect:', 'Efecto:'), 'Paleta (até 10 cores). Rainbow e Fogo usam cores próprias.': ('Palette (up to 10 colors). Rainbow and Fire use their own colors.', 'Paleta (hasta 10 colores). Rainbow y Fuego usan colores propios.'), 'Toda cor da tela vira a cor selecionada mais próxima; o brilho segue a tela. Com uma só cor, tudo aparece nela.': ('Every screen color becomes the nearest selected color; brightness follows the screen. With one color, everything shows in it.', 'Cada color de la pantalla se convierte en el color seleccionado más cercano; el brillo sigue la pantalla. Con un solo color, todo aparece en él.'), 'Brilho acima de 100% realça sem mudar o tom. Limite de potência 100 = sem limite.': ('Brightness above 100% boosts without changing the hue. Power limit 100 = no limit.', 'Brillo por encima de 100% realza sin cambiar el tono. Límite de potencia 100 = sin límite.'), 'Tema de cores:': ('Color theme:', 'Tema de color:'), 'Balanço de branco: se o branco estiver azulado, reduza Azul e Verde.': ('White balance: if white looks bluish, reduce Blue and Green.', 'Balance de blancos: si el blanco se ve azulado, reduzca Azul y Verde.'), 'Vermelho': ('Red', 'Rojo'), 'Verde': ('Green', 'Verde'), 'Azul': ('Blue', 'Azul'), 'Gamma por canal (ajuste fino)': ('Per-channel gamma (fine tuning)', 'Gamma por canal (ajuste fino)'), 'Margem esquerda (%)': ('Left margin (%)', 'Margen izquierdo (%)'), 'Margem do topo (%)': ('Top margin (%)', 'Margen superior (%)'), 'Margem direita (%)': ('Right margin (%)', 'Margen derecho (%)'), 'Margem de baixo (%)': ('Bottom margin (%)', 'Margen inferior (%)'), 'Resolução:': ('Resolution:', 'Resolución:'), 'Layouts prontos:': ('Ready-made layouts:', 'Diseños listos:'), 'Cada trecho é uma parte da fita, na ordem em que os LEDs estão ligados. Inverter troca o sentido.': ('Each segment is a part of the strip, in the order the LEDs are wired. Reverse flips the direction.', 'Cada tramo es una parte de la cinta, en el orden en que están conectados los LEDs. Invertir cambia el sentido.'), 'Inverter': ('Reverse', 'Invertir'), 'Sem dados: o serviço está parado ou a fita não está recebendo quadros.': ('No data: the service is stopped or the strip is not receiving frames.', 'Sin datos: el servicio está detenido o la cinta no recibe cuadros.'), 'Nenhuma fita Quiklight USB encontrada.': ('No Quiklight USB strip found.', 'No se encontró ninguna cinta Quiklight USB.'), 'O preset guarda tudo: modo, cores, captura, área, resolução e LEDs/fitas. Depois de carregar, clique em Aplicar.': ('A preset stores everything: mode, colors, capture, area, resolution and LEDs/strips. After loading, click Apply.', 'El preajuste guarda todo: modo, colores, captura, área, resolución y LEDs/cintas. Tras cargarlo, haga clic en Aplicar.'), "Não consegui ler o preset '{n}'.": ("Could not read preset '{n}'.", "No pude leer el preajuste '{n}'."), 'Excluir preset': ('Delete preset', 'Eliminar preajuste'), "Preset '{n}' excluído.": ("Preset '{n}' deleted.", "Preajuste '{n}' eliminado."), 'Tema da janela:': ('Window theme:', 'Tema de la ventana:'), 'Importar: escolha um backup encontrado em Downloads ou cole o texto abaixo.': ('Import: choose a backup found in Downloads or paste the text below.', 'Importar: elija una copia encontrada en Descargas o pegue el texto abajo.'), 'Backup salvo em {p}': ('Backup saved to {p}', 'Copia guardada en {p}'), 'Importado: {n} item(ns).': ('Imported: {n} item(s).', 'Importado: {n} elemento(s).'), 'Voltar todos os valores ao padrão? (LEDs e fitas são mantidos)': ('Reset all values to default? (LEDs and strips are kept)', '¿Volver todos los valores a los predeterminados? (los LEDs y cintas se mantienen)'), 'Backup não reconhecido.': ('Backup not recognized.', 'Copia no reconocida.'), 'Serviço ligado.': ('Service started.', 'Servicio iniciado.'), 'Serviço desligado (fita apagada).': ('Service stopped (strip off).', 'Servicio detenido (cinta apagada).'), 'Serviço reiniciado.': ('Service restarted.', 'Servicio reiniciado.'), 'Preset ativo': ('Active preset', 'Preajuste activo'), 'Modo': ('Mode', 'Modo'), 'Serviço': ('Service', 'Servicio'), 'Fitas': ('Strips', 'Cintas'), 'detectada(s)': ('detected', 'detectada(s)'), 'de 1 núcleo': ('of 1 core', 'de 1 núcleo'), 'Memória': ('Memory', 'Memoria'), 'GPU do app': ('App GPU', 'GPU de la app'), 'GPU total (sistema)': ('Total GPU (system)', 'GPU total (sistema)'), 'modificado': ('modified', 'modificado'), 'Duas cores: metade esquerda da tela no lado esquerdo da fita e metade direita no lado direito.': ('Two colors: left half of the screen on the left side of the strip and right half on the right side.', 'Dos colores: mitad izquierda de la pantalla en el lado izquierdo de la cinta y mitad derecha en el derecho.'), 'Quatro cores: esquerda, direita, topo e baixo da tela, cada uma no seu lado da fita.': ('Four colors: left, right, top and bottom of the screen, each on its side of the strip.', 'Cuatro colores: izquierda, derecha, arriba y abajo de la pantalla, cada uno en su lado de la cinta.'), "Tema '{n}' carregado.": ("Theme '{n}' loaded.", "Tema '{n}' cargado."), 'Trecho': ('Segment', 'Tramo'), 'Fita': ('Strip', 'Cinta'), 'LEDs acesos': ('LEDs on', 'LEDs encendidos'), 'Consumo estimado': ('Estimated consumption', 'Consumo estimado'), 'LEDs': ('LEDs', 'LEDs'), 'configurados': ('configured', 'configurados'), 'Total configurado': ('Total configured', 'Total configurado'), 'Consumo máximo teórico': ('Theoretical maximum consumption', 'Consumo máximo teórico'), 'todos em branco total': ('all at full white', 'todos en blanco total'), 'Importar': ('Import', 'Importar'), 'Rodando': ('Running', 'En marcha'), 'Parado': ('Stopped', 'Detenido'), '+ cor (aleatória)': ('+ color (random)', '+ color (aleatorio)'), 'Erro': ('Error', 'Error'), 'A fita acompanha as bordas da tela. Ajustes em Cores e Captura.': ('The strip follows the screen edges. Settings in Colors and Capture.', 'La cinta sigue los bordes de la pantalla. Ajustes en Colores y Captura.'), 'Atenção: a configuração usa {a} fita(s), mas só {b} foi/foram detectada(s).': ('Warning: the configuration uses {a} strip(s), but only {b} was/were detected.', 'Atención: la configuración usa {a} cinta(s), pero solo se detectó/detectaron {b}.'), 'Fabricante': ('Manufacturer', 'Fabricante'), 'Produto': ('Product', 'Producto'), 'Número de série': ('Serial number', 'Número de serie'), 'Versão do USB': ('USB version', 'Versión de USB'), 'Corrente máxima declarada': ('Declared maximum current', 'Corriente máxima declarada'), 'Gerenciamento de energia': ('Power management', 'Gestión de energía'), 'Estado': ('State', 'Estado'), 'Nós HID': ('HID nodes', 'Nodos HID')}
ICONS = {'Ligar': '▶', 'Desligar': '⏹', 'Reiniciar': '🔄', 'Resetar valores': '♻', 'Tempo real': '⚡', 'Aplicar': '✔', 'Escolher outra tela': '🖥', 'Esquerda + topo + direita': '📐', 'Moldura completa (com embaixo)': '🖼', 'Adicionar trecho': '➕', 'Adicionar trecho em outra fita (Fita 2)': '➕', 'Excluir': '🗑', 'Salvar preset': '💾', 'Copiar relatório para suporte': '📋', 'Exportar backup (pasta Downloads)': '📤', 'Importar texto colado': '📥', 'Importar': '📥', 'Atualizar registro': '🔄', 'Atualizar': '🔄', 'Borda': '▫', 'Um pouco para dentro': '◽', 'Centro': '◾', 'Home': '🏠', 'Custo do aplicativo': '📈', 'Modo de iluminação': '💡', 'Brilho e proteção': '🛡', 'Cores (modos dinâmicos)': '🎨', 'Acurácia (ative a caixa acima)': '🎯', 'Área de captura da tela': '🖥', 'LEDs e fitas': '✨', 'Ao vivo': '📡', 'Presets': '💾', 'Hardware da fita': '🔌', 'Sistema': '⚙', 'Relatório e backup': '📋', 'Registro do programa': '📜', 'Dinâmico (captura de tela)': '🖥', 'Estático': '🎨', 'Efeitos': '✨'}
ICONS.update({
    "Brilho (%)": "🔆", "Brilho mínimo %": "🔅", "Contraste": "◐", "Espessura da faixa": "📏", "Fidelidade da cor": "🎯",
    "Gamma": "📈", "Limite de potência (%)": "🔋", "Limite de variação (0 = desligado)": "🎚",
    "Mínimo (%) - menor = efeito mais forte": "💪", "Preferência por cores vibrantes": "🌈", "Profundidade das áreas (%)": "📐",
    "Quadros por segundo": "🎞", "Respeitar o brilho da cena": "🎬", "Saturação": "🎨", "Sensibilidade à batida": "📡",
    "Suavidade da troca": "🌊", "Suavização entre cores (0 = instantâneo)": "🌫", "Velocidade": "⏩",
    "Velocidade de detecção das barras pretas (1 = lenta, 10 = rápida)": "⏱", "Vermelho": "🔴", "Verde": "🟢", "Azul": "🔵",
    "Completar slots vazios com cores aleatórias": "🎲", "Detectar barras pretas automaticamente (recorta a área para onde há imagem)": "⬛",
    "Limitar a captura ao fps": "⏲", "Melhor acurácia de cores (balanço de branco, gamma por canal e proteção de neutros)": "🎯",
    "Modo música (pulsa na batida do som do PC)": "🎵", "Modo vívido": "🌈", "Inverter": "↔",
    "Estilo:": "🎭", "Reagir a:": "👂", "Efeito:": "✨", "Cor:": "🎨", "Tema de cores:": "🎨", "Tema da janela:": "🖌",
    "Presets do modo música": "💾", "Estilo e ajustes": "🎛", "Fitas que reagem ao som": "📍", "Detecção de barras pretas": "⬛",
    "Acurácia de cores": "🎯", "Salvar preset de música": "💾", "Excluir preset de música": "🗑",
})
ICONS.update({"Modo música": "🎵", "Monitor capturado": "🖥", "Escolher monitor no KDE": "🖥", "Sobre": "ℹ"})
TR.update({
    "Velocidade de detecção das barras pretas (1 = lenta, 10 = rápida)": ("Black-bar detection speed (1 = slow, 10 = fast)", "Velocidad de detección de barras negras (1 = lenta, 10 = rápida)"),
    "Monitor capturado": ("Captured monitor", "Monitor capturado"),
    "Escolher monitor no KDE": ("Choose monitor in KDE", "Elegir monitor en KDE"),
    "No Linux (KDE) o monitor final é escolhido na janela de compartilhamento do KDE (botão ao lado).": ("On Linux (KDE) the final monitor is chosen in KDE's sharing window (button beside).", "En Linux (KDE) el monitor final se elige en la ventana de compartir de KDE (botón al lado)."),
    "Sobre": ("About", "Acerca de"), "Versão": ("Version", "Versión"),
    "Detalhes USB: disponíveis apenas no Linux.": ("USB details: available on Linux only.", "Detalles USB: disponibles solo en Linux."),
    "Iluminação e cores": ("Lighting and colors", "Iluminación y colores"),
    "Ativar fidelidade adaptativa (experimental)": ("Enable adaptive fidelity (experimental)", "Activar fidelidad adaptativa (experimental)"),
    "Intensidade da fidelidade adaptativa (%)": ("Adaptive fidelity strength (%)", "Intensidad de fidelidad adaptativa (%)"),
    "Desativado = processamento original. Ative e ajuste a intensidade (0-100%). A calibração RGB é preservada.": ("Off = original processing. Enable and adjust strength (0-100%). RGB calibration is preserved.", "Desactivado = procesamiento original. Activa y ajusta la intensidad (0-100%). Se conserva la calibración RGB."),
    "Detectar barras pretas automaticamente (recorta a área para onde há imagem)": ("Detect black bars automatically (crops the area to where the picture is)", "Detectar barras negras automáticamente (recorta el área a donde hay imagen)"),
})

MUSIC_BANDS = [("bass", "Graves (bumbo e baixo)"), ("treble", "Agudos (voz e pratos)"), ("both", "Graves + agudos")]
MUSIC_STYLES = [("dim", "Escurece na batida"), ("boost", "Acende na batida"), ("flash", "Flash branco na batida"), ("sat", "Cores mais vivas na batida"), ("comp", "Cor oposta na batida"), ("pal", "Troca de cor a cada batida"), ("split", "Graves nas laterais, agudos no topo"), ("vol", "Brilho segue o volume"), ("wave", "Onda de luz na batida"), ("vu", "Medidor de volume (do centro)"), ("spark", "Faíscas na batida"), ("rev", "REV sound - motor de carro (RPM)"),
                ("hue", "Giro de matiz na batida"), ("breath", "Respiração pelo volume"), ("chase", "Corrida de luz"),
                ("center", "Explosão do centro"), ("confetti", "Confete de cores"), ("heat", "Termômetro de cores"),
                ("quad", "Quatro bordas"), ("heartbeat", "Batimento cardíaco"), ("echo", "Eco longo"), ("pingpong", "Ping-pong")]
TR.update({
    "Flash branco na batida": ("White flash on the beat", "Destello blanco con el ritmo"),
    "Cores mais vivas na batida": ("More vivid colors on the beat", "Colores más vivos con el ritmo"),
    "Cor oposta na batida": ("Opposite color on the beat", "Color opuesto con el ritmo"),
    "Troca de cor a cada batida": ("Color change on every beat", "Cambio de color en cada golpe"),
    "Graves nas laterais, agudos no topo": ("Bass on the sides, treble on top", "Graves a los lados, agudos arriba"),
    "Brilho segue o volume": ("Brightness follows the volume", "El brillo sigue el volumen"),
    "Onda de luz na batida": ("Light wave on the beat", "Onda de luz con el ritmo"),
    "Medidor de volume (do centro)": ("Volume meter (from center)", "Medidor de volumen (desde el centro)"),
    "Faíscas na batida": ("Sparkles on the beat", "Chispas con el ritmo"),
    "Mínimo (%) - menor = efeito mais forte": ("Minimum (%) - lower = stronger effect", "Mínimo (%) - menor = efecto más fuerte"),
    "Sensibilidade à batida": ("Beat sensitivity", "Sensibilidad al ritmo"),
    "Escolha o estilo. Quanto menor o mínimo, mais forte o efeito. Aumente a sensibilidade se a luz quase não reage.": ("Choose the style. The lower the minimum, the stronger the effect. Raise the sensitivity if the light barely reacts.", "Elija el estilo. Cuanto menor el mínimo, más fuerte el efecto. Suba la sensibilidad si la luz casi no reacciona."),
    "Reagir a:": ("React to:", "Reaccionar a:"),
    "Graves (bumbo e baixo)": ("Bass (kick and bass line)", "Graves (bombo y bajo)"),
    "Agudos (voz e pratos)": ("Treble (vocals and cymbals)", "Agudos (voz y platillos)"),
    "Graves + agudos": ("Bass + treble", "Graves + agudos"),
    "Graves": ("Bass", "Graves"), "Agudos": ("Treble", "Agudos"), "Volume": ("Volume", "Volumen"), "Reação da luz": ("Light reaction", "Reacción de la luz"),
    "Marque Modo música e clique em Aplicar (ou ligue Tempo real) para ver o medidor.": ("Check Music mode and click Apply (or turn on Real time) to see the meter.", "Marque Modo música y haga clic en Aplicar (o active Tiempo real) para ver el medidor."),
    "Sem dados de áudio: o serviço está parado ou ainda não captou som. Toque uma música.": ("No audio data: the service is stopped or has not picked up sound yet. Play some music.", "Sin datos de audio: el servicio está detenido o aún no captó sonido. Reproduzca música."),
    "Barras azuis: o que o som tem agora. Em cada barra, arraste as alças amarelas: abaixo da mínima é ignorado, acima da máxima conta como 100% (duplo clique restaura). A barra de reação mostra o que move a luz; passou da linha = batida.": ("Blue bars: what the sound has right now. On each bar, drag the yellow handles: below the minimum is ignored, above the maximum counts as 100% (double-click resets). The reaction bar shows what drives the light; past the line = beat.", "Barras azules: lo que tiene el sonido ahora. En cada barra, arrastre los tiradores amarillos: por debajo del mínimo se ignora, por encima del máximo cuenta como 100% (doble clic restaura). La barra de reacción muestra lo que mueve la luz; pasó la línea = golpe."),
    "Estilo:": ("Style:", "Estilo:"),
    "Música": ("Music", "Música"),
    "REV sound - motor de carro (RPM)": ("REV sound - car engine (RPM)", "REV sound - motor de coche (RPM)"),
    "REV sound (jogos de corrida): acompanha o giro do motor pelo som. O brilho sobe com o RPM, avermelha perto do limite e dá um clarão na troca de marcha. Experimental: funciona melhor com a música do jogo baixa. A barra Reação da luz mostra o RPM.": ("REV sound (racing games): follows the engine revs from the sound. Brightness rises with RPM, turns red near the limit and flashes on gear shifts. Experimental: works best with the game music low. The Light reaction bar shows the RPM.", "REV sound (juegos de carreras): sigue las revoluciones del motor por el sonido. El brillo sube con las RPM, se pone rojo cerca del límite y destella al cambiar de marcha. Experimental: funciona mejor con la música del juego baja. La barra Reacción de la luz muestra las RPM."),
    "Entrada mín": ("Min input", "Entrada mín"), "Saída máx": ("Max output", "Salida máx"),
    "CPU (app + serviço)": ("CPU (app + service)", "CPU (app + servicio)"), "Processos medidos": ("Processes measured", "Procesos medidos"),
    "Só o Quiklight (janela, serviço e processos filhos). A cópia de tela feita pelo KDE não entra. \"—\" = o driver da placa não informa.": ("Quiklight only (window, service and child processes). The screen copy made by KDE is not included. \"—\" = the graphics driver does not report it.", "Solo Quiklight (ventana, servicio y procesos hijos). La copia de pantalla hecha por KDE no entra. \"—\" = el controlador de la tarjeta no lo informa."),
    "Presets do modo música": ("Music mode presets", "Presets del modo música"), "Estilo e ajustes": ("Style and settings", "Estilo y ajustes"),
    "Fitas que reagem ao som": ("Strips that react to sound", "Cintas que reaccionan al sonido"), "Detecção de barras pretas": ("Black bar detection", "Detección de barras negras"),
    "Acurácia de cores": ("Color accuracy", "Precisión de color"), "Salvar preset de música": ("Save music preset", "Guardar preset de música"),
    "Excluir preset de música": ("Delete music preset", "Eliminar preset de música"), "escolher um preset...": ("choose a preset...", "elegir un preset..."),
    "Nome do preset:": ("Preset name:", "Nombre del preset:"), "Escolha o preset:": ("Choose the preset:", "Elija el preset:"),
    "Preset de música '{n}' salvo.": ("Music preset '{n}' saved.", "Preset de música '{n}' guardado."),
    "Preset de música '{n}' carregado.": ("Music preset '{n}' loaded.", "Preset de música '{n}' cargado."),
    "Preset de música '{n}' excluído.": ("Music preset '{n}' deleted.", "Preset de música '{n}' eliminado."),
    "Não há presets de música salvos para excluir.": ("There are no saved music presets to delete.", "No hay presets de música guardados para eliminar."),
    "Marque os trechos que reagem ao som. Os desmarcados ficam com a iluminação normal.": ("Check the sections that react to sound. Unchecked ones keep the normal lighting.", "Marque los tramos que reaccionan al sonido. Los desmarcados mantienen la iluminación normal."),
    "Todos": ("All", "Todos"), "Nenhum": ("None", "Ninguno"), "Motor (RPM)": ("Engine (RPM)", "Motor (RPM)"),
    "desligado": ("off", "apagado"), "ligado": ("on", "encendido"), "inativo (só age no modo Dinâmico)": ("inactive (only works in Dynamic mode)", "inactivo (solo actúa en el modo Dinámico)"),
    "Festa (batida forte)": ("Party (strong beat)", "Fiesta (ritmo fuerte)"), "Lounge (suave)": ("Lounge (soft)", "Lounge (suave)"),
    "Eletrônica (graves)": ("Electronic (bass)", "Electrónica (graves)"), "Rock / Pop": ("Rock / Pop", "Rock / Pop"),
    "Corrida (REV sound)": ("Racing (REV sound)", "Carreras (REV sound)"), "Trilha de cinema": ("Movie score", "Banda sonora"),
    "Giro de matiz na batida": ("Hue spin on the beat", "Giro de matiz con el ritmo"), "Respiração pelo volume": ("Breathing by volume", "Respiración por volumen"),
    "Corrida de luz": ("Light chase", "Luz en carrera"), "Explosão do centro": ("Burst from the center", "Explosión desde el centro"),
    "Confete de cores": ("Color confetti", "Confeti de colores"), "Termômetro de cores": ("Color thermometer", "Termómetro de colores"),
    "Quatro bordas": ("Four edges", "Cuatro bordes"), "Batimento cardíaco": ("Heartbeat", "Latido"), "Eco longo": ("Long echo", "Eco largo"), "Ping-pong": ("Ping-pong", "Ping-pong"),
    "Personalizado": ("Custom", "Personalizado"),
    "Passe o mouse sobre cada barra para ver o que ela faz. Use o interruptor à esquerda para ligar ou desligar uma faixa.": ("Hover each bar to see what it does. Use the switch on the left to turn a band on or off.", "Pase el ratón sobre cada barra para ver qué hace. Use el interruptor de la izquierda para activar o desactivar una banda."),
    "Versões e rollback": ("Versions and rollback", "Versiones y rollback"), "Versão atual": ("Current version", "Versión actual"),
    "Versões anteriores guardadas (até 10):": ("Saved previous versions (up to 10):", "Versiones anteriores guardadas (hasta 10):"),
    "Ainda não há versões anteriores guardadas. Elas aparecem aqui depois da próxima atualização.": ("There are no saved previous versions yet. They appear here after the next update.", "Aún no hay versiones anteriores guardadas. Aparecen aquí después de la próxima actualización."),
    "Restaurar esta versão": ("Restore this version", "Restaurar esta versión"), "Restaurar versão": ("Restore version", "Restaurar versión"),
    "Voltar para a versão": ("Go back to version", "Volver a la versión"),
    "O programa vai reiniciar. Suas configurações e presets são mantidos.": ("The program will restart. Your settings and presets are kept.", "El programa se reiniciará. Sus ajustes y presets se mantienen."),
    "Os arquivos dessa versão não foram encontrados.": ("The files for this version were not found.", "No se encontraron los archivos de esta versión."),
    "Novidades": ("What's new", "Novedades"),
    "Detecção de barras pretas reescrita: varre as bordas, ignora letras e objetos no centro da tela e volta ao normal quando a imagem reaparece.": ("Black bar detection rewritten: scans the edges, ignores letters and objects in the middle of the screen and returns to normal when the picture reappears.", "Detección de barras negras reescrita: recorre los bordes, ignora letras y objetos en el centro de la pantalla y vuelve a la normalidad cuando reaparece la imagen."),
    "Modo música": ("Music mode", "Modo música"),
    "Atenção: o Modo música só age no modo Dinâmico (aba Iluminação e cores).": ("Note: Music mode only works in Dynamic mode (Lighting and colors tab).", "Atención: el Modo música solo actúa en el modo Dinámico (pestaña Iluminación y colores)."),
    "Escurece na batida": ("Dims on the beat", "Se atenúa con el ritmo"),
    "Acende na batida": ("Brightens on the beat", "Se enciende con el ritmo"),
    "Modo música (pulsa na batida do som do PC)": ("Music mode (pulses to the beat of the PC audio)", "Modo música (pulsa con el ritmo del sonido del PC)"),
    "Dimming mínimo na batida (%)": ("Minimum dimming on the beat (%)", "Atenuación mínima en el golpe (%)"),
    "Escolha o estilo. Quanto menor o mínimo, mais forte o efeito. Aumente a sensibilidade se a luz quase não reage.": ("On the beat the lighting dims down to the minimum and returns to normal. The lower the value, the stronger the pulse.", "En el golpe la iluminación se atenúa hasta el mínimo y vuelve a la normalidad. Cuanto menor el valor, más fuerte el pulso."),
})

TR.update({
    "Iniciar automaticamente com o sistema (minimizado na bandeja)": (
        "Start automatically with the system (minimized to tray)",
        "Iniciar automáticamente con el sistema (minimizado en la bandeja)"),
    "Inicia depois de entrar na conta Windows.": (
        "Starts after signing in to Windows.",
        "Se inicia después de iniciar sesión en Windows."),
    "Inicia a interface na bandeja e o serviço de LEDs ao entrar no KDE.": (
        "Starts the tray interface and LED service when signing in to KDE.",
        "Inicia la interfaz en la bandeja y el servicio LED al entrar en KDE."),
    "Inicialização automática ativada para o próximo login.": (
        "Automatic startup enabled for the next sign-in.",
        "Inicio automático activado para el próximo inicio de sesión."),
    "Inicialização automática desativada.": (
        "Automatic startup disabled.",
        "Inicio automático desactivado."),
})

def tr(s):
    if LANG == "pt": return s
    t = TR.get(s)
    if not t: return s
    return t[0] if LANG == "en" else t[1]

def tr_i(s):
    e = ICONS.get(s)
    return f"{e} {tr(s)}" if e else tr(s)

def lang_path(): return data_dir() / "gui_lang"
def read_lang():
    try:
        v = lang_path().read_text().strip()
        return v if v in ("pt", "en", "es") else "pt"
    except Exception: return "pt"
def save_lang(v):
    data_dir().mkdir(parents=True, exist_ok=True); lang_path().write_text(v)

class NoWheelSlider(QSlider):
    def wheelEvent(self, e): e.ignore()
class NoWheelCombo(QComboBox):
    def __init__(self, *a):
        super().__init__(*a); self.setMaximumWidth(260)
    def wheelEvent(self, e): e.ignore()
class NoWheelSpin(QSpinBox):
    def wheelEvent(self, e): e.ignore()

class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=6):
        super().__init__(parent); self._items = []; self.setSpacing(spacing)
    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, i): return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i): return self._items.pop(i) if 0 <= i < len(self._items) else None
    def hasHeightForWidth(self): return True
    def heightForWidth(self, w): return self._do(QRect(0, 0, w, 0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self._do(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        s = QSize()
        for it in self._items: s = s.expandedTo(it.minimumSize())
        return s
    def _do(self, rect, test):
        x, y, lh, sp = rect.x(), rect.y(), 0, self.spacing()
        for it in self._items:
            sh = it.sizeHint()
            if x + sh.width() > rect.right() and lh > 0: x = rect.x(); y += lh + sp; lh = 0
            if not test: it.setGeometry(QRect(QPoint(x, y), sh))
            x += sh.width() + sp; lh = max(lh, sh.height())
        return y + lh - rect.y()

# ───────────────────────── Dados ─────────────────────────
def data_dir():
    if IS_WIN: base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else: base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "quiklight-rust"

def config_path(): return data_dir() / "config.toml"
def presets_dir(): return data_dir() / "presets"
def preset_path(n): return presets_dir() / f"{n}.toml"

DEFAULTS = dict(
    top=29, right=17, left=17, bottom=0, cap_w=80, cap_h=45, border=3,
    inset_left=0.0, inset_top=0.0, inset_right=0.0, inset_bottom=0.0,
    fps=60, brightness=200, smoothing=0.15, saturation=1.4, gamma=1.2, contrast=1.0,
    gain_r=1.0, gain_g=1.0, gain_b=1.0, color_mode="average", capture_limit=True,
    mode="screen", static_r=255, static_g=120, static_b=40, effect="breathing",
    effect_speed=3.0, effect_min=20.0, dom_scene=0.6, dom_smooth=0.95, slew=5.0,
    music=False, music_min=25.0, music_style="dim", music_sens=1.0, music_band="bass", music_in_bass=0.0, music_out_bass=1.0, music_in_treble=0.0, music_out_treble=1.0,
    music_in_vol=0.0, music_out_vol=1.0, music_in_rpm=0.0, music_out_rpm=1.0,
    music_on_bass=True, music_on_treble=True, music_on_vol=True, music_on_rpm=True,
    palette_random=True, dom_vibrance=0.25, dom_fidelity=0.4, zone_depth=33.0,
    gamma_r=1.0, gamma_g=1.0, gamma_b=1.0, level=100.0, power_limit=100.0,
    accuracy=False, adaptive_fidelity_enabled=False, adaptive_fidelity=60.0, fade_time=0.10, auto_crop=False, crop_speed=2.0,
)
FLOATS = [k for k, v in DEFAULTS.items() if isinstance(v, float)]
INTS = [k for k, v in DEFAULTS.items() if isinstance(v, int) and not isinstance(v, bool)]

def normalize(c):
    for k in FLOATS: c[k] = float(c.get(k, DEFAULTS[k]))
    for k in INTS: c[k] = int(c.get(k, DEFAULTS[k]))
    for k in ("color_mode", "mode", "effect", "music_style", "music_band"):
        if not c.get(k): c[k] = DEFAULTS[k]
    pal = [str(x) for x in (c.get("palette") or [])][:10]
    c["palette"] = pal + [""] * (10 - len(pal))
    segs = []
    for s in c.get("segment") or []:
        segs.append(dict(device=int(s.get("device", 0)), edge=str(s.get("edge", "top")),
                         leds=int(s.get("leds", 0)), reverse=bool(s.get("reverse", False)), music=bool(s.get("music", True))))
    if not segs:
        for e in ("left", "top", "right", "bottom"):
            n = int(c.get(e, 0))
            if n > 0: segs.append(dict(device=0, edge=e, leds=n, reverse=False, music=True))
    c["segment"] = segs
    c.setdefault("monitor", None)
    return c

def cfg_from_dict(d):
    c = copy.deepcopy(DEFAULTS)
    c["palette"] = [""] * 10
    c["segment"] = []
    c["monitor"] = None
    c.update(d)
    return normalize(c)

def read_config():
    try: d = tomllib.loads(config_path().read_text())
    except Exception: d = {}
    return cfg_from_dict(d)

def b(x): return "true" if x else "false"

def cfg_text(c, preset=False):
    s = lambda e: sum(g["leds"] for g in c["segment"] if g["edge"] == e)
    mon = f'monitor = "{c["monitor"]}"' if c.get("monitor") else '# monitor = "DP-4"'
    t = "# Quiklight — configuração (escrita pelo quiklight-gui)\n"
    if preset: t += "preset_version = 2\n"
    t += (f"\ntop = {s('top')}\nright = {s('right')}\nleft = {s('left')}\nbottom = {s('bottom')}\n\n"
          f"cap_w = {c['cap_w']}\ncap_h = {c['cap_h']}\nborder = {c['border']}\n\n"
          f"inset_left = {c['inset_left']:.1f}\ninset_top = {c['inset_top']:.1f}\n"
          f"inset_right = {c['inset_right']:.1f}\ninset_bottom = {c['inset_bottom']:.1f}\n\n"
          f"{mon}\n\nfps = {c['fps']}\n\n"
          f"brightness = {c['brightness']}\nsmoothing = {c['smoothing']:.2f}\n"
          f"saturation = {c['saturation']:.2f}\ngamma = {c['gamma']:.2f}\ncontrast = {c['contrast']:.2f}\n"
          f"gain_r = {c['gain_r']:.2f}\ngain_g = {c['gain_g']:.2f}\ngain_b = {c['gain_b']:.2f}\n"
          f"color_mode = \"{c['color_mode']}\"\ncapture_limit = {b(c['capture_limit'])}\n"
          f"mode = \"{c['mode']}\"\nstatic_r = {c['static_r']}\nstatic_g = {c['static_g']}\nstatic_b = {c['static_b']}\n"
          f"effect = \"{c['effect']}\"\neffect_speed = {c['effect_speed']:.1f}\neffect_min = {c['effect_min']:.1f}\n"
          f"dom_scene = {c['dom_scene']:.2f}\ndom_smooth = {c['dom_smooth']:.3f}\nslew = {c['slew']:.1f}\n"
          f"palette = [{', '.join(chr(34) + x + chr(34) for x in c['palette'])}]\n"
          f"palette_random = {b(c['palette_random'])}\ndom_vibrance = {c['dom_vibrance']:.2f}\n"
          f"dom_fidelity = {c['dom_fidelity']:.2f}\nzone_depth = {c['zone_depth']:.1f}\n"
          f"gamma_r = {c['gamma_r']:.2f}\ngamma_g = {c['gamma_g']:.2f}\ngamma_b = {c['gamma_b']:.2f}\n"
          f"level = {c['level']:.1f}\npower_limit = {c['power_limit']:.1f}\naccuracy = {b(c['accuracy'])}\nadaptive_fidelity_enabled = {b(c['adaptive_fidelity_enabled'])}\nadaptive_fidelity = {c['adaptive_fidelity']:.0f}\n"
          f"fade_time = {c['fade_time']:.2f}\nauto_crop = {b(c['auto_crop'])}\ncrop_speed = {c['crop_speed']:.1f}\n"
          f"music = {b(c['music'])}\nmusic_min = {c['music_min']:.1f}\nmusic_style = \"{c['music_style']}\"\nmusic_sens = {c['music_sens']:.2f}\nmusic_band = \"{c['music_band']}\"\nmusic_in_bass = {c['music_in_bass']:.2f}\nmusic_out_bass = {c['music_out_bass']:.2f}\nmusic_in_treble = {c['music_in_treble']:.2f}\nmusic_out_treble = {c['music_out_treble']:.2f}\nmusic_in_vol = {c['music_in_vol']:.2f}\nmusic_out_vol = {c['music_out_vol']:.2f}\nmusic_in_rpm = {c['music_in_rpm']:.2f}\nmusic_out_rpm = {c['music_out_rpm']:.2f}\nmusic_on_bass = {b(c['music_on_bass'])}\nmusic_on_treble = {b(c['music_on_treble'])}\nmusic_on_vol = {b(c['music_on_vol'])}\nmusic_on_rpm = {b(c['music_on_rpm'])}\n")
    for g in c["segment"]:
        t += (f"\n[[segment]]\ndevice = {g['device']}\nedge = \"{g['edge']}\"\n"
              f"leds = {g['leds']}\nreverse = {b(g['reverse'])}\nmusic = {b(g.get('music', True))}\n")
    return t

def write_config(c):
    """Publica a configuração completa sem expor um TOML parcial ao backend."""
    data_dir().mkdir(parents=True, exist_ok=True)
    target = config_path()
    temp = target.with_name(target.name + f".{os.getpid()}.tmp")
    try:
        temp.write_text(cfg_text(c), encoding="utf-8")
        os.replace(temp, target)
    finally:
        try: temp.unlink(missing_ok=True)
        except OSError: pass

# ───────────────────────── Presets ─────────────────────────
THEMES = [
    ("Natural", 1.2, 1.0, 1.1, (1.0, 1.0, 1.0), False),
    ("Vívido", 1.9, 1.1, 1.3, (1.0, 1.0, 1.0), True),
    ("Neon", 2.6, 1.2, 1.5, (1.0, 1.0, 1.0), True),
    ("Cinema (quente suave)", 1.5, 1.05, 1.2, (1.0, 0.95, 0.85), True),
    ("Quente", 1.6, 1.05, 1.2, (1.0, 0.88, 0.65), False),
    ("Frio", 1.6, 1.05, 1.2, (0.8, 0.95, 1.0), False),
]

def apply_color_theme(c, t):
    _, sat, con, gam, gain, vivid = t
    c.update(saturation=sat, contrast=con, gamma=gam, gain_r=gain[0], gain_g=gain[1], gain_b=gain[2],
             color_mode="vivid" if vivid else "average")

def clean_name(s):
    return "".join(ch for ch in s.strip() if ch not in "/\\\0.").strip()

TITLE_ICONS = {
    "Home": ("go-home",), "Custo do aplicativo": ("utilities-system-monitor", "office-chart-line"),
    "Sobre": ("help-about", "dialog-information"), "Modo de iluminação": ("help-hint", "lightbulb", "dialog-information"),
    "Brilho e proteção": ("security-high", "security-medium"), "Detecção de barras pretas": ("transform-crop", "view-fullscreen"),
    "Cores (modos dinâmicos)": ("preferences-desktop-color", "color-management", "applications-graphics"),
    "Acurácia de cores": ("color-picker", "color-management"), "Área de captura da tela": ("transform-crop", "view-fullscreen", "video-display"),
    "LEDs e fitas": ("preferences-desktop-display-color", "applications-graphics", "format-justify-fill"),
    "Monitor capturado": ("video-display", "computer"), "Hardware da fita": ("drive-removable-media-usb", "preferences-system"),
    "Presets": ("document-save", "bookmarks"), "Sistema": ("configure", "preferences-system"),
    "Relatório e backup": ("document-export", "edit-copy"), "Registro do programa": ("text-x-log", "view-list-text", "text-x-generic"),
    "Modo música": ("audio-x-generic", "multimedia-player", "folder-music"), "Presets do modo música": ("document-save", "bookmarks"),
    "Estilo e ajustes": ("configure", "preferences-other"), "Versões e rollback": ("document-revert", "edit-undo", "view-history"), "Fitas que reagem ao som": ("edit-select-all", "view-list-icons"),
}
TITLE_GLYPHS = {
    "Home": "⌂", "Custo do aplicativo": "◷", "Sobre": "ⓘ", "Modo de iluminação": "☀", "Brilho e proteção": "⛨",
    "Detecção de barras pretas": "▭", "Cores (modos dinâmicos)": "◐", "Acurácia de cores": "◎", "Área de captura da tela": "⛶",
    "LEDs e fitas": "✦", "Monitor capturado": "▣", "Hardware da fita": "⚙", "Presets": "★", "Sistema": "☰",
    "Relatório e backup": "⇩", "Registro do programa": "☷", "Modo música": "♪", "Presets do modo música": "★",
    "Estilo e ajustes": "✎", "Fitas que reagem ao som": "◉", "Versões e rollback": "↺",
}
def title_icon_win(text, color):
    """Windows não tem tema de ícones: desenha um símbolo (Segoe UI Symbol) na cor de destaque."""
    pm = QPixmap(40, 40); pm.setDevicePixelRatio(2.0); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    f = QFont("Segoe UI Symbol"); f.setPixelSize(16); p.setFont(f); p.setPen(color)
    p.drawText(QRectF(0, 0, 20, 20), int(Qt.AlignmentFlag.AlignCenter), TITLE_GLYPHS.get(text, "■")); p.end()
    return pm
def title_icon(text, color):
    """Ícone de título: ícone do tema pintado na cor de destaque (nunca fica em branco)."""
    if IS_WIN: return title_icon_win(text, color)
    for name in TITLE_ICONS.get(text, ()):
        ic = QIcon.fromTheme(name)
        if ic.isNull(): continue
        pm = ic.pixmap(20, 20)
        if pm.isNull(): continue
        out = QPixmap(pm.size()); out.setDevicePixelRatio(pm.devicePixelRatio()); out.fill(Qt.GlobalColor.transparent)
        p = QPainter(out); p.drawPixmap(0, 0, pm); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); p.fillRect(out.rect(), color); p.end()
        return out
    pm = QPixmap(20, 20); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen); p.setBrush(color)
    p.drawRoundedRect(QRectF(4, 4, 12, 12), 3, 3); p.end(); return pm

BIN_NAME = "quiklight.exe" if IS_WIN else "quiklight"
def versions_dir():
    if IS_WIN: return win_dir() / "versions"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "quiklight-versions"
def bin_path():
    return win_dir() / "quiklight.exe" if IS_WIN else Path.home() / ".local" / "bin" / "quiklight"
def list_versions():
    """Versões anteriores guardadas (mais recente primeiro): (pasta, versão, data)."""
    out = []
    try:
        for d in versions_dir().iterdir():
            try:
                if (d / BIN_NAME).is_file() and (d / "quiklight_gui.py").is_file():
                    v = (d / "VERSION").read_text().strip() if (d / "VERSION").exists() else d.name.lstrip("v")
                    out.append((d.name, v, d.stat().st_mtime))
            except Exception: continue
    except Exception: pass
    return sorted(out, key=lambda x: -x[2])
def prune_versions(keep=10):
    for name, _, _ in list_versions()[keep:]:
        shutil.rmtree(versions_dir() / name, ignore_errors=True)
def snapshot_current(prune=True):
    """Guarda o programa e a janela instalados agora (para poder voltar a eles)."""
    d = versions_dir() / f"v{APP_VERSION}"; d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bin_path(), d / BIN_NAME); shutil.copy2(Path(__file__).resolve(), d / "quiklight_gui.py")
    (d / "VERSION").write_text(str(APP_VERSION)); os.utime(d, None)
    if prune: prune_versions()
def restore_version(name):
    """Volta para uma versão guardada. Devolve None se deu certo, ou o texto do erro."""
    src = versions_dir() / name; gui = Path(__file__).resolve(); binp = bin_path()
    if not ((src / BIN_NAME).is_file() and (src / "quiklight_gui.py").is_file()):
        return tr("Os arquivos dessa versão não foram encontrados.")
    try:
        snapshot_current(prune=False)           # guarda a atual: dá para voltar para ela depois
        was = is_active(); service_cmd("stop"); time.sleep(0.6)
        tmp = binp.with_name(binp.name + ".new"); shutil.copy2(src / BIN_NAME, tmp)
        if not IS_WIN: os.chmod(tmp, 0o755)
        os.replace(tmp, binp)
        shutil.copy2(src / "quiklight_gui.py", gui)
        shutil.rmtree(src, ignore_errors=True)  # agora é a versão instalada
        prune_versions()
        if was: service_cmd("start")
    except Exception as e:
        return str(e)
    return None
def relaunch_gui():
    """Abre a janela de novo depois que esta fechar (a instância única impede abrir antes)."""
    gui = str(Path(__file__).resolve()); args = sys.argv[1:]
    if IS_WIN:
        # Arguments are passed as a list, never interpolated into cmd.exe.
        subprocess.Popen(
            [sys.executable, "-c",
             "import sys,time,subprocess;time.sleep(1);subprocess.Popen(sys.argv[1:])",
             sys.executable, gui, *args],
            creationflags=NOWIN | 0x00000008)
    else:
        subprocess.Popen(["sh", "-c", 'sleep 1; exec "$0" "$@"', sys.executable, gui, *args], start_new_session=True)

def music_dir(): return data_dir() / "music-presets"
def music_presets():
    try: return sorted(p.stem for p in music_dir().glob("*.json"))
    except Exception: return []
def music_preset_read(n):
    try: return json.loads((music_dir() / f"{n}.json").read_text())
    except Exception: return None
def music_preset_write(n, d):
    music_dir().mkdir(parents=True, exist_ok=True); (music_dir() / f"{n}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1))

MUSIC_KEYS = ["music_style", "music_min", "music_sens", "music_band", "music_in_bass", "music_out_bass", "music_in_treble",
              "music_out_treble", "music_in_vol", "music_out_vol", "music_in_rpm", "music_out_rpm",
              "music_on_bass", "music_on_treble", "music_on_vol", "music_on_rpm"]
MUSIC_BUILTIN = {
    "Festa (batida forte)": dict(music_style="center", music_min=15.0, music_sens=1.3, music_band="bass", tip="Um anel de luz parte do centro a cada batida forte."),
    "Lounge (suave)": dict(music_style="breath", music_min=45.0, music_sens=1.0, music_band="both", tip="Respiração lenta que acompanha o volume da música."),
    "Eletrônica (graves)": dict(music_style="dim", music_min=10.0, music_sens=1.2, music_band="bass", music_in_bass=0.15, tip="Escurece forte no bumbo e ignora graves fracos."),
    "Rock / Pop": dict(music_style="boost", music_min=30.0, music_sens=1.0, music_band="both", tip="A luz sobe ao normal a cada batida de graves ou agudos."),
    "Corrida (REV sound)": dict(music_style="rev", music_min=20.0, music_sens=1.0, music_band="bass", tip="Acompanha o giro do motor em jogos de corrida."),
    "Trilha de cinema": dict(music_style="heat", music_min=30.0, music_sens=0.9, music_band="both", tip="As cores vão do azul ao vermelho conforme o volume."),
}
DYN_TIPS = {
    "screen": "Cada trecho da fita copia a cor da borda da tela mais próxima.",
    "dominant": "A fita inteira usa a cor dominante da cena.",
    "dominant_lr": "Lado esquerdo e direito usam a cor dominante de cada metade da tela.",
    "dominant_4": "Cada borda (esquerda, topo, direita, embaixo) usa a cor dominante da sua região.",
    "palette": "Cada cor da tela vira a cor mais próxima da sua paleta; o brilho segue a tela.",
}
EFFECT_TIPS = {
    "breathing": "O brilho sobe e desce suavemente, como uma respiração.",
    "pulsing": "Pulsos suaves de brilho com a cor escolhida.",
    "rainbow": "Percorre todo o espectro de cores.",
    "fade": "Transição suave entre as cores da paleta.",
    "comet": "Um ponto luminoso com cauda percorre a fita.",
    "aurora": "As cores da paleta se movem como uma aurora.",
    "fire": "Chamas tremulando em tons de fogo.",
}
BAND_TIPS = {
    "bass": "Reage ao bumbo e ao baixo (sons graves, até cerca de 150 Hz).",
    "treble": "Reage a voz, pratos e chimbais (sons agudos, acima de cerca de 2 kHz).",
    "both": "Reage ao que for mais forte entre graves e agudos.",
}
STYLE_TIPS = {
    "dim": "A luz normal escurece na batida e volta. Quanto menor o mínimo, mais forte o pulso.",
    "boost": "A luz fica no mínimo e sobe ao normal a cada batida.",
    "flash": "Mistura branco na luz a cada batida (clarão). Pode incomodar quem é sensível a luz piscante.",
    "sat": "As cores ficam mais vivas na batida e voltam ao normal.",
    "comp": "Na batida a cor vai para a cor oposta e volta.",
    "pal": "A cada batida forte a luz muda para a próxima cor da sua paleta, mantendo o desenho da cena.",
    "split": "Graves pulsam as laterais e embaixo; agudos pulsam o topo.",
    "vol": "O brilho acompanha o volume da música o tempo todo, sem depender de batida.",
    "wave": "Uma onda de luz branca corre pela fita a cada batida.",
    "vu": "Medidor de volume: a luz acende do centro para as pontas conforme o volume.",
    "spark": "Pontos aleatórios faíscam em branco na batida, como glitter.",
    "rev": "Jogos de corrida: acompanha o giro do motor (RPM), avermelha perto do limite e dá um clarão na troca de marcha.",
    "hue": "Na batida o matiz das cores gira (vermelho, verde, azul...) e volta ao normal.",
    "breath": "A luz respira em ciclos; quanto mais alto o volume, mais rápido o ritmo.",
    "chase": "Um ponto brilhante corre pela fita; a velocidade sobe com o volume e a batida.",
    "center": "Cada batida lança um anel de luz do centro da fita para as pontas.",
    "confetti": "Na batida, LEDs aleatórios acendem em cores da sua paleta, como confete.",
    "heat": "Termômetro de cores: do azul (baixo) ao vermelho (alto) conforme o volume.",
    "quad": "Esquerda reage aos graves, direita aos agudos, topo ao volume e embaixo ao mais forte entre graves e agudos.",
    "heartbeat": "Dois pulsos seguidos na batida, como um coração, e volta ao normal.",
    "echo": "Escurece na batida e demora a voltar, deixando um rastro longo.",
    "pingpong": "A cada batida a luz alterna entre a primeira e a segunda metade da fita.",
}

def list_presets():
    try: return sorted(p.stem for p in presets_dir().glob("*.toml"))
    except Exception: return []

def write_preset(name, c):
    presets_dir().mkdir(parents=True, exist_ok=True)
    preset_path(name).write_text(cfg_text(c, True))

def read_preset(name):
    try: d = tomllib.loads(preset_path(name).read_text())
    except Exception: return None
    if "preset_version" in d: return ("full", cfg_from_dict(d))
    return ("legacy", d)

def apply_preset_data(c, p):
    kind, data = p
    if kind == "full":
        c.clear(); c.update(copy.deepcopy(data))
    else:
        for k in ("brightness", "smoothing", "saturation", "gamma", "fps"):
            if k in data: c[k] = type(DEFAULTS[k])(data[k])

def ensure_default_presets():
    if list_presets(): return
    base = read_config()
    def make(bri, smo, fps, th):
        c = copy.deepcopy(base); c.update(brightness=bri, smoothing=smo, fps=fps); apply_color_theme(c, THEMES[th]); return c
    write_preset("Padrão", make(200, 0.15, 60, 0))
    write_preset("Suave (filmes)", make(160, 0.5, 30, 3))
    write_preset("Vivo (jogos)", make(255, 0.05, 60, 1))
    write_preset("Noturno", make(60, 0.4, 30, 4))

def apply_preset_by_name(name):
    p = read_preset(name)
    if not p: return "Não consegui ler o preset."
    c = read_config(); apply_preset_data(c, p); normalize(c); write_config(c)
    return service_cmd("restart")

# ───────────────────────── Serviço / sistema ─────────────────────────
def win_dir():
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Quiklight"

def win_running():
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq quiklight.exe", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, creationflags=NOWIN)
        return "quiklight.exe" in r.stdout.lower()
    except Exception: return False

def win_service(verb):
    exe = win_dir() / "quiklight.exe"
    def stop():
        subprocess.run(["taskkill", "/IM", "quiklight.exe", "/F"], capture_output=True, creationflags=NOWIN)
        try: subprocess.run([str(exe), "--off"], capture_output=True, creationflags=NOWIN, timeout=10)
        except Exception: pass
    def start():
        if not exe.exists(): return "quiklight.exe não encontrado em " + str(exe.parent)
        log = open(win_dir() / "quiklight.log", "a")
        subprocess.Popen([str(exe)], stdout=log, stderr=log, creationflags=NOWIN | 0x00000008)
        return None
    if verb == "start": return None if win_running() else start()
    if verb == "stop": stop(); return None
    if verb == "restart": stop(); time.sleep(0.6); return start()
    return None


# Autostart is a GUI setting, not a part of the LED configuration/presets.
# Windows: HKCU Run (no administrator or PowerShell policy changes).
# KDE/Linux: XDG autostart for the tray + systemd user service for the LEDs.
def autostart_desktop_path():
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "autostart" / "quiklight-gui.desktop"


def autostart_enabled():
    if IS_WIN:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                return bool(winreg.QueryValueEx(key, "QuiklightWindows")[0])
        except FileNotFoundError:
            return False
        except OSError:
            return False

    # The service runs at systemd user's default.target in both KDE
    # Desktop and Gamescope. The KDE tray autostart is independent.
    # Never require a KDE .desktop file to report service autostart.
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", "quiklight.service"],
            capture_output=True, text=True, timeout=3,
        )
        return result.returncode == 0 and result.stdout.strip() in ("enabled", "enabled-runtime")
    except (OSError, subprocess.TimeoutExpired):
        return False

def set_autostart(enabled):
    if IS_WIN:
        import winreg
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0,
                                winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            if enabled:
                interpreter = Path(sys.executable)
                pythonw = interpreter.with_name("pythonw.exe")
                if pythonw.is_file():
                    interpreter = pythonw
                launcher = Path(__file__).resolve().with_name("quiklight_windows.pyw")
                if not launcher.is_file():
                    raise RuntimeError("Iniciador Windows (.pyw) não encontrado.")
                args = [str(interpreter), str(launcher), "--tray"]
                winreg.SetValueEx(key, "QuiklightWindows", 0, winreg.REG_SZ,
                                  subprocess.list2cmdline(args))
            else:
                try:
                    winreg.DeleteValue(key, "QuiklightWindows")
                except FileNotFoundError:
                    pass
        return

    # The installed Bazzite Quiklight already uses these exact paths:
    #   ~/.config/systemd/user/quiklight.service  (driver, also Gamescope)
    #   ~/.config/autostart/quiklight-gui.desktop (KDE tray only)
    # Preserve those files. Never create another driver or override an
    # existing desktop entry just because the toggle is switched on.
    desktop = autostart_desktop_path()
    parked = desktop.with_name(desktop.name + ".disabled-by-quiklight")
    # Refuse conflicting backups before modifying the running startup setup.
    if not enabled and desktop.exists() and parked.exists():
        raise RuntimeError(
            "Entrada KDE já possui uma cópia desativada; "
            "não substituirei nenhum arquivo."
        )
    action = "enable" if enabled else "disable"
    result = subprocess.run(
        ["systemctl", "--user", action, "quiklight.service"],
        capture_output=True, text=True, timeout=8,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or
                            "Não foi possível configurar quiklight.service.").strip())

    if enabled:
        if not desktop.exists() and parked.exists():
            parked.replace(desktop)  # Restore original KDE autostart untouched.
        elif not desktop.exists():
            # Only recreate the tray entry if it is truly absent. Use the
            # wrapper installed by Quiklight instead of launching a copy of
            # the driver or depending on the current Git checkout's path.
            wrapper = Path.home() / ".local" / "bin" / "quiklight-gui"
            if wrapper.is_file():
                desktop.parent.mkdir(parents=True, exist_ok=True)
                executable = str(wrapper).replace("\\", "\\\\").replace('"', '\\"')
                desktop.write_text(
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Quiklight (bandeja)\n"
                    'Exec="' + executable + '" --tray\n'
                    "Icon=preferences-desktop-display\n"
                    "Terminal=false\n"
                    "X-KDE-autostart-after=panel\n",
                    encoding="utf-8",
                )
    else:
        # Reversible: keep the exact entry installed on Bazzite so that
        # re-enabling the toggle does not clobber installer customizations.
        if desktop.exists():
            desktop.replace(parked)

_dev_cache = [0.0, 0]
_dev_polling = False

def _refresh_windows_usb_devices():
    global _dev_polling
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-PnpDevice -PresentOnly -Class USB | Where-Object { $_.InstanceId -like '*VID_1A86&PID_FE07*' } | Measure-Object).Count"],
            capture_output=True, text=True, timeout=10, creationflags=NOWIN)
        if r.returncode == 0:
            _dev_cache[1] = int(r.stdout.strip() or 0)
    except Exception:
        pass
    finally:
        _dev_polling = False


def sctl(*a):
    return subprocess.run(["systemctl", "--user", *a], capture_output=True, text=True)

def is_active():
    if IS_WIN: return win_running()
    try: return sctl("is-active", "quiklight").stdout.strip() in ("active", "activating")
    except Exception: return False

def service_cmd(verb):
    if IS_WIN: return win_service(verb)
    try: r = sctl(verb, "quiklight")
    except Exception as e: return str(e)
    return None if r.returncode == 0 else (r.stderr.strip() or f"systemctl {verb} falhou")

def journal(n=40):
    if IS_WIN:
        try: return "\n".join((win_dir() / "quiklight.log").read_text(errors="replace").splitlines()[-n:])
        except Exception: return ""
    try:
        return subprocess.run(["journalctl", "--user", "-u", "quiklight", "-n", str(n), "--no-pager"],
                              capture_output=True, text=True).stdout
    except Exception: return ""

def count_devices():
    if IS_WIN:
        # Device enumeration can launch PowerShell for up to 10 seconds.
        # Never let it block the Qt GUI or delay starting the LED backend.
        global _dev_polling
        if not _dev_polling and time.time() - _dev_cache[0] > 30:
            _dev_polling = True
            _dev_cache[0] = time.time()
            threading.Thread(target=_refresh_windows_usb_devices, daemon=True).start()
        return _dev_cache[1]
    s = set()
    base = Path("/sys/bus/hid/devices")
    try: items = list(base.iterdir())
    except Exception: return 0
    for d in items:
        try:
            if "0003:00001A86:0000FE07" in (d / "uevent").read_text().upper():
                s.add(str(d.resolve().parent.parent))
        except Exception: pass
    return len(s)

def is_dynamic(m): return m not in ("static", "effect")

def is_structural(a, b_):
    sig = lambda c: [(g["device"], g["edge"], g["leds"], g["reverse"]) for g in c["segment"]]
    return (is_dynamic(a["mode"]) != is_dynamic(b_["mode"]) or a["cap_w"] != b_["cap_w"] or a["cap_h"] != b_["cap_h"]
            or a["capture_limit"] != b_["capture_limit"] or (is_dynamic(b_["mode"]) and a["fps"] != b_["fps"])
            or sig(a) != sig(b_))

DYN = [("screen", "Cores das bordas"), ("dominant", "Cor dominante"),
       ("dominant_lr", "Cor dominante esquerda/direita"), ("dominant_4", "Cor dominante nas bordas"),
       ("palette", "Cores selecionadas")]
EFFECTS = [("breathing", "Breathing (respiração suave)"), ("pulsing", "Pulsing suave"),
           ("rainbow", "Rainbow (espectro completo)"), ("fade", "Fade entre as cores da paleta"),
           ("comet", "Cometa"), ("aurora", "Aurora (paleta em movimento)"), ("fire", "Fogo")]
EDGES = [("left", "Esquerda"), ("top", "Topo"), ("right", "Direita"), ("bottom", "Embaixo")]
SEG_COLORS = [(240, 170, 60), (80, 200, 120), (90, 160, 255), (230, 100, 180), (170, 130, 255), (240, 90, 80)]

def mode_label(m):
    if m == "static": return tr("Estático")
    if m == "effect": return tr("Efeitos")
    return tr("Dinâmico") + " · " + tr(dict(DYN).get(m, "Cores das bordas"))

WTHEMES = [
    ("Escuro", True, (30, 31, 36), (42, 44, 52), (90, 150, 255)),
    ("Claro", False, (243, 244, 247), (255, 255, 255), (40, 110, 230)),
    ("Meia-noite", True, (12, 16, 32), (24, 30, 56), (70, 130, 255)),
    ("Neon", True, (14, 10, 24), (30, 20, 50), (255, 60, 190)),
    ("Floresta", True, (14, 24, 20), (26, 42, 34), (70, 210, 130)),
    ("Pôr do sol", True, (28, 16, 18), (48, 28, 30), (255, 140, 50)),
]

def read_settings():
    rt, ap, th = False, None, 2
    try:
        for l in (data_dir() / "gui_settings").read_text().splitlines():
            if l.startswith("realtime="): rt = l.split("=", 1)[1].strip() == "1"
            if l.startswith("active_preset=") and l.split("=", 1)[1].strip(): ap = l.split("=", 1)[1].strip()
    except Exception: pass
    try:
        n = (data_dir() / "gui_theme").read_text().strip()
        th = [t[0] for t in WTHEMES].index(n)
    except Exception: pass
    return rt, ap, th

def save_settings(rt, ap, th):
    data_dir().mkdir(parents=True, exist_ok=True)
    (data_dir() / "gui_settings").write_text(f"realtime={1 if rt else 0}\nactive_preset={ap or ''}\n")
    (data_dir() / "gui_theme").write_text(WTHEMES[th][0])

# backup
def downloads_dir():
    p = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    return Path(p) if p else Path.home()

def list_backups():
    try: return sorted(downloads_dir().glob("quiklight-backup-*.toml"), reverse=True)
    except Exception: return []

def backup_text():
    t = "# Quiklight backup\n### CONFIG\n"
    try: t += config_path().read_text()
    except Exception: pass
    for n in list_presets():
        t += f"\n### PRESET {n}\n" + preset_path(n).read_text()
    return t

def import_backup(text):
    cfg_txt, presets, cur, markers = None, [], None, False
    def flush():
        nonlocal cfg_txt
        if cur:
            if cur[0] == "CONFIG": cfg_txt = cur[2]
            else: presets.append((cur[1], cur[2]))
    for line in text.splitlines():
        if line.startswith("### "):
            markers = True; flush(); h = line[4:].strip()
            if h == "CONFIG": cur = ["CONFIG", "", ""]
            elif h.startswith("PRESET "): cur = ["PRESET", clean_name(h[7:]), ""]
            else: cur = None
        elif cur is not None:
            cur[2] += line + "\n"
    flush()
    if not markers: cfg_txt = text
    n = 0
    if cfg_txt is not None:
        try: tomllib.loads(cfg_txt)
        except Exception as e: return None, f"Configuração inválida no backup: {e}"
        data_dir().mkdir(parents=True, exist_ok=True); config_path().write_text(cfg_txt); n += 1
    for name, body in presets:
        try: tomllib.loads(body)
        except Exception: continue
        if name:
            presets_dir().mkdir(parents=True, exist_ok=True); preset_path(name).write_text(body); n += 1
    return (n, None) if n else (None, "Backup não reconhecido.")

# métricas do app
class Metrics:
    """Mede só o Quiklight: a janela (este processo), o serviço `quiklight` e os processos filhos dele
    (captura de tela/áudio). CPU = tempo de CPU dos processos; memória = PSS (divide as bibliotecas
    compartilhadas); GPU = tempo de engine em /proc/<pid>/fdinfo (só se o driver expõe)."""
    def __init__(self):
        self.pids = []; self.scan_t = 0.0; self.reset(); self.gpu_total = None
    def reset(self):
        self.last = None; self.ticks = {}; self.gpu = {}
        self.cpu = None; self.mem = None; self.gpu_app = None
    def find_pids(self):
        info = {}
        for e in Path("/proc").iterdir():
            if not e.name.isdigit(): continue
            try:
                s = (e / "stat").read_text()
                info[int(e.name)] = (s[s.index("(") + 1:s.rindex(")")], int(s[s.rindex(")") + 2:].split()[1]))
            except Exception: continue
        own = {os.getpid()} | {p for p, (c, _) in info.items() if c == "quiklight"}
        grow = True
        while grow:
            grow = False
            for p, (_, pp) in info.items():
                if p not in own and pp in own: own.add(p); grow = True
        return sorted(own)
    def sample(self):
        if IS_WIN: return
        now = time.time(); dt = (now - self.last) if self.last else 0
        if not self.pids or now - self.scan_t > 10: self.pids = self.find_pids(); self.scan_t = now
        tck = os.sysconf("SC_CLK_TCK") or 100
        ticks, gpu, mem, seen = {}, {}, 0.0, False
        for pid in self.pids:
            e = Path("/proc") / str(pid)
            try:
                f = (e / "stat").read_text().rsplit(")", 1)[1].split()
                ticks[pid] = int(f[11]) + int(f[12])
            except Exception: continue
            try:
                pss = [int(l.split()[1]) for l in (e / "smaps_rollup").read_text().splitlines() if l.startswith("Pss:")]
                mem += pss[0] * 1024
            except Exception:
                try: mem += int((e / "statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
                except Exception: pass
            cl = {}
            try: fds = list((e / "fdinfo").iterdir())
            except Exception: fds = []
            for fd in fds:
                try: txt = fd.read_text()
                except Exception: continue
                if "drm-engine" not in txt: continue
                seen = True; cid, ns = "", 0
                for l in txt.splitlines():
                    if l.startswith("drm-client-id:"): cid = l.split(":", 1)[1].strip()
                    elif l.startswith(("drm-engine-gfx:", "drm-engine-compute:")):
                        try: ns += int(l.split(":", 1)[1].split()[0])
                        except Exception: pass
                cl[cid] = ns
            gpu[pid] = sum(cl.values())
        if dt > 0 and self.ticks:
            dc = sum(max(0, t - self.ticks[p]) for p, t in ticks.items() if p in self.ticks)
            self.cpu = dc / tck / dt * 100
            if seen: self.gpu_app = sum(max(0, t - self.gpu[p]) for p, t in gpu.items() if p in self.gpu) / 1e9 / dt * 100
        if not seen: self.gpu_app = None
        self.mem = mem / 1048576; self.ticks, self.gpu, self.last = ticks, gpu, now
        self.gpu_total = None
        for p in Path("/sys/class/drm").glob("*/device/gpu_busy_percent"):
            try: self.gpu_total = float(p.read_text().strip()); break
            except Exception: pass

# ───────────────────────── Pré-visualização ─────────────────────────
def rainbow_bulb_icon():
    pm = QPixmap(64, 64); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QConicalGradient(32, 26, 0)
    for k, col in enumerate(("#ff3b30", "#ff9500", "#ffcc00", "#34c759", "#32ade6", "#5856d6", "#af52de", "#ff3b30")):
        g.setColorAt(k / 7, QColor(col))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(g)); p.drawEllipse(QPointF(32, 26), 21, 21)
    p.setBrush(QBrush(QColor(170, 170, 175)))
    p.drawRoundedRect(QRectF(23, 46, 18, 7), 2, 2); p.drawRoundedRect(QRectF(26, 54, 12, 6), 2, 2)
    p.end(); return QIcon(pm)

def music_icon():
    pm = QPixmap(64, 64); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen)
    for k, (col, h) in enumerate((("#ff3b30", 30), ("#ff9500", 46), ("#34c759", 58), ("#32ade6", 40), ("#af52de", 24))):
        p.setBrush(QBrush(QColor(col))); p.drawRoundedRect(QRectF(5 + k * 11.5, 62 - h, 8, h), 3, 3)
    p.end(); return QIcon(pm)

def app_icon():
    ic = QIcon.fromTheme("preferences-desktop-display")
    return ic if not ic.isNull() else rainbow_bulb_icon()

class InfoTile(QFrame):
    def __init__(self, cap):
        super().__init__(); self.setObjectName("tile")
        l = QVBoxLayout(self); l.setContentsMargins(12, 8, 12, 8); l.setSpacing(1)
        self.cap = QLabel(cap); self.cap.setObjectName("cap")
        self.val = QLabel(); self.val.setObjectName("val"); self.val.setTextFormat(Qt.TextFormat.RichText); self.val.setWordWrap(True)
        l.addWidget(self.cap); l.addWidget(self.val)
    def set(self, html): self.val.setText(html)

class MusicMeter(QWidget):
    LW = 130.0
    KEYS = (("music_in_bass", "music_out_bass"), ("music_in_treble", "music_out_treble"),
            ("music_in_vol", "music_out_vol"), ("music_in_rpm", "music_out_rpm"))
    ONS = ("music_on_bass", "music_on_treble", "music_on_vol", "music_on_rpm")
    TIPS = ("Graves: bumbo e baixo (até cerca de 150 Hz). É a batida: dispara os estilos que pulsam a cada batida.",
            "Agudos: voz, pratos e chimbais (acima de cerca de 2 kHz). Dispara a batida quando \"Reagir a\" inclui agudos.",
            "Volume: a intensidade geral do som (todas as frequências juntas) comparada com o pico recente. Não detecta batidas: sobe e desce com a música. Move os estilos Brilho segue o volume, Medidor de volume, Respiração, Corrida de luz, Termômetro de cores e o topo do Quatro bordas.",
            "Motor (RPM): o tom grave do motor em jogos de corrida. Só o estilo REV sound usa.",
            "Reação da luz: o que está movendo a luz agora, depois de aplicar interruptores, entrada mínima, saída máxima e sensibilidade.")
    def __init__(self, win):
        super().__init__(); self.win = win; self.v = [0.0] * 5; self.drag = None; self.tip_bar = -1
        self.setMinimumHeight(170); self.setMouseTracking(True)
    def _geo(self): return 4.0, (self.height() - 4.0) / 5.0
    def _x(self, f): return self.LW + (self.width() - self.LW - 4) * f
    def _f(self, x): return max(0.0, min(1.0, (x - self.LW) / max(1.0, self.width() - self.LW - 4)))
    def _row(self, y):
        top, h = self._geo(); b = int((y - top) // h)
        return b if 0 <= b < 5 else None
    def _bar(self, y):
        b = self._row(y); return b if (b is not None and b < 4) else None
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fg = self.palette().text().color(); c = self.win.cfg
        names = (tr("Graves"), tr("Agudos"), tr("Volume"), tr("Motor (RPM)"), tr("Reação da luz"))
        top, h = self._geo()
        f = p.font(); f.setPixelSize(13); p.setFont(f); small = QFont(f); small.setPixelSize(11)
        for i, (n, v) in enumerate(zip(names, self.v)):
            y = top + i * h + 2; bh = h - 6; v = max(0.0, min(1.0, v)); on = True if i == 4 else bool(c[self.ONS[i]])
            if i < 4:
                px = QRectF(0, y + (bh - 14) / 2, 26, 14); p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(52, 199, 89) if on else QColor(120, 120, 130)); p.drawRoundedRect(px, 7, 7)
                p.setBrush(QColor(255, 255, 255)); p.drawEllipse(QPointF(px.x() + (19 if on else 7), px.y() + 7), 5, 5)
            tc = QColor(fg); tc.setAlpha(255 if on else 110); p.setPen(tc)
            p.drawText(QRectF(34, y, self.LW - 34, bh), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), n)
            r = QRectF(self.LW, y, self.width() - self.LW - 4, bh)
            p.setPen(Qt.PenStyle.NoPen); bg = QColor(fg); bg.setAlpha(35); p.setBrush(bg); p.drawRoundedRect(r, 4, 4)
            col = QColor(60, 170, 255)
            if i == 4: col = QColor(255, 70, 70) if v > 0.6 else QColor(255, 150, 40)
            if not on: col.setAlpha(70)
            p.setBrush(col); p.drawRoundedRect(QRectF(r.x(), r.y(), r.width() * v, r.height()), 4, 4)
            if i == 4:
                p.setPen(QPen(fg, 1)); x = r.x() + r.width() * 0.6; p.drawLine(QPointF(x, r.y()), QPointF(x, r.y() + r.height()))
                continue
            lo, hi = c[self.KEYS[i][0]], c[self.KEYS[i][1]]
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(0, 0, 0, 80))
            p.drawRect(QRectF(self._x(0), y, self._x(lo) - self._x(0), bh)); p.drawRect(QRectF(self._x(hi), y, self._x(1) - self._x(hi), bh))
            for fr in (lo, hi):
                x = self._x(fr); p.setPen(QPen(QColor(255, 200, 0, 255 if on else 90), 2)); p.drawLine(QPointF(x, y - 1), QPointF(x, y + bh + 1))
            p.setFont(small); p.setPen(tc)
            p.drawText(r.adjusted(0, 0, -6, 0), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), f"{lo * 100:.0f}–{hi * 100:.0f}%")
            p.setFont(f)
        p.end()
    def _move(self, e):
        b, w = self.drag; kin, kout = self.KEYS[b]; f = round(self._f(e.position().x()), 2); c = self.win.cfg
        if w == "in": c[kin] = round(min(f, c[kout] - 0.05), 2)
        else: c[kout] = round(max(f, c[kin] + 0.05), 2)
        self.win.changed(); self.update()
    def mousePressEvent(self, e):
        b = self._bar(e.position().y())
        if b is None: return
        c = self.win.cfg
        if e.position().x() < 32:
            c[self.ONS[b]] = not c[self.ONS[b]]; self.win.changed(); self.update(); return
        if e.position().x() < self.LW: return
        f = self._f(e.position().x()); kin, kout = self.KEYS[b]
        self.drag = (b, "in" if abs(f - c[kin]) <= abs(f - c[kout]) else "out"); self._move(e)
    def mouseDoubleClickEvent(self, e):
        b = self._bar(e.position().y())
        if b is None or e.position().x() < self.LW: return
        self.drag = None; self.win.cfg[self.KEYS[b][0]] = 0.0; self.win.cfg[self.KEYS[b][1]] = 1.0; self.win.changed(); self.update()
    def mouseMoveEvent(self, e):
        if self.drag: self._move(e); return
        r = self._row(e.position().y()); x = e.position().x()
        if r != self.tip_bar: self.tip_bar = r; self.setToolTip(tr(self.TIPS[r]) if r is not None else "")
        if r is not None and r < 4 and x < 32: self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif r is not None and r < 4 and x > self.LW: self.setCursor(Qt.CursorShape.SizeHorCursor)
        else: self.setCursor(Qt.CursorShape.ArrowCursor)
    def mouseReleaseEvent(self, e): self.drag = None

class Preview(QWidget):
    def __init__(self, win):
        super().__init__(); self.win = win; self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    def paintEvent(self, _):
        c = self.win.cfg; p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height(); sw = min(W - 40, (H - 40) * 16 / 9); sh = sw * 9 / 16
        ox, oy = (W - sw) / 2, (H - sh) / 2
        P = lambda fx, fy: (ox + fx * sw, oy + fy * sh)
        p.fillRect(QRectF(ox, oy, sw, sh), QColor(22, 22, 26))
        p.setPen(QPen(QColor(130, 130, 130), 1)); p.drawRect(QRectF(ox, oy, sw, sh))
        ix0, iy0 = min(max(c["inset_left"] / 100, 0), .45), min(max(c["inset_top"] / 100, 0), .45)
        ix1, iy1 = 1 - min(max(c["inset_right"] / 100, 0), .45), 1 - min(max(c["inset_bottom"] / 100, 0), .45)
        p.setPen(QPen(QColor(120, 160, 255), 1))
        a, bb = P(ix0, iy0), P(ix1, iy1); p.drawRect(QRectF(a[0], a[1], bb[0] - a[0], bb[1] - a[1]))
        tx = max(c["border"] / max(c["cap_w"], 1), .025); ty = max(c["border"] / max(c["cap_h"], 1), .04)
        for si, s in enumerate(c["segment"]):
            n = s["leds"]
            if n <= 0: continue
            cr, cg, cb = SEG_COLORS[si % len(SEG_COLORS)]
            for i in range(n):
                j = n - 1 - i if s["reverse"] else i
                u, v = j / n, (j + 1) / n; e = s["edge"]
                if e == "left": r = (ix0, min(ix0 + tx, ix1), iy0 + (iy1 - iy0) * u, iy0 + (iy1 - iy0) * v)
                elif e == "right": r = (max(ix1 - tx, ix0), ix1, iy0 + (iy1 - iy0) * u, iy0 + (iy1 - iy0) * v)
                elif e == "bottom": r = (ix0 + (ix1 - ix0) * u, ix0 + (ix1 - ix0) * v, max(iy1 - ty, iy0), iy1)
                else: r = (ix0 + (ix1 - ix0) * u, ix0 + (ix1 - ix0) * v, iy0, min(iy0 + ty, iy1))
                x0, y0 = P(r[0], r[2]); x1, y1 = P(r[1], r[3]); rect = QRectF(x0, y0, x1 - x0, y1 - y0)
                p.setPen(QPen(QColor(0, 0, 0, 160), 1)); p.setBrush(QBrush(QColor(cr, cg, cb, 130))); p.drawRect(rect)
                if i == 0 or (i == n - 1 and n > 1):
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QBrush(QColor(40, 220, 80) if i == 0 else QColor(235, 60, 60)))
                    p.drawEllipse(rect.center(), 3.5, 3.5)
        if self.win.live_on: self.paint_live(p, ox, oy, sw, sh)

    def paint_live(self, p, ox, oy, sw, sh):
        c = self.win.applied; data = self.win.live_data
        counts = {}
        for s_ in c["segment"]:
            if s_["leds"] > 0: counts[s_["device"]] = counts.get(s_["device"], 0) + s_["leds"]
        offs, acc = {}, 0
        for d in sorted(counts): offs[d] = acc; acc += counts[d]
        used = {d: 0 for d in counts}
        for s_ in c["segment"]:
            n = s_["leds"]
            for i in range(n):
                idx = offs.get(s_["device"], 0) + used[s_["device"]]; used[s_["device"]] += 1
                j = n - 1 - i if s_["reverse"] else i
                f = (j + 0.5) / n; e = s_["edge"]
                if e == "left": x, y = ox - 12, oy + sh * f
                elif e == "right": x, y = ox + sw + 12, oy + sh * f
                elif e == "bottom": x, y = ox + sw * f, oy + sh + 12
                else: x, y = ox + sw * f, oy - 12
                o = idx * 3
                if o + 2 < len(data) and (data[o] or data[o + 1] or data[o + 2]):
                    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(data[o], data[o + 1], data[o + 2])))
                else:
                    p.setPen(QPen(QColor(90, 90, 90), 1)); p.setBrush(QBrush(QColor(30, 30, 34)))
                p.drawEllipse(QPointF(x, y), 4.5, 4.5)

# ───────────────────────── Janela ─────────────────────────
TAB_ICONS = {"Home": "go-home", "Captura": "video-display",
             "LEDs e fitas": "view-list-details", "Presets": "bookmark-new", "Hardware": "drive-removable-media-usb", "Sistema": "preferences-system"}
TABS = [("🏠", "Home"), ("💡", "Iluminação e cores"), ("🖥", "Captura"), ("🎵", "Música"),
        ("✨", "LEDs e fitas"), ("💾", "Presets"), ("🔌", "Hardware"), ("⚙", "Sistema")]

class Win(QMainWindow):
    def __init__(self, app):
        super().__init__(); self.app = app
        self.cfg = read_config(); self.applied = copy.deepcopy(self.cfg)
        self.realtime, self.active_preset, self.theme_idx = read_settings()
        self.block = 0; self.title_icons = []; self.grid_reg = {}; self.binders = []; self.metrics = Metrics(); self.last_dyn = "screen"
        if is_dynamic(self.cfg["mode"]): self.last_dyn = self.cfg["mode"]
        self.running = is_active(); self.devices = count_devices()
        self.rt_timer = QTimer(self); self.rt_timer.setSingleShot(True); self.rt_timer.timeout.connect(self.apply_now)
        self.live_on = False; self.live_data = b""
        self.live_timer = QTimer(self); self.live_timer.timeout.connect(self.update_live)
        self.music_timer = QTimer(self); self.music_timer.timeout.connect(self.update_music); self.music_timer.start(100)
        self.setWindowTitle("Quiklight"); self.setWindowIcon(app_icon())
        self.resize(940, 640); self.setMinimumSize(560, 420)
        root = QWidget(); self.setCentralWidget(root); v = QVBoxLayout(root); v.setContentsMargins(10, 8, 10, 4)
        v.addWidget(self.build_top())
        body = QHBoxLayout(); v.addLayout(body, 1)
        self.side = QListWidget(); self.side.setIconSize(QSize(22, 22)); self.side.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.side.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.side.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.side.setSpacing(1); body.addWidget(self.side)
        self.stack = QStackedWidget(); body.addWidget(self.stack, 1)
        self.preview = Preview(self)
        for builder in (self.pg_home, self.pg_luz_cores, self.pg_captura, self.pg_musica, self.pg_leds, self.pg_presets, self.pg_hw, self.pg_sistema):
            w, lay = QWidget(), None
            lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop); builder(lay)
            sa = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.Shape.NoFrame); sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); sa.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); sa.setWidget(w)
            self.stack.addWidget(sa)
        self.side.currentRowChanged.connect(self.on_tab)
        self.fill_side(False); self.side.setCurrentRow(0)
        self.apply_theme(); self.sync_all()
        self.poll = QTimer(self); self.poll.timeout.connect(self.on_poll); self.poll.start(2000)
        self.metrics.sample()

    # ── helpers de widgets ──
    def title(self, lay, text):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 8, 0, 0); h.setSpacing(8)
        ic = QLabel(); ic.setFixedSize(22, 22); ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setPixmap(title_icon(text, QColor(*WTHEMES[self.theme_idx][4]))); self.title_icons.append((ic, text))
        l = QLabel(tr(text)); l.setObjectName("sec")
        h.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter); h.addWidget(l, 0, Qt.AlignmentFlag.AlignVCenter); h.addStretch(1); lay.addWidget(w); return l
    def slider(self, grid, i, text, key, lo, hi, step, fmt="{:.2f}"):
        box = QWidget(); v = QVBoxLayout(box); v.setContentsMargins(0, 2, 0, 2); v.setSpacing(0)
        top = QHBoxLayout(); lab = QLabel(tr(text)); val = QLabel(); val.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(lab, 1); top.addWidget(val); v.addLayout(top)
        sl = NoWheelSlider(Qt.Orientation.Horizontal); sl.setRange(0, int(round((hi - lo) / step))); v.addWidget(sl)
        is_int = key in INTS
        def refresh():
            x = float(self.cfg[key]); self.block += 1; sl.setValue(int(round((x - lo) / step))); self.block -= 1; val.setText(fmt.format(x))
        def moved(n):
            if self.block: return
            x = lo + n * step; self.cfg[key] = int(round(x)) if is_int else round(x, 4); val.setText(fmt.format(x)); self.changed()
        sl.valueChanged.connect(moved); self.binders.append(refresh); refresh(); grid.addWidget(box, i // 2, i % 2); self.grid_reg.setdefault(id(grid), (grid, []))[1].append(box)
        return box
    def sgrid(self, lay):
        g = QGridLayout(); g.setColumnStretch(0, 1); g.setColumnStretch(1, 1); lay.addLayout(g); return g
    def check(self, lay, text, key):
        cb = QCheckBox(tr(text))
        def refresh(): self.block += 1; cb.setChecked(bool(self.cfg[key])); self.block -= 1
        def tog(x):
            if self.block: return
            self.cfg[key] = bool(x); self.changed()
        cb.toggled.connect(tog); self.binders.append(refresh); refresh(); lay.addWidget(cb); return cb
    def color_button(self, getter, setter):
        btn = QPushButton()
        def refresh():
            r, g, b_ = getter(); btn.setText(f"#{r:02x}{g:02x}{b_:02x}")
            btn.setStyleSheet(f"background: rgb({r},{g},{b_}); color: {'black' if r*0.3+g*0.6+b_*0.1 > 140 else 'white'};")
        def click():
            r, g, b_ = getter(); col = QColorDialog.getColor(QColor(r, g, b_), self)
            if col.isValid(): setter((col.red(), col.green(), col.blue())); refresh(); self.changed()
        btn.clicked.connect(click); self.binders.append(refresh); refresh(); return btn
    def palette_grid(self, lay):
        g = QGridLayout(); lay.addLayout(g)
        for i in range(10):
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.addWidget(QLabel(f"{i+1}:"))
            btn = QPushButton(); x = QPushButton(tr_i("x")); x.setMaximumWidth(28); h.addWidget(btn, 1); h.addWidget(x)
            def refresh(i=i, btn=btn, x=x):
                hx = self.cfg["palette"][i]; col = QColor(hx) if hx else None
                if col and col.isValid():
                    btn.setText(hx); btn.setStyleSheet(f"background:{hx}; color:{'black' if col.lightness() > 140 else 'white'};"); x.setVisible(True)
                else: btn.setText(tr("+ cor (aleatória)")); btn.setStyleSheet(""); x.setVisible(False)
            def pick(_=False, i=i, refresh=refresh):
                hx = self.cfg["palette"][i]; col = QColorDialog.getColor(QColor(hx) if hx else QColor("#ff6428"), self)
                if col.isValid(): self.cfg["palette"][i] = col.name(); refresh(); self.changed()
            def clear(_=False, i=i, refresh=refresh):
                self.cfg["palette"][i] = ""; refresh(); self.changed()
            btn.clicked.connect(pick); x.clicked.connect(clear); self.binders.append(refresh); refresh()
            g.addWidget(w, i // 2, i % 2)
    def set_tips(self, cb, tips):
        for i in range(cb.count()):
            tip = tips.get(cb.itemData(i))
            if tip: cb.setItemData(i, tr(tip), Qt.ItemDataRole.ToolTipRole)
        def cur(i, cb=cb):
            tip = tips.get(cb.itemData(i)); cb.setToolTip(tr(tip) if tip else "")
        cb.currentIndexChanged.connect(cur); cur(cb.currentIndex())
    def mp_fill(self):
        cb = self.mp_combo; self.mp_name = getattr(self, "mp_name", ""); self.mp_data = {}
        cb.blockSignals(True); cb.clear(); cb.addItem(tr("Personalizado"), "")
        for n, d in MUSIC_BUILTIN.items():
            cb.addItem("★ " + tr(n), "b:" + n); cb.setItemData(cb.count() - 1, tr(d["tip"]), Qt.ItemDataRole.ToolTipRole); self.mp_data["b:" + n] = d
        for n in music_presets():
            cb.addItem(n, "u:" + n); self.mp_data["u:" + n] = music_preset_read(n) or {}
        cb.blockSignals(False); self.mp_sync()
    def mp_sync(self):
        if not hasattr(self, "mp_data"): return
        def eq(k, a):
            b = self.cfg[k]
            return a == b if isinstance(b, (str, bool)) else abs(float(a) - float(b)) < 1e-6
        idx = 0
        for i in range(1, self.mp_combo.count()):
            key = self.mp_combo.itemData(i); d = self.mp_data.get(key) or {}
            if all(eq(k, d.get(k, DEFAULTS[k])) for k in MUSIC_KEYS): idx = i; self.mp_name = key.split(":", 1)[1]; break
        cb = self.mp_combo; cb.blockSignals(True)
        cb.setItemText(0, f"{self.mp_name} ({tr('modificado')})" if (idx == 0 and self.mp_name) else tr("Personalizado"))
        cb.setCurrentIndex(idx); cb.blockSignals(False)
    def mp_pick(self, i):
        key = self.mp_combo.itemData(i)
        if not key or self.block: return
        d = self.mp_data.get(key)
        if d:
            for k in MUSIC_KEYS:
                try: self.cfg[k] = type(DEFAULTS[k])(d.get(k, DEFAULTS[k]))
                except Exception: pass
            self.mp_name = key.split(":", 1)[1]
            self.sync_all(); self.changed(); self.msg(tr("Preset de música '{n}' carregado.").format(n=self.mp_name))
    def mp_save(self):
        name, ok = QInputDialog.getText(self, tr("Salvar preset de música"), tr("Nome do preset:"))
        name = clean_name(name) if ok else ""
        if not name: return
        music_preset_write(name, {k: self.cfg[k] for k in MUSIC_KEYS}); self.mp_name = name; self.mp_fill(); self.msg(tr("Preset de música '{n}' salvo.").format(n=name))
    def mp_delete(self):
        names = music_presets()
        if not names: return self.msg("Não há presets de música salvos para excluir.", True)
        name, ok = QInputDialog.getItem(self, tr("Excluir preset de música"), tr("Escolha o preset:"), names, 0, False)
        if ok and name:
            try: (music_dir() / f"{name}.json").unlink()
            except Exception: pass
            self.mp_fill(); self.msg(tr("Preset de música '{n}' excluído.").format(n=name))
    def rebuild_music_segs(self):
        if not hasattr(self, "music_seg_box"): return
        while self.music_seg_box.count():
            it = self.music_seg_box.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        def setall(v):
            for s in self.cfg["segment"]: s["music"] = v
            self.rebuild_music_segs(); self.changed()
        row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0)
        for t, v in (("Todos", True), ("Nenhum", False)):
            b = QPushButton(tr(t)); b.clicked.connect(lambda _=False, v=v: setall(v)); h.addWidget(b)
        h.addStretch(1); self.music_seg_box.addWidget(row)
        for i, s in enumerate(self.cfg["segment"]):
            cr, cg, cb_ = SEG_COLORS[i % len(SEG_COLORS)]
            edge = dict(EDGES).get(s["edge"], s["edge"])
            cbx = QCheckBox(f"{tr('Trecho')} {i + 1} · {tr('Fita')} {s['device'] + 1} · {tr(edge)} · {s['leds']} LEDs")
            cbx.setStyleSheet(f"QCheckBox {{ color: rgb({cr},{cg},{cb_}); font-weight:bold; }}")
            cbx.setChecked(bool(s.get("music", True)))
            cbx.toggled.connect(lambda v, i=i: self.seg_music(i, v)); self.music_seg_box.addWidget(cbx)
    def seg_music(self, i, v):
        if self.block: return
        self.cfg["segment"][i]["music"] = bool(v); self.changed()
    def msg(self, text, err=False):
        self.statusBar().showMessage((tr("Erro") + ": " if err else "") + tr(text), 8000)

    # ── barra superior ──
    def build_top(self):
        box = QWidget(); fl = FlowLayout(box, 6)
        t = QLabel("💡 Quiklight"); t.setObjectName("sec"); fl.addWidget(t)
        for text, fn in (("Ligar", lambda: self.svc("start", "Serviço ligado.")),
                         ("Desligar", lambda: self.svc("stop", "Serviço desligado (fita apagada).")),
                         ("Reiniciar", lambda: self.svc("restart", "Serviço reiniciado.")),
                         ("Resetar valores", lambda: self.reset_all())):
            btn = QPushButton(tr_i(text)); btn.setObjectName({"Ligar": "btnStart", "Desligar": "btnStop", "Resetar valores": "btnDanger"}.get(text, "")); btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.clicked.connect(lambda _=False, f=fn: f()); fl.addWidget(btn)
        self.rt_cb = QCheckBox(tr("Tempo real")); self.rt_cb.setObjectName("switch"); self.rt_cb.setChecked(self.realtime); self.rt_cb.toggled.connect(self.on_rt); fl.addWidget(self.rt_cb)
        ap = QPushButton(tr_i("Aplicar")); ap.setObjectName("btnPrimary"); ap.setCursor(Qt.CursorShape.PointingHandCursor); ap.clicked.connect(self.apply_now); fl.addWidget(ap)
        self.pend = QLabel(); self.pend.setStyleSheet("color:#e6aa32;"); fl.addWidget(self.pend)
        fl.addWidget(QLabel("🌐"))
        self.lang_cb = NoWheelCombo()
        for code, name in (("pt", "Português"), ("en", "English"), ("es", "Español")): self.lang_cb.addItem(name, code)
        self.lang_cb.setCurrentIndex(max(0, self.lang_cb.findData(LANG)))
        self.lang_cb.activated.connect(self.on_lang)
        fl.addWidget(self.lang_cb)
        return box
    def on_lang(self, i):
        code = self.lang_cb.itemData(i)
        if code == LANG: return
        save_lang(code)
        if IS_WIN:
            subprocess.Popen([sys.executable, "-c", "import time,subprocess,sys;time.sleep(1.2);subprocess.Popen(sys.argv[1:])",
                              sys.executable, os.path.abspath(__file__)], creationflags=0x00000008)
            self.app.quit()
        else: os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
    def on_rt(self, x):
        self.realtime = x
        save_settings(self.realtime, self.active_preset, self.theme_idx)
        self.update_pending()
        if self.realtime and self.cfg != self.applied:
            self.rt_timer.start(0)
    def svc(self, verb, ok):
        e = service_cmd(verb); self.msg(e or ok, bool(e)); self.running = is_active(); self.refresh_status()
    def refresh_status(self):
        if hasattr(self, "t_service"):
            self.t_service.set(f'<span style="color:#3cb44b">● {tr("Rodando")}</span>' if self.running else f'<span style="color:#d25050">● {tr("Parado")}</span>')
    def update_pending(self):
        self.pend.setText(tr("alterações pendentes") if (self.cfg != self.applied and not self.realtime) else "")

    # ── páginas ──
    def pg_home(self, lay):
        self.title(lay, "Home")
        g = QGridLayout(); g.setSpacing(8); g.setColumnStretch(0, 1); g.setColumnStretch(1, 1); lay.addLayout(g)
        self.t_service = InfoTile(tr("Serviço")); self.t_preset = InfoTile(tr("Preset ativo"))
        self.t_mode = InfoTile(tr("Modo")); self.t_strips = InfoTile(tr("Fitas"))
        for i, w in enumerate((self.t_service, self.t_preset, self.t_mode, self.t_strips)): g.addWidget(w, i // 2, i % 2)
        if not IS_WIN:
            self.title(lay, "Custo do aplicativo")
            g2 = QGridLayout(); g2.setSpacing(8); g2.setColumnStretch(0, 1); g2.setColumnStretch(1, 1); lay.addLayout(g2)
            self.t_cpu = InfoTile(tr("CPU (app + serviço)")); self.t_mem = InfoTile(tr("Memória"))
            self.t_gpu = InfoTile(tr("GPU do app")); self.t_gpus = InfoTile(tr("GPU total (sistema)"))
            for i, w in enumerate((self.t_cpu, self.t_mem, self.t_gpu, self.t_gpus)): g2.addWidget(w, i // 2, i % 2)
            self.cost_note = QLabel(); self.cost_note.setWordWrap(True); lay.addWidget(self.cost_note)
        self.title(lay, "Sobre")
        ab = InfoTile(tr("Versão"))
        ab.set(f"<b>Quiklight v{APP_VERSION}</b> · {APP_YEAR}<br><span style='font-size:11px'>Qt {qVersion()} · PySide6 {__import__('PySide6').__version__} · Python {sys.version.split()[0]}</span><br>{tr('Novidades')}: {tr(CHANGES)}")
        ab.val.setStyleSheet("font-size:13px; font-weight:normal;"); lay.addWidget(ab)
    def refresh_home(self):
        total = sum(s["leds"] for s in self.cfg["segment"])
        if self.active_preset:
            ok = False
            p = read_preset(self.active_preset)
            if p and p[0] == "full": ok = p[1] == self.cfg
            pre = self.active_preset + ("" if ok else " (" + tr("modificado") + ")")
        else: pre = tr("Nenhum (valores personalizados)")
        self.refresh_status()
        self.t_preset.set(pre)
        ms = dict(MUSIC_STYLES).get(self.applied["music_style"], "")
        if not self.applied["music"]: mu = tr("desligado")
        elif not is_dynamic(self.applied["mode"]): mu = tr("inativo (só age no modo Dinâmico)")
        else: mu = tr("ligado") + " · " + tr(ms)
        self.t_mode.set(f"{mode_label(self.applied['mode'])}<br><span style='font-size:12px'>🎵 {tr('Modo música')}: {mu}</span>")
        self.t_strips.set(f"{self.devices} {tr('detectada(s)')} · {total} LEDs")
        if IS_WIN: return
        m = self.metrics; dash = "—"
        self.t_cpu.set(dash if m.cpu is None else f"{m.cpu:.1f}% <span style='font-size:11px'>{tr('de 1 núcleo')}</span>")
        self.t_mem.set(dash if m.mem is None else f"{m.mem:.0f} MB")
        self.t_gpu.set(dash if m.gpu_app is None else f"{m.gpu_app:.1f}%")
        self.t_gpus.set(dash if m.gpu_total is None else f"{m.gpu_total:.0f}%")
        self.cost_note.setText(f"{tr('Processos medidos')}: {len(m.pids)} · " + tr("Só o Quiklight (janela, serviço e processos filhos). A cópia de tela feita pelo KDE não entra. \"—\" = o driver da placa não informa."))

    def pg_luz(self, lay):
        self.title(lay, "Modo de iluminação")
        r = QHBoxLayout(); lay.addLayout(r)
        self.rb = {}
        for key, text in (("dyn", "Dinâmico (captura de tela)"), ("static", "Estático"), ("effect", "Efeitos")):
            rb = QRadioButton(tr(text)); rb.toggled.connect(lambda on, k=key: on and not self.block and self.pick_kind(k)); r.addWidget(rb); self.rb[key] = rb
        self.dyn_combo = NoWheelCombo()
        for k, l in DYN: self.dyn_combo.addItem(tr(l), k)
        self.set_tips(self.dyn_combo, DYN_TIPS)
        self.dyn_combo.currentIndexChanged.connect(lambda i: (not self.block) and self.set_mode(self.dyn_combo.itemData(i)))
        lay.addWidget(self.dyn_combo)
        self.panels = {}
        def panel(name):
            w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); lay.addWidget(w); self.panels[name] = (w, l); return l
        l = panel("dominant"); self.dom_desc = QLabel(); self.dom_desc.setWordWrap(True); l.addWidget(self.dom_desc)
        g = self.sgrid(l)
        self.slider(g, 0, "Respeitar o brilho da cena", "dom_scene", 0, 1, 0.01)
        self.slider(g, 1, "Preferência por cores vibrantes", "dom_vibrance", 0, 1, 0.01)
        self.slider(g, 2, "Fidelidade da cor", "dom_fidelity", 0, 1, 0.01)
        self.slider(g, 3, "Suavidade da troca", "dom_smooth", 0.5, 0.99, 0.01)
        self.zone_box = self.slider(g, 4, "Profundidade das áreas (%)", "zone_depth", 10, 50, 1, "{:.0f}")
        l = panel("static"); row = QHBoxLayout(); row.addWidget(QLabel(tr("Cor:")))
        row.addWidget(self.color_button(lambda: (self.cfg["static_r"], self.cfg["static_g"], self.cfg["static_b"]),
                                        lambda c: self.cfg.update(static_r=c[0], static_g=c[1], static_b=c[2]))); row.addStretch(1); l.addLayout(row)
        l = panel("effect"); row = QHBoxLayout(); row.addWidget(QLabel(tr("Efeito:"))); self.fx_combo = NoWheelCombo()
        for k, t in EFFECTS: self.fx_combo.addItem(tr(t), k)
        self.set_tips(self.fx_combo, EFFECT_TIPS)
        self.fx_combo.currentIndexChanged.connect(lambda i: (not self.block) and (self.cfg.update(effect=self.fx_combo.itemData(i)), self.changed()))
        row.addWidget(self.fx_combo, 1); l.addLayout(row)
        g = self.sgrid(l); self.slider(g, 0, "Velocidade", "effect_speed", 1, 10, 0.1, "{:.1f}"); self.slider(g, 1, "Brilho mínimo %", "effect_min", 0, 90, 1, "{:.0f}")
        l.addWidget(QLabel(tr("Paleta (até 10 cores). Rainbow e Fogo usam cores próprias."))); self.palette_grid(l)
        self.check(l, "Completar slots vazios com cores aleatórias", "palette_random")
        l = panel("palette"); l.addWidget(QLabel(tr("Toda cor da tela vira a cor selecionada mais próxima; o brilho segue a tela. Com uma só cor, tudo aparece nela.")))
        self.palette_grid(l)
        for name in ("palette", "screen"):
            l = panel("fade_" + name) if name == "palette" else panel("screen")
            if name == "screen": l.addWidget(QLabel(tr("A fita acompanha as bordas da tela. Ajustes em Cores e Captura.")))
            g = self.sgrid(l); self.slider(g, 0, "Suavização entre cores (0 = instantâneo)", "fade_time", 0, 3, 0.05)
        self.title(lay, "Detecção de barras pretas")
        self.check(lay, "Detectar barras pretas automaticamente (recorta a área para onde há imagem)", "auto_crop")
        g = self.sgrid(lay); self.slider(g, 0, "Velocidade de detecção das barras pretas (1 = lenta, 10 = rápida)", "crop_speed", 1, 10, 0.5, "{:.1f}")
        self.title(lay, "Brilho e proteção")
        g = self.sgrid(lay)
        self.slider(g, 0, "Brilho (%)", "level", 10, 150, 1, "{:.0f}"); self.slider(g, 1, "Limite de potência (%)", "power_limit", 20, 100, 1, "{:.0f}")
        self.slider(g, 2, "Limite de variação (0 = desligado)", "slew", 0, 20, 0.5, "{:.1f}")
        lay.addWidget(QLabel(tr("Brilho acima de 100% realça sem mudar o tom. Limite de potência 100 = sem limite.")))

    def pg_musica(self, lay):
        self.title(lay, "Modo música")
        self.music_warn = QLabel(tr("Atenção: o Modo música só age no modo Dinâmico (aba Iluminação e cores).")); self.music_warn.setWordWrap(True); self.music_warn.setObjectName("card"); lay.addWidget(self.music_warn)
        self.music_box = QWidget(); ml = QVBoxLayout(self.music_box); ml.setContentsMargins(0, 4, 0, 4); lay.addWidget(self.music_box)
        self.check(ml, "Modo música (pulsa na batida do som do PC)", "music")
        self.title(ml, "Presets do modo música")
        pr = QHBoxLayout(); self.mp_combo = NoWheelCombo(); pr.addWidget(self.mp_combo, 1)
        for text, fn in (("Salvar preset de música", self.mp_save), ("Excluir preset de música", self.mp_delete)):
            bt = QPushButton(tr_i(text)); bt.setCursor(Qt.CursorShape.PointingHandCursor); bt.clicked.connect(lambda _=False, f=fn: f()); pr.addWidget(bt)
        ml.addLayout(pr); self.mp_fill(); self.mp_combo.currentIndexChanged.connect(self.mp_pick)
        self.title(ml, "Estilo e ajustes")
        mr = QHBoxLayout(); mr.addWidget(QLabel(tr("Estilo:"))); self.music_combo = NoWheelCombo()
        for k, t in MUSIC_STYLES: self.music_combo.addItem(tr(t), k)
        self.set_tips(self.music_combo, STYLE_TIPS)
        self.music_combo.currentIndexChanged.connect(lambda i: (not self.block) and (self.cfg.update(music_style=self.music_combo.itemData(i)), self.sync_music_ui(), self.changed()))
        mr.addWidget(self.music_combo, 1); ml.addLayout(mr)
        self.band_row = QWidget(); br = QHBoxLayout(self.band_row); br.setContentsMargins(0, 0, 0, 0); br.addWidget(QLabel(tr("Reagir a:"))); self.band_combo = NoWheelCombo()
        for k, t in MUSIC_BANDS: self.band_combo.addItem(tr(t), k)
        self.set_tips(self.band_combo, BAND_TIPS)
        self.band_combo.currentIndexChanged.connect(lambda i: (not self.block) and (self.cfg.update(music_band=self.band_combo.itemData(i)), self.changed()))
        br.addWidget(self.band_combo, 1); ml.addWidget(self.band_row)
        self.rev_hint = QLabel(tr("REV sound (jogos de corrida): acompanha o giro do motor pelo som. O brilho sobe com o RPM, avermelha perto do limite e dá um clarão na troca de marcha. Experimental: funciona melhor com a música do jogo baixa. A barra Reação da luz mostra o RPM.")); self.rev_hint.setWordWrap(True); self.rev_hint.setObjectName("card"); ml.addWidget(self.rev_hint)
        mg = self.sgrid(ml); self.slider(mg, 0, "Mínimo (%) - menor = efeito mais forte", "music_min", 0, 90, 1, "{:.0f}")
        self.slider(mg, 1, "Sensibilidade à batida", "music_sens", 0.3, 3, 0.05)
        mh = QLabel(tr("Escolha o estilo. Quanto menor o mínimo, mais forte o efeito. Aumente a sensibilidade se a luz quase não reage.")); mh.setWordWrap(True); ml.addWidget(mh)
        self.music_meter = MusicMeter(self); ml.addWidget(self.music_meter)
        mh2 = QLabel(tr("Passe o mouse sobre cada barra para ver o que ela faz. Use o interruptor à esquerda para ligar ou desligar uma faixa.")); mh2.setWordWrap(True); ml.addWidget(mh2)
        self.music_info = QLabel(""); self.music_info.setWordWrap(True); ml.addWidget(self.music_info)
        self.title(ml, "Fitas que reagem ao som")
        ml.addWidget(QLabel(tr("Marque os trechos que reagem ao som. Os desmarcados ficam com a iluminação normal.")))
        self.music_seg_box = QVBoxLayout(); ml.addLayout(self.music_seg_box); self.rebuild_music_segs()

    def pg_luz_cores(self, lay):
        self.pg_luz(lay)
        self.pg_cores(lay)

    def pick_kind(self, k):
        self.set_mode(self.last_dyn if k == "dyn" else k)
    def set_mode(self, m):
        self.cfg["mode"] = m
        if is_dynamic(m): self.last_dyn = m
        self.sync_mode_ui(); self.changed()
    def sync_mode_ui(self):
        m = self.cfg["mode"]; self.block += 1
        kind = "static" if m == "static" else "effect" if m == "effect" else "dyn"
        for k, rb in self.rb.items(): rb.setChecked(k == kind)
        self.dyn_combo.setVisible(kind == "dyn"); self.music_warn.setVisible(kind != "dyn")
        i = self.dyn_combo.findData(self.last_dyn if kind != "dyn" else m)
        if i >= 0: self.dyn_combo.setCurrentIndex(i)
        bj = self.band_combo.findData(self.cfg["music_band"])
        if bj >= 0: self.band_combo.setCurrentIndex(bj)
        mj = self.music_combo.findData(self.cfg["music_style"])
        if mj >= 0: self.music_combo.setCurrentIndex(mj)
        j = self.fx_combo.findData(self.cfg["effect"])
        if j >= 0: self.fx_combo.setCurrentIndex(j)
        self.block -= 1; self.sync_music_ui()
        show = {"dominant": m in ("dominant", "dominant_lr", "dominant_4"), "static": m == "static", "effect": m == "effect",
                "palette": m == "palette", "fade_palette": m == "palette", "screen": m == "screen"}
        for name, (w, _) in self.panels.items(): w.setVisible(show.get(name, False))
        self.zone_box.setVisible(m == "dominant_4")
        self.dom_desc.setText({"dominant_lr": "Duas cores: metade esquerda da tela no lado esquerdo da fita e metade direita no lado direito.",
                               "dominant_4": "Quatro cores: esquerda, direita, topo e baixo da tela, cada uma no seu lado da fita."}.get(
                               m, "Uma só cor para toda a fita: a cor mais marcante da área capturada."))

    def sync_music_ui(self):
        st = self.cfg["music_style"]
        self.band_row.setVisible(st not in ("split", "vol", "vu", "rev", "quad", "breath", "heat")); self.rev_hint.setVisible(st == "rev")
    def update_music(self):
        if not self.music_meter.isVisible(): return
        d = self.runtime_dir()
        if int(time.time() * 10) % 10 == 0:
            try: (d / "quiklight-audio.want").touch()
            except Exception: pass
        if not self.applied.get("music") or is_dynamic(self.applied["mode"]) is False:
            self.music_meter.v = [0.0] * 5; self.music_meter.update()
            self.music_info.setText(tr("Marque Modo música e clique em Aplicar (ou ligue Tempo real) para ver o medidor.")); return
        vals = None
        try:
            f = d / "quiklight-audio.txt"
            if time.time() - f.stat().st_mtime < 2: vals = [float(x) for x in f.read_text().split()[:5]]
        except Exception: pass
        if not vals or len(vals) < 5:
            self.music_meter.v = [0.0] * 5; self.music_meter.update()
            self.music_info.setText(tr("Sem dados de áudio: o serviço está parado ou ainda não captou som. Toque uma música."))
            return
        self.music_meter.v = vals; self.music_meter.update()
        self.music_info.setText(tr("Barras azuis: o que o som tem agora. Em cada barra, arraste as alças amarelas: abaixo da mínima é ignorado, acima da máxima conta como 100% (duplo clique restaura). A barra de reação mostra o que move a luz; passou da linha = batida."))

    def pg_cores(self, lay):
        self.title(lay, "Cores (modos dinâmicos)")
        row = QHBoxLayout(); row.addWidget(QLabel(tr("Tema de cores:"))); cb = NoWheelCombo(); cb.addItem(tr("escolher um tema..."))
        for t in THEMES: cb.addItem(tr(t[0]))
        def pick(i):
            if i > 0 and not self.block:
                apply_color_theme(self.cfg, THEMES[i - 1]); self.sync_all(); self.changed(); self.msg(tr("Tema '{n}' carregado.").format(n=tr(THEMES[i-1][0])))
                self.block += 1; cb.setCurrentIndex(0); self.block -= 1
        cb.currentIndexChanged.connect(pick); row.addWidget(cb); row.addStretch(1); lay.addLayout(row)
        g = self.sgrid(lay)
        self.slider(g, 0, "Saturação", "saturation", 0.5, 3, 0.05); self.slider(g, 1, "Contraste", "contrast", 0.7, 1.6, 0.01)
        self.slider(g, 2, "Gamma", "gamma", 0.6, 2.4, 0.05); self.slider(g, 3, "Quadros por segundo", "fps", 5, 120, 1, "{:.0f}")
        vv = QCheckBox(tr("Modo vívido"))
        def vr(): self.block += 1; vv.setChecked(self.cfg["color_mode"] == "vivid"); self.block -= 1
        def vt(x):
            if not self.block: self.cfg["color_mode"] = "vivid" if x else "average"; self.changed()
        vv.toggled.connect(vt); self.binders.append(vr); vr(); lay.addWidget(vv)
        self.check(lay, "Limitar a captura ao fps", "capture_limit")
        self.title(lay, "Acurácia de cores")
        self.check(lay, "Melhor acurácia de cores (balanço de branco, gamma por canal e proteção de neutros)", "accuracy")
        adaptive_toggle = self.check(lay, "Ativar fidelidade adaptativa (experimental)", "adaptive_fidelity_enabled")
        adaptive_slider = self.slider(self.sgrid(lay), 0, "Intensidade da fidelidade adaptativa (%)", "adaptive_fidelity", 0, 100, 5, "{:.0f}")
        adaptive_slider.setEnabled(bool(self.cfg["adaptive_fidelity_enabled"]))
        adaptive_toggle.toggled.connect(adaptive_slider.setEnabled)
        info = QLabel(tr("Desativado = processamento original. Ative e ajuste a intensidade (0-100%). A calibração RGB é preservada."))
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addWidget(QLabel(tr("Balanço de branco: se o branco estiver azulado, reduza Azul e Verde.")))
        g = self.sgrid(lay)
        for i, (k, t) in enumerate((("gain_r", "Vermelho"), ("gain_g", "Verde"), ("gain_b", "Azul"))): self.slider(g, i, t, k, 0.2, 1.5, 0.01)
        lay.addWidget(QLabel(tr("Gamma por canal (ajuste fino)"))); g = self.sgrid(lay)
        for i, (k, t) in enumerate((("gamma_r", "Vermelho"), ("gamma_g", "Verde"), ("gamma_b", "Azul"))): self.slider(g, i, t, k, 0.6, 1.6, 0.01)

    def pg_captura(self, lay):
        self.title(lay, "Área de captura da tela")
        if not IS_WIN:
            rs = QPushButton(tr_i("Escolher outra tela")); rs.clicked.connect(self.reset_screen); lay.addWidget(rs)
        lay.addWidget(self.preview, 1)
        row = QHBoxLayout(); lt = QCheckBox(tr("Ao vivo")); lt.setChecked(self.live_on); lt.toggled.connect(self.on_live_toggle); row.addWidget(lt)
        self.live_info = QLabel(); row.addWidget(self.live_info, 1); lay.addLayout(row)
        row = QHBoxLayout()
        for t, v in (("Borda", 0.0), ("Um pouco para dentro", 10.0), ("Centro", 25.0)):
            bt = QPushButton(tr_i(t)); bt.clicked.connect(lambda _=False, v=v: self.set_insets(v)); row.addWidget(bt)
        row.addStretch(1); lay.addLayout(row)
        g = self.sgrid(lay)
        for i, (k, t) in enumerate((("inset_left", "Margem esquerda (%)"), ("inset_top", "Margem do topo (%)"),
                                    ("inset_right", "Margem direita (%)"), ("inset_bottom", "Margem de baixo (%)"))):
            self.slider(g, i, t, k, 0, 45, 0.5, "{:.1f}")
        self.slider(g, 4, "Espessura da faixa", "border", 1, 20, 1, "{:.0f}")
        row = QHBoxLayout(); row.addWidget(QLabel(tr("Resolução:")))
        for k, lo, hi in (("cap_w", 16, 640), ("cap_h", 9, 360)):
            sb = NoWheelSpin(); sb.setRange(lo, hi)
            def refresh(sb=sb, k=k): self.block += 1; sb.setValue(self.cfg[k]); self.block -= 1
            sb.valueChanged.connect(lambda v, k=k: (not self.block) and (self.cfg.__setitem__(k, v), self.changed()))
            self.binders.append(refresh); refresh(); row.addWidget(sb)
        row.addStretch(1); lay.addLayout(row)
    def set_insets(self, v):
        for k in ("inset_left", "inset_top", "inset_right", "inset_bottom"): self.cfg[k] = v
        self.sync_all(); self.changed()
    def reset_screen(self):
        try: (data_dir() / "restore_token").unlink()
        except Exception: pass
        e = service_cmd("restart"); self.msg(e or "Escolha a tela da fita na janela do KDE.", bool(e))

    def pg_leds(self, lay):
        self.title(lay, "LEDs e fitas")
        self.title(lay, "Monitor capturado")
        row = QHBoxLayout(); self.mon_cb = NoWheelCombo()
        for i, sc in enumerate(QGuiApplication.screens()):
            g = sc.geometry(); self.mon_cb.addItem(f"{i+1}: {sc.name()} — {g.width()}x{g.height()}", i)
        row.addWidget(self.mon_cb, 1)
        def mon_refresh():
            m = str(self.cfg.get("monitor") or "0"); idx = int(m) if m.isdigit() else 0
            self.block += 1; self.mon_cb.setCurrentIndex(min(idx, max(0, self.mon_cb.count() - 1))); self.block -= 1
        def mon_changed(ix):
            if self.block or ix < 0: return
            self.cfg["monitor"] = str(self.mon_cb.itemData(ix)); self.changed()
        self.mon_cb.currentIndexChanged.connect(mon_changed); self.binders.append(mon_refresh); mon_refresh()
        if not IS_WIN:
            bt = QPushButton(tr_i("Escolher monitor no KDE")); bt.clicked.connect(lambda _=False: self.reset_screen()); row.addWidget(bt)
        lay.addLayout(row)
        if not IS_WIN: lay.addWidget(QLabel(tr("No Linux (KDE) o monitor final é escolhido na janela de compartilhamento do KDE (botão ao lado).")))
        row = QHBoxLayout(); row.addWidget(QLabel(tr("Layouts prontos:")))
        for t, full in (("Esquerda + topo + direita", False), ("Moldura completa (com embaixo)", True)):
            bt = QPushButton(tr_i(t)); bt.clicked.connect(lambda _=False, f=full: self.layout_preset(f)); row.addWidget(bt)
        row.addStretch(1); lay.addLayout(row)
        lay.addWidget(QLabel(tr("Cada trecho é uma parte da fita, na ordem em que os LEDs estão ligados. Inverter troca o sentido.")))
        self.seg_box = QVBoxLayout(); lay.addLayout(self.seg_box)
        row = QHBoxLayout()
        for t, d in (("Adicionar trecho", 0), ("Adicionar trecho em outra fita (Fita 2)", 1)):
            bt = QPushButton(tr_i(t)); bt.clicked.connect(lambda _=False, d=d: self.seg_add(d)); row.addWidget(bt)
        row.addStretch(1); lay.addLayout(row)
        self.seg_sum = QLabel(); lay.addWidget(self.seg_sum)
    def layout_preset(self, full):
        S = lambda e, n, r=False: dict(device=0, edge=e, leds=n, reverse=r, music=True)
        self.cfg["segment"] = [S("left", 17), S("top", 29), S("right", 17)] + ([S("bottom", 29, True)] if full else [])
        self.rebuild_segments(); self.changed()
    def seg_add(self, d):
        self.cfg["segment"].append(dict(device=d, edge="bottom", leds=29, reverse=False, music=True)); self.rebuild_segments(); self.changed()
    def seg_set(self, i, k, v):
        if self.block: return
        self.cfg["segment"][i][k] = v; self.update_seg_sum(); self.changed()
    def seg_move(self, i, d):
        s = self.cfg["segment"]; j = i + d
        if 0 <= j < len(s): s[i], s[j] = s[j], s[i]; self.rebuild_segments(); self.changed()
    def seg_remove(self, i):
        self.cfg["segment"].pop(i); self.rebuild_segments(); self.changed()
    def rebuild_segments(self):
        while self.seg_box.count():
            it = self.seg_box.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self.block += 1
        for i, s in enumerate(self.cfg["segment"]):
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(4); cr, cg, cb = SEG_COLORS[i % len(SEG_COLORS)]
            lab = QLabel(tr("Trecho") + f" {i+1}"); lab.setStyleSheet(f"color: rgb({cr},{cg},{cb}); font-weight:bold;"); h.addWidget(lab)
            dev = NoWheelSpin(); dev.setRange(1, 8); dev.setPrefix(tr("Fita") + " "); dev.setValue(s["device"] + 1)
            dev.valueChanged.connect(lambda v, i=i: self.seg_set(i, "device", v - 1)); h.addWidget(dev)
            ed = NoWheelCombo()
            for k, l in EDGES: ed.addItem(tr(l), k)
            ed.setCurrentIndex(max(0, ed.findData(s["edge"])))
            ed.currentIndexChanged.connect(lambda ix, i=i, ed=ed: self.seg_set(i, "edge", ed.itemData(ix))); h.addWidget(ed)
            lk = NoWheelSpin(); lk.setRange(0, 300); lk.setSuffix(" LEDs"); lk.setValue(s["leds"])
            lk.valueChanged.connect(lambda v, i=i: self.seg_set(i, "leds", v)); h.addWidget(lk)
            inv = QCheckBox(tr("Inverter")); inv.setChecked(s["reverse"]); inv.toggled.connect(lambda v, i=i: self.seg_set(i, "reverse", bool(v))); h.addWidget(inv)
            for t, fn in (("▲", lambda i=i: self.seg_move(i, -1)), ("▼", lambda i=i: self.seg_move(i, 1)), ("✖", lambda i=i: self.seg_remove(i))):
                bt = QPushButton(t); bt.setMaximumWidth(34); bt.clicked.connect(lambda _=False, fn=fn: fn()); h.addWidget(bt)
            h.addStretch(1); self.seg_box.addWidget(w)
        self.block -= 1; self.update_seg_sum(); self.rebuild_music_segs()
    def update_seg_sum(self):
        mx = max([s["device"] + 1 for s in self.cfg["segment"]] or [1]); tot = [0] * mx
        for s in self.cfg["segment"]: tot[s["device"]] += s["leds"]
        t = "  ·  ".join(f"{tr('Fita')} {i+1}: {n} LEDs" for i, n in enumerate(tot))
        if mx > self.devices: t += "\n" + tr("Atenção: a configuração usa {a} fita(s), mas só {b} foi/foram detectada(s).").format(a=mx, b=self.devices)
        self.seg_sum.setText(t)

    def runtime_dir(self):
        return Path(os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TEMP") or "/tmp")
    def on_tab(self, i):
        if i < 0: return
        self.stack.setCurrentIndex(i)
        self.set_live(self.live_on and TABS[i][1] == "Captura")
        if TABS[i][1] == "Hardware": self.refresh_hw()
        if TABS[i][1] == "Sistema": self.refresh_autostart()
    def set_live(self, active):
        want = self.runtime_dir() / "quiklight-live.want"
        if active:
            try: want.touch()
            except Exception: pass
            self.live_timer.start(100)
        else:
            self.live_timer.stop()
            try: want.unlink()
            except Exception: pass
            self.live_data = b""; self.preview.update(); self.live_info.setText("")
    def on_live_toggle(self, on):
        self.live_on = on
        self.set_live(on and TABS[self.stack.currentIndex()][1] == "Captura")
    def update_live(self):
        d = self.runtime_dir()
        if int(time.time() * 10) % 10 == 0:
            try: (d / "quiklight-live.want").touch()
            except Exception: pass
        data = b""
        try:
            f = d / "quiklight-live.bin"
            if time.time() - f.stat().st_mtime < 2: data = f.read_bytes()
        except Exception: pass
        self.live_data = data; self.preview.update()
        n = len(data) // 3
        if not n:
            self.live_info.setText(tr("Sem dados: o serviço está parado ou a fita não está recebendo quadros."))
            return
        on = sum(1 for i in range(n) if data[i*3] or data[i*3+1] or data[i*3+2])
        ma = sum(data) / 255 * 20
        self.live_info.setText(f"{tr('LEDs acesos')}: {on}/{n} · {tr('Consumo estimado')}: ~{ma:.0f} mA")

    # ── hardware ──
    def pg_hw(self, lay):
        self.title(lay, "Hardware da fita")
        self.hw_text = QPlainTextEdit(); self.hw_text.setReadOnly(True); self.hw_text.setMinimumHeight(300); lay.addWidget(self.hw_text, 1)
        bt = QPushButton(tr_i("Atualizar")); bt.clicked.connect(lambda _=False: self.refresh_hw()); lay.addWidget(bt)
    def refresh_hw(self):
        def rd(p, n):
            try: return (p / n).read_text().strip()
            except Exception: return "—"
        found = []
        for d in Path("/sys/bus/usb/devices").glob("*"):
            if rd(d, "idVendor").lower() == "1a86" and rd(d, "idProduct").lower() == "fe07": found.append(d)
        L = []
        if IS_WIN: L.append(tr("Detalhes USB: disponíveis apenas no Linux."))
        elif not found: L.append(tr("Nenhuma fita Quiklight USB encontrada."))
        for k, d in enumerate(found):
            L.append(f"── {tr('Fita')} {k+1} ({d.name}) ──")
            L.append(f"{tr('Fabricante')}: {rd(d, 'manufacturer')}")
            L.append(f"{tr('Produto')}: {rd(d, 'product')}")
            L.append(f"ID USB: {rd(d, 'idVendor')}:{rd(d, 'idProduct')}")
            L.append(f"{tr('Versão do USB')}: {rd(d, 'version')} · {tr('Velocidade')}: {rd(d, 'speed')} Mb/s")
            L.append(f"{tr('Corrente máxima declarada')}: {rd(d, 'bMaxPower')}")
            L.append(f"{tr('Gerenciamento de energia')}: {rd(d / 'power', 'control')} · {tr('Estado')}: {rd(d / 'power', 'runtime_status')}")
            hid = sorted(Path("/sys/class/hidraw").glob("hidraw*"))
            nodes = [h.name for h in hid if "1A86" in rd(h / "device", "uevent").upper() and "FE07" in rd(h / "device", "uevent").upper()]
            L.append(f"{tr('Nós HID')}: {', '.join('/dev/' + n for n in nodes) or '—'}")
            L.append("")
        per = {}
        for sg in self.cfg["segment"]: per[sg["device"]] = per.get(sg["device"], 0) + sg["leds"]
        total = sum(per.values())
        L.append(f"── {tr('LEDs')} ──")
        for dv in sorted(per): L.append(f"{tr('Fita')} {dv+1}: {per[dv]} LEDs ({tr('configurados')})")
        L.append(f"{tr('Total configurado')}: {total} LEDs")
        L.append(tr("O controlador não informa a quantidade real de LEDs; confira pelo teste ao vivo."))
        L.append(f"{tr('Consumo máximo teórico')}: ~{total * 60} mA ({tr('todos em branco total')})")
        L.append(tr("Referência: USB 2.0 entrega 500 mA e USB 3.x entrega 900 mA por porta."))
        self.hw_text.setPlainText("\n".join(L))

    def pg_presets(self, lay):
        self.title(lay, "Presets")
        row = QHBoxLayout(); self.pcombo = NoWheelCombo(); self.pcombo.setMinimumWidth(240)
        self.pcombo.activated.connect(self.load_preset); row.addWidget(self.pcombo)
        d = QPushButton(tr_i("Excluir")); d.clicked.connect(self.del_preset); row.addWidget(d); row.addStretch(1); lay.addLayout(row)
        row = QHBoxLayout(); self.pname = QLineEdit(); self.pname.setPlaceholderText(tr("Nome do novo preset")); row.addWidget(self.pname, 1)
        s = QPushButton(tr_i("Salvar preset")); s.clicked.connect(self.save_preset); row.addWidget(s); lay.addLayout(row)
        lay.addWidget(QLabel(tr("O preset guarda tudo: modo, cores, captura, área, resolução e LEDs/fitas. Depois de carregar, clique em Aplicar.")))
        self.refresh_presets()
    def refresh_presets(self):
        self.pcombo.clear(); self.pcombo.addItem(tr("(escolha um preset)"))
        for n in list_presets(): self.pcombo.addItem(n)
        if self.active_preset in list_presets(): self.pcombo.setCurrentText(self.active_preset)
    def load_preset(self, i):
        if i <= 0: return
        name = self.pcombo.itemText(i); p = read_preset(name)
        if not p: return self.msg(tr("Não consegui ler o preset '{n}'.").format(n=name), True)
        apply_preset_data(self.cfg, p); normalize(self.cfg); self.active_preset = name
        save_settings(self.realtime, self.active_preset, self.theme_idx); self.sync_all(); self.changed()
        self.msg("Preset carregado. Clique em Aplicar para usar.")
    def save_preset(self):
        name = clean_name(self.pname.text()) or (self.pcombo.currentText() if self.pcombo.currentIndex() > 0 else "")
        if not name: return self.msg("Digite um nome para o preset.", True)
        write_preset(name, self.cfg); self.active_preset = name; self.pname.clear()
        save_settings(self.realtime, self.active_preset, self.theme_idx); self.refresh_presets(); self.msg(tr("Preset '{n}' salvo.").format(n=name))
    def del_preset(self):
        if self.pcombo.currentIndex() <= 0: return
        n = self.pcombo.currentText()
        if QMessageBox.question(self, tr("Excluir preset"), tr("Excluir") + f" '{n}'?") == QMessageBox.StandardButton.Yes:
            try: preset_path(n).unlink()
            except Exception: pass
            self.refresh_presets(); self.msg(tr("Preset '{n}' excluído.").format(n=n))

    def refresh_autostart(self):
        if not hasattr(self, "autostart_cb"):
            return
        self.autostart_cb.blockSignals(True)
        self.autostart_cb.setChecked(autostart_enabled())
        self.autostart_cb.blockSignals(False)

    def on_autostart_toggle(self, enabled):
        try:
            set_autostart(bool(enabled))
            self.refresh_autostart()
            self.msg("Inicialização automática ativada para o próximo login."
                     if enabled else "Inicialização automática desativada.")
        except Exception as error:
            self.refresh_autostart()
            QMessageBox.warning(self, "Quiklight", str(error))

    def pg_sistema(self, lay):
        self.title(lay, "Sistema")
        self.autostart_cb = QCheckBox(tr("Iniciar automaticamente com o sistema (minimizado na bandeja)"))
        self.autostart_cb.setObjectName("switch")
        self.autostart_cb.setToolTip(tr(
            "Inicia depois de entrar na conta Windows." if IS_WIN else
            "Inicia a interface na bandeja e o serviço de LEDs ao entrar no KDE."
        ))
        self.refresh_autostart()
        self.autostart_cb.toggled.connect(self.on_autostart_toggle)
        lay.addWidget(self.autostart_cb)
        row = QHBoxLayout(); row.addWidget(QLabel(tr("Tema da janela:"))); tc = NoWheelCombo()
        for t in WTHEMES: tc.addItem(tr(t[0]))
        tc.setCurrentIndex(self.theme_idx)
        tc.currentIndexChanged.connect(lambda i: (setattr(self, "theme_idx", i), save_settings(self.realtime, self.active_preset, i), self.apply_theme()))
        row.addWidget(tc); row.addStretch(1); lay.addLayout(row)
        self.title(lay, "Relatório e backup"); row = QHBoxLayout()
        for t, fn in (("Copiar relatório para suporte", self.copy_report), ("Exportar backup (pasta Downloads)", self.export_backup)):
            bt = QPushButton(tr_i(t)); bt.clicked.connect(lambda _=False, f=fn: f()); row.addWidget(bt)
        row.addStretch(1); lay.addLayout(row)
        lay.addWidget(QLabel(tr("Importar: escolha um backup encontrado em Downloads ou cole o texto abaixo.")))
        self.bk_box = QVBoxLayout(); lay.addLayout(self.bk_box); self.refresh_backups()
        self.paste = QPlainTextEdit(); self.paste.setPlaceholderText(tr("Cole aqui o backup (Ctrl+V)")); self.paste.setMaximumHeight(90); lay.addWidget(self.paste)
        ib = QPushButton(tr_i("Importar texto colado")); ib.clicked.connect(lambda: self.do_import(self.paste.toPlainText())); lay.addWidget(ib)
        self.title(lay, "Versões e rollback")
        self.ver_info = QLabel(); self.ver_info.setWordWrap(True); lay.addWidget(self.ver_info)
        self.ver_box = QVBoxLayout(); lay.addLayout(self.ver_box); self.refresh_versions()
        self.title(lay, "Registro do programa")
        rb = QPushButton(tr_i("Atualizar registro")); lay.addWidget(rb)
        self.logv = QPlainTextEdit(); self.logv.setReadOnly(True); self.logv.setMinimumHeight(160); lay.addWidget(self.logv)
        rb.clicked.connect(lambda: self.logv.setPlainText(journal(40)))
    def refresh_versions(self):
        while self.ver_box.count():
            it = self.ver_box.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        vs = list_versions()
        self.ver_info.setText(f"{tr('Versão atual')}: v{APP_VERSION}. " + (tr("Versões anteriores guardadas (até 10):") if vs else
                              tr("Ainda não há versões anteriores guardadas. Elas aparecem aqui depois da próxima atualização.")))
        for name, ver, ts in vs:
            w = QWidget(); row = QHBoxLayout(w); row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(QLabel(f"v{ver} · {time.strftime('%d/%m/%Y %H:%M', time.localtime(ts))}"), 1)
            bt = QPushButton(tr("Restaurar esta versão")); bt.setCursor(Qt.CursorShape.PointingHandCursor)
            bt.clicked.connect(lambda _=False, n=name, v=ver: self.do_rollback(n, v)); row.addWidget(bt)
            self.ver_box.addWidget(w)
    def do_rollback(self, name, ver):
        if QMessageBox.question(self, tr("Restaurar versão"), tr("Voltar para a versão") + f" v{ver}? " + tr("O programa vai reiniciar. Suas configurações e presets são mantidos.")) != QMessageBox.StandardButton.Yes: return
        err = restore_version(name)
        if err: self.msg(err, True); self.refresh_versions(); return
        relaunch_gui(); QTimer.singleShot(200, lambda: os._exit(0))
    def refresh_backups(self):
        while self.bk_box.count():
            it = self.bk_box.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        for p in list_backups()[:5]:
            bt = QPushButton(tr_i("Importar") + f" {p.name}"); bt.clicked.connect(lambda _=False, p=p: self.do_import(p.read_text())); self.bk_box.addWidget(bt)
    def report(self):
        t = ("=== Quiklight (Qt) — relatório ===\n"
             f"Serviço: {'rodando' if self.running else 'parado'}\nFitas USB detectadas: {self.devices}\n"
             f"Modo: {mode_label(self.applied['mode'])}\nPreset ativo: {self.active_preset or 'nenhum'}\n"
             f"Tempo real: {'ligado' if self.realtime else 'desligado'}\n\n--- config.toml (aplicada) ---\n")
        try: t += config_path().read_text()
        except Exception: pass
        return t + "\n--- registro (últimas linhas) ---\n" + journal(40)
    def copy_report(self):
        QApplication.clipboard().setText(self.report()); self.msg("Relatório copiado. Cole na conversa (Ctrl+V).")
    def export_backup(self):
        p = downloads_dir() / f"quiklight-backup-{int(time.time())}.toml"
        try: p.write_text(backup_text()); self.msg(tr("Backup salvo em {p}").format(p=p))
        except Exception as e: self.msg(str(e), True)
        self.refresh_backups()
    def do_import(self, text):
        n, err = import_backup(text)
        if err: return self.msg(err, True)
        self.cfg = read_config(); self.applied = copy.deepcopy(self.cfg); self.sync_all(); self.refresh_presets()
        e = service_cmd("restart"); self.msg(e or tr("Importado: {n} item(ns).").format(n=n), bool(e))

    # ── ações gerais ──
    def reset_all(self):
        if QMessageBox.question(self, tr("Resetar valores"), tr("Voltar todos os valores ao padrão? (LEDs e fitas são mantidos)")) != QMessageBox.StandardButton.Yes: return
        segs = self.cfg["segment"]; self.cfg.clear(); self.cfg.update(cfg_from_dict({})); self.cfg["segment"] = segs
        self.active_preset = None; save_settings(self.realtime, None, self.theme_idx); self.sync_all(); self.changed()
        self.msg("Valores padrão carregados (LEDs e fitas mantidos). Clique em Aplicar.")
    def apply_now(self):
        st = is_structural(self.applied, self.cfg); was = is_active()
        try: write_config(self.cfg); err = service_cmd("restart") if (st or not was) else None
        except Exception as e: err = str(e)
        if not err: self.applied = copy.deepcopy(self.cfg)
        self.msg(err or "Aplicado.", bool(err)); self.running = is_active(); self.refresh_status(); self.update_pending()
    def changed(self):
        self.preview.update(); self.update_pending(); self.update_seg_sum(); self.mp_sync()
        if self.realtime and self.cfg != self.applied: self.rt_timer.start(200)
    def sync_all(self):
        self.block += 1
        for f in self.binders: f()
        self.block -= 1
        self.rebuild_segments(); self.sync_mode_ui(); self.preview.update(); self.update_pending(); self.refresh_status(); self.mp_sync()
    def on_poll(self):
        self.running = is_active(); self.devices = count_devices(); self.refresh_status()
        if self.isVisible():
            if self.stack.currentIndex() == 0: self.metrics.sample(); self.refresh_home()
            else: self.metrics.reset()

    # ── aparência / janela ──
    def fill_side(self, narrow):
        row = self.side.currentRow(); self.side.blockSignals(True); self.side.clear()
        for ic, lb in TABS:
            icon = rainbow_bulb_icon() if lb == "Iluminação e cores" else music_icon() if lb == "Música" else QIcon.fromTheme(TAB_ICONS.get(lb, ""))
            if icon.isNull(): it = QListWidgetItem(ic if narrow else f"{ic}  {tr(lb)}")
            else: it = QListWidgetItem(icon, "" if narrow else tr(lb))
            it.setToolTip(tr(lb)); self.side.addItem(it)
        self.side.setCurrentRow(max(row, 0)); self.side.blockSignals(False)
        self._narrow = narrow; self.fit_side()
    def fit_side(self):
        n = self.side.count()
        if not n: return
        narrow = getattr(self, "_narrow", False)
        w = 62 if narrow else max(150, min(190, int(self.width() * 0.18)))
        if self.side.width() != w: self.side.setFixedWidth(w)
        h = int(max(28, min(44, (self.height() - 130) / n)))
        for i in range(n): self.side.item(i).setSizeHint(QSize(w - 12, h))
        f = self.side.font(); f.setPixelSize(13 if h < 36 else 15); self.side.setFont(f)
        s = max(16, min(24, h - 14)); self.side.setIconSize(QSize(s, s))
    def relayout(self):
        cols = 1 if self.stack.width() < 560 else 2
        for grid, boxes in self.grid_reg.values():
            for w in boxes: grid.removeWidget(w)
            for k, w in enumerate(boxes): grid.addWidget(w, k // cols, k % cols)
    def resizeEvent(self, e):
        super().resizeEvent(e); n = self.width() < 800
        if hasattr(self, "_narrow") and n != self._narrow: self.fill_side(n)
        if hasattr(self, "_narrow"): self.fit_side()
        if hasattr(self, "grid_reg"): self.relayout()
    def closeEvent(self, e):
        if QSystemTrayIcon.isSystemTrayAvailable(): self.set_live(False); e.ignore(); self.hide()
        else: e.accept()
    def show_window(self):
        self.refresh_home(); self.show(); self.raise_(); self.activateWindow()
        self.set_live(self.live_on and TABS[self.stack.currentIndex()][1] == "Captura")
    def apply_theme(self):
        _, dark, bg, panel, acc = WTHEMES[self.theme_idx]; fg = (230, 232, 240) if dark else (30, 32, 40)
        pal = QPalette()
        for role, col in ((QPalette.ColorRole.Window, bg), (QPalette.ColorRole.WindowText, fg), (QPalette.ColorRole.Base, panel),
                          (QPalette.ColorRole.AlternateBase, panel), (QPalette.ColorRole.Text, fg), (QPalette.ColorRole.Button, panel),
                          (QPalette.ColorRole.ButtonText, fg), (QPalette.ColorRole.Highlight, acc), (QPalette.ColorRole.HighlightedText, (255, 255, 255)),
                          (QPalette.ColorRole.ToolTipBase, panel), (QPalette.ColorRole.ToolTipText, fg)):
            pal.setColor(role, QColor(*col))
        self.app.setPalette(pal)
        for ic, tx in list(getattr(self, "title_icons", [])):
            try: ic.setPixmap(title_icon(tx, QColor(*acc)))
            except RuntimeError: pass
        A = f"rgb({acc[0]},{acc[1]},{acc[2]})"; P = f"rgb({panel[0]},{panel[1]},{panel[2]})"; B = f"rgba({fg[0]},{fg[1]},{fg[2]},60)"
        A2 = f"rgb({min(255, acc[0] + 35)},{min(255, acc[1] + 35)},{min(255, acc[2] + 35)})"; H = f"rgba({fg[0]},{fg[1]},{fg[2]},22)"; M = f"rgba({fg[0]},{fg[1]},{fg[2]},150)"
        self.app.setStyleSheet(f"""
          QPushButton {{ background:{P}; border:1px solid {B}; border-radius:8px; padding:4px 12px; }}
          QPushButton:hover {{ border-color:{A}; background:{H}; }} QPushButton:pressed {{ background:{A}; color:white; }}
          QPushButton#btnPrimary {{ background:{A}; color:white; border:none; font-weight:600; padding:5px 18px; }}
          QPushButton#btnPrimary:hover {{ background:{A2}; }}
          QPushButton#btnStart {{ border-color:#34c759; color:#34c759; }} QPushButton#btnStart:hover {{ background:rgba(52,199,89,40); }}
          QPushButton#btnStop {{ border-color:#ff5a52; color:#ff5a52; }} QPushButton#btnStop:hover {{ background:rgba(255,90,82,40); }}
          QPushButton#btnDanger {{ border-color:#ff9f0a; color:#ff9f0a; }} QPushButton#btnDanger:hover {{ background:rgba(255,159,10,40); }}
          QCheckBox#switch::indicator {{ width:32px; height:16px; border-radius:9px; background:{B}; border:1px solid {B}; }}
          QCheckBox#switch::indicator:checked {{ background:{A}; border-color:{A}; }}
          QFrame#tile {{ background:{P}; border-radius:10px; }}
          QLabel#cap {{ color:{M}; font-size:11px; }} QLabel#val {{ font-size:15px; font-weight:600; }}
          QSlider::groove:horizontal {{ height:6px; background:{B}; border-radius:3px; }}
          QSlider::sub-page:horizontal {{ background:{A}; border-radius:3px; }}
          QSlider::handle:horizontal {{ background:rgb({fg[0]},{fg[1]},{fg[2]}); width:14px; margin:-5px 0; border-radius:7px; }}
          QListWidget {{ background:{P}; border:none; border-radius:8px; padding:4px; }}
          QListWidget::item {{ padding:4px; border-radius:6px; }} QListWidget::item:selected {{ background:{A}; color:white; }}
          QLabel#sec {{ font-size:16px; font-weight:bold; color:{A}; }}
          QLabel#card {{ background:{P}; border-radius:10px; padding:12px; }}
          QComboBox, QSpinBox, QLineEdit {{ background:{P}; border:1px solid {B}; border-radius:5px; padding:1px 6px; min-height:20px; }}
          QPlainTextEdit {{ background:{P}; border:1px solid {B}; border-radius:6px; padding:4px; }}
        """)


# Windows session end is different from the tray's explicit Quit command.
# Qt emits commitDataRequest while Windows is logging off or shutting down.
# Keep this bounded and silent: the desktop is already being terminated.
_WINDOWS_SHUTDOWN_REQUEST = 0x0011
_WINDOWS_SHUTDOWN_CONFIRM = 0x0016
_windows_shutdown_handled = False


def log_windows_shutdown(text):
    if not IS_WIN:
        return
    try:
        win_dir().mkdir(parents=True, exist_ok=True)
        with (win_dir() / "shutdown.log").open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S") +
                         " pid=" + str(os.getpid()) + " " + str(text)[:600] + "\n")
    except OSError:
        pass


class WindowsShutdownFilter(QAbstractNativeEventFilter):
    # Handle the Windows end-of-session notification even when the Qt GUI
    # is started hidden with --tray. Never suppress Windows' own message.
    def nativeEventFilter(self, event_type, message):
        if not IS_WIN:
            return False
        try:
            if bytes(event_type) != b"windows_generic_MSG":
                return False
            import ctypes
            from ctypes import wintypes
            native = wintypes.MSG.from_address(int(message))
            if native.message == _WINDOWS_SHUTDOWN_REQUEST:
                log_windows_shutdown("WM_QUERYENDSESSION received")
            elif native.message == _WINDOWS_SHUTDOWN_CONFIRM:
                if native.wParam:
                    windows_session_shutdown(None)
                else:
                    log_windows_shutdown("WM_ENDSESSION cancelled")
        except Exception as error:
            log_windows_shutdown("native filter error: " + repr(error))
        return False


def windows_session_shutdown(_session_manager):
    global _windows_shutdown_handled
    if not IS_WIN or _windows_shutdown_handled:
        return
    _windows_shutdown_handled = True
    log_windows_shutdown("WM_ENDSESSION confirmed; blackout starting")
    # Windows expects a quick response to session-end messages. The old
    # implementation could time out while killing the backend and then try
    # to open HID while it was still held by that backend.
    exe = win_dir() / "quiklight.exe"
    if not exe.is_file():
        return
    log = win_dir() / "shutdown.log"
    started = time.monotonic()
    notes = []
    try:
        # Do not spawn a PowerShell process or touch the Qt UI here.
        killed = subprocess.run(
            ["taskkill", "/IM", "quiklight.exe", "/F"],
            capture_output=True, creationflags=NOWIN, timeout=1.5,
        )
        notes.append("taskkill=" + str(killed.returncode))
        if killed.returncode != 0:
            notes.append("taskkill-stderr=" + killed.stderr.decode("utf-8", "replace")[-160:])
        # Only the known-working, 63-LED legacy protocol is used.
        off = subprocess.run(
            [str(exe), "--off"], capture_output=True,
            creationflags=NOWIN, timeout=2.0,
        )
        notes.append("off=" + str(off.returncode))
        if off.returncode:
            notes.append("off-stderr=" + off.stderr.decode("utf-8", "replace")[-300:])
    except subprocess.TimeoutExpired as error:
        notes.append("timeout=" + str(error.cmd))
    except Exception as error:
        notes.append("exception=" + repr(error)[:300])
    finally:
        try:
            win_dir().mkdir(parents=True, exist_ok=True)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(time.strftime("%Y-%m-%d %H:%M:%S") +
                             " session-end duration-ms=" + str(elapsed_ms) +
                             " " + " | ".join(notes) + "\n")
        except OSError:
            pass

# ───────────────────────── Bandeja ─────────────────────────
def build_tray(app, win):
    tray = QSystemTrayIcon(app_icon(), app); menu = QMenu()

    def quit_with_leds_off():
        # Only this tray action changes. Leave the known-working Windows
        # restart path and the Rust USB/HID protocol untouched.
        if not IS_WIN:
            app.quit()
            return
        if getattr(win, "_tray_exit_in_progress", False):
            return
        win._tray_exit_in_progress = True
        import threading
        result = []

        def stop_worker():
            exe = win_dir() / "quiklight.exe"
            try:
                if not exe.is_file():
                    result.append("Executável do serviço não encontrado.")
                    return
                # Use the same proven sequence as win_service('stop'):
                # release the backend HID handle, then run the existing --off.
                subprocess.run(
                    ["taskkill", "/IM", "quiklight.exe", "/F"],
                    capture_output=True, creationflags=NOWIN, timeout=5,
                )
                time.sleep(0.2)
                if win_running():
                    result.append("O processo quiklight.exe ainda está em execução.")
                    return
                off = subprocess.run(
                    [str(exe), "--off"], capture_output=True, text=True,
                    creationflags=NOWIN, timeout=8,
                )
                if off.returncode != 0:
                    details = (off.stderr or off.stdout or "").strip()
                    result.append("Falha ao enviar o desligamento à fita." +
                                  (("\n" + details[-350:]) if details else ""))
                else:
                    result.append(None)
            except subprocess.TimeoutExpired:
                result.append("Tempo esgotado na comunicação com o controlador USB.")
            except Exception as error:
                result.append("Falha ao desligar a fita: " + str(error))

        # Keep the Qt event loop responsive if a USB HID call stalls.
        timer = QTimer(win)
        win._tray_exit_timer = timer
        def finish():
            if not result:
                return
            timer.stop()
            win._tray_exit_in_progress = False
            if result[0] is None:
                app.quit()
            else:
                QMessageBox.warning(win, "Quiklight",
                                    result[0] + "\nA interface continuará aberta para uma nova tentativa.")
        timer.timeout.connect(finish)
        threading.Thread(target=stop_worker, daemon=True).start()
        timer.start(100)

    def rebuild():
        menu.clear(); run = is_active()
        menu.addAction(tr("Abrir configurações"), win.show_window)
        menu.addSeparator(); a = menu.addAction("● " + tr("Rodando") if run else "○ " + tr("Parado")); a.setEnabled(False)
        if run:
            menu.addAction(tr("Desligar"), lambda: service_cmd("stop")); menu.addAction(tr("Reiniciar"), lambda: service_cmd("restart"))
        else: menu.addAction(tr("Ligar"), lambda: service_cmd("start"))
        sub = menu.addMenu(tr("Presets"))
        for n in list_presets(): sub.addAction(n, lambda _c=False, n=n: apply_preset_by_name(n))
        menu.addSeparator(); menu.addAction(tr("Sair do ícone"), quit_with_leds_off)
    menu.aboutToShow.connect(rebuild); tray.setContextMenu(menu)
    tray.activated.connect(lambda r: win.show_window() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show(); return tray

def main():
    global LANG
    LANG = read_lang()
    tray_only = "--tray" in sys.argv
    app = QApplication(sys.argv); app.setStyle("Fusion"); app.setQuitOnLastWindowClosed(False)
    if IS_WIN:
        # commitDataRequest is associated with WM_QUERYENDSESSION.
        # Microsoft requires quick acknowledgement there; perform USB I/O
        # later at WM_ENDSESSION, when the Windows session really ends.
        app.commitDataRequest.connect(
            lambda manager: log_windows_shutdown("Qt commitDataRequest received"),
            Qt.ConnectionType.DirectConnection)
    sock = QLocalSocket(); sock.connectToServer(APP_ID)
    if sock.waitForConnected(300):
        if not tray_only: sock.write(b"show"); sock.flush(); sock.waitForBytesWritten(300)
        return 0
    ensure_default_presets()
    # Launch the LED driver before creating widgets/reading USB inventory.
    if IS_WIN and not is_active(): service_cmd("start")
    win = Win(app)
    if IS_WIN:
        # Crucial for tray-only startup: create an invisible top-level HWND
        # so Windows can deliver WM_QUERYENDSESSION / WM_ENDSESSION.
        native_hwnd = int(win.winId())
        app._quiklight_shutdown_filter = WindowsShutdownFilter()
        app.installNativeEventFilter(app._quiklight_shutdown_filter)
        log_windows_shutdown("native watcher ready HWND=" + str(native_hwnd))
    tray = build_tray(app, win)
    QLocalServer.removeServer(APP_ID); srv = QLocalServer(); srv.listen(APP_ID); conns = []
    def on_conn():
        c = srv.nextPendingConnection(); conns.append(c)
        c.readyRead.connect(lambda c=c: win.show_window() if bytes(c.readAll()) == b"show" else None)
    srv.newConnection.connect(on_conn)
    if not tray_only or not QSystemTrayIcon.isSystemTrayAvailable(): win.show_window()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
