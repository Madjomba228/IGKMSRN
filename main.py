import sys
import os
import math
import random

from PyQt6.QtWidgets import (
    QApplication, QWidget,
    QVBoxLayout, QGraphicsScene, QGraphicsView,
    QGraphicsItem, QGraphicsPixmapItem, QFrame,
    QLineEdit, QLabel,
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QTimer, QElapsedTimer,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QKeyEvent,
    QPixmap, QFont, QPolygonF, QTransform, QLinearGradient,
)


# ---------- Константы ----------
REFERENCE_WIDTH = 1920
REFERENCE_HEIGHT = 1200

BALLOON_COUNT = 16
BALLOON_RADIUS = 400
HEARTS_PER_CLICK = 2

# ----- Игровая механика -----
CLICK_STEP = 0.03
DECAY_RATE = 0.1
MAX_ZOOM = 1.45
SHAKE_TIME = 0.22
SHAKE_STRENGTH = 20

# ----- Фон -----
BG_COLOR_A1 = "#0F172A"
BG_COLOR_A2 = "#1E293B"
BG_COLOR_B1 = "#2D1B4E"
BG_COLOR_B2 = "#1A1A2E"

BG_COLOR_PERIOD = 7.0
BG_ROTATION_PERIOD = 30.0

# ----- Арт -----
def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает в режиме разработки и в PyInstaller """
    import sys, os
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

ART_PATH = resource_path("art.jpg")

# ============================================================
#  Balloon
# ============================================================
class Balloon(QGraphicsItem):
    COLORS = ["#A2D2FF", "#BDE0FE", "#FFC8DD",
              "#FFAFCC", "#CDB4DB", "#B8E0D2"]

    def __init__(self, size: int, color: str,
                 base_x: float, base_y: float,
                 phase: float,
                 amplitude: float = 18,
                 speed: float = 1.2):
        super().__init__()
        self.size = size
        self.color = color
        self.base_x = base_x
        self.base_y = base_y
        self.phase = phase
        self.amplitude = amplitude
        self.speed = speed
        self.t = 0.0
        self.setPos(self.base_x, self.base_y)

    def boundingRect(self) -> QRectF:
        s = self.size
        return QRectF(-s / 2, -s / 2, s, s * 1.4)

    def paint(self, painter: QPainter, option, widget):
        s = self.size
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(self.color)))
        painter.drawEllipse(QRectF(-s / 2, -s / 2, s, s))
        painter.setBrush(QBrush(QColor(255, 255, 255, 90)))
        painter.drawEllipse(QRectF(-s * 0.28, -s * 0.32, s * 0.32, s * 0.32))
        painter.setBrush(QBrush(QColor(self.color).darker(130)))
        painter.drawPolygon(QPolygonF([
            QPointF(-s * 0.08, s / 2 - 2),
            QPointF( s * 0.08, s / 2 - 2),
            QPointF( 0,        s / 2 + s * 0.3),
        ]))

    def advance(self, dt: float):
        self.t += dt
        dx = math.sin(self.t * self.speed + self.phase) * self.amplitude
        dy = math.cos(self.t * self.speed * 0.7 + self.phase * 1.3) * self.amplitude * 0.5
        self.setPos(self.base_x + dx, self.base_y + dy)


# ============================================================
#  Heart
# ============================================================
class Heart(QGraphicsItem):
    COLORS = ["#FF1744", "#FF4569", "#F50057", "#FF80AB", "#FF8FA3"]

    def __init__(self, size: int):
        super().__init__()
        self.size = size
        self.color = random.choice(self.COLORS)
        self.vy = -random.uniform(350, 650)
        self.vx = 0.0
        self.life = 0.0
        self._build_polygon()

    def _build_polygon(self):
        pts = []
        s = self.size / 16.0
        for i in range(40):
            t = i / 40.0 * math.tau
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t)
                  - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append(QPointF(x * s, y * s))
        self.polygon = QPolygonF(pts)

    def boundingRect(self) -> QRectF:
        return self.polygon.boundingRect()

    def paint(self, painter: QPainter, option, widget):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(self.color)))
        painter.drawPolygon(self.polygon)

    def advance(self, dt: float) -> bool:
        self.life += dt
        self.setPos(self.x() + self.vx * dt, self.y() + self.vy * dt)
        return self.life < 2.5


# ============================================================
#  GiftBox
# ============================================================
class GiftBox(QGraphicsItem):
    def __init__(self, size: int):
        super().__init__()
        self.size = size
        self.is_open = False
        self.on_click = None

    def boundingRect(self) -> QRectF:
        s = self.size
        return QRectF(-s / 2 - 10, -s * 0.8, s + 20, s * 1.3)

    def paint(self, painter: QPainter, option, widget):
        s = self.size
        half = s / 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 90)))
        painter.drawRect(QRectF(-half + 8, -half + 8, s, s))

        painter.setBrush(QBrush(QColor("#F8F9FA")))
        painter.setPen(QPen(QColor("#ADB5BD"), 3))
        painter.drawRect(QRectF(-half, -half, s, s))

        lid_h = s * 0.28
        if self.is_open:
            painter.save()
            painter.translate(0, -half - lid_h * 0.9)
            painter.rotate(-18)
            painter.setBrush(QBrush(QColor("#E9ECEF")))
            painter.setPen(QPen(QColor("#ADB5BD"), 3))
            painter.drawRect(QRectF(-half * 1.05, -lid_h / 2, s * 1.05, lid_h))
            painter.restore()
        else:
            painter.setBrush(QBrush(QColor("#E9ECEF")))
            painter.setPen(QPen(QColor("#ADB5BD"), 3))
            painter.drawRect(QRectF(-half * 1.05, -half - lid_h / 2,
                                    s * 1.05, lid_h))

        painter.setBrush(QBrush(QColor("#4EA8DE")))
        painter.setPen(Qt.PenStyle.NoPen)
        rib = s * 0.14
        painter.drawRect(QRectF(-rib / 2, -half, rib, s))
        painter.drawRect(QRectF(-half, -rib / 2, s, rib))

        if not self.is_open:
            bow_r = s * 0.13
            painter.setBrush(QBrush(QColor("#4EA8DE")))
            painter.setPen(QPen(QColor("#3A86FF"), 2))
            painter.drawEllipse(QPointF(-bow_r * 0.8,
                                        -half - lid_h - bow_r * 0.4),
                                bow_r, bow_r)
            painter.drawEllipse(QPointF(bow_r * 0.8,
                                        -half - lid_h - bow_r * 0.4),
                                bow_r, bow_r)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_click:
            self.on_click()
        super().mousePressEvent(event)


# ============================================================
#  EasterEgg — секретное поле ввода
# ============================================================
class EasterEgg:
    """Поле ввода в углу с заготовленными ответами."""
    
    RESPONSES = {
        "привет": "И тебе привет, Дашут!",
        "даша": "Даа, это тыыы, наша сладкая булочка❤️",
        "довли": "Даа, это тыыы, моя булочка сладкая❤️",
        "спасибо": "Тебе спасибо, солнце моё 😋",
        "это мне?": "Тебе-тебе, открывай давай😇",
        "секрет": "Думай, подбирай, гадай, хи-хи-хи",
        "помощь": "Подсказок не будет. Просто кликай быстрее! 💨",
        "кто": "Тот, кто очень тебя ценит 🙂",
        "нююнь": "Нюююююююнь, уле-ле-ле-ле",
        "мяу": "Мяу-мяу-мямяу😭",
        "кофе": "Тебе нельзя, ты и так бодрая ☕...ну разве что если ты и мне сделаешь🐀",
        "диплом": "Обязательно сдашь, я в тебя верю! Очень жду результата!📚",
        "сколько?":"Так много, что я устал писать. Точнее руки устали, я только рад был☺️",
        "кьюша":"У вас с ней всё будет хорошо, вот увидишь! Главное - не сдавайся!",
        "эйдина":"Я очень рад, что вы с ней подружились!",
        "люблю":"Я тебя тоже очень люблю, искренне и нежно☺️",
        "томск":"Город небольшой, но тебе тут всегда рады❤️...особенно в моём доме😇",
        "питер":"Удивительный город, хотел бы его посетить. Но только с тобой📸",
        "улыбка":"Ты очень милая, когда улыбаешься. Надеюсь, ты будешь делать это почаще☺️",
        "деньги":"Ох, знаю, ты взрослая тётя и гордость не позволяет тебе принять мою помощь, но дай маленькому мальчику себя проявить и порадовать любимую🐀😌",
        "масло":"смяжьте мясло маслом -_-",
        "мосси":"Да, это яяя - Мосси (´｡•ᵕ•｡`)",
        "мося":"Да, это яяя - Мося (ᵔ ⩊ ᵔ)",
        "моська":"Твоя, или моя? Мне нравятся обе👉👈",
        "чмок":"Юпиии, меня чмокнула Довли🥳",
        "сипухи":"помню, ты хотела себе сипуху, да?...)",
        "день рождения":"дааа, у тебя! Пусть он будет чудесным!",
        "диша":"Ну,допустим, гав",
        "собака":"Здесь был Диша" ,
        "опоссум":"Здесь была Эдна",
        "группа":"OLT Foreva!!! (Д)",
        "дельтарун":"Тоби Фокс - пидорас (Д)",
        "бег":"Ещё один день бегства от армии Израиля (Д)",
        "призрак":"А какие у этой программы призрачные трюки? (Д)",
        "порча":"Насылаю Ломели порчу на понос (Д)",
        "урожай":"Добро пожаловать в Урожайск (Д)",
        "крис": "Ты всегда был шутнярой, Крис (Д)",
        "балдура":"Тёмный Сасазм (Д)",
        "зелёный":"Eat your greens (Д)",
        "шишка":"Блблблблб, нююююнь (Д)",
        "насла":"Я всего лишь рыб (Д)",
        "удивление":"Ебутся гуси в кукурузе (Д)",
        "нация":"Крузи!",
        "нахуй мир":"...и ссаный пидор!",
        "сова":"Совушки едят крыс, но ты ведь меня не скушаешь, правда, Солнце моё?👀",
        "ида":"Лет ми дуу ит фор юю",
        "свага":"С-В-А-Г-А, это SWAG",
        "тык":"чего тыкаешь? Я тоже тебя буду тыкать👈",
        "писька":"Почему ты решила это написать?...",
        "питон":"Да, я на питоне это написал, хехехе",
        "слайм":"do u like poopin?",
        "голубой":"Я, или цвет твоих волос?👀",
        "слово":"Подход интересный, конечно",
        "случайное":"рандом-рандом, подари мне дом🙏",
        "бее":"бе-бе-бе, ба-ба-ба, бу-бу-бу😛",
        "кирилл":"а даа, это я, халоу 🫪",
        "диско":"и лизиум😛🐱",
        "куно":"похуй!",
        "куни":"ты ведь хотела написать куно, правда?..",
        "200":"не груз, но количество",
        "твиттер":"-соевая помойка, туда не заходим =_=",
        "тольятти":"мне даже интересно, хочешь ли ты туда снова? Я бы съездил, за компанию(„• ᴗ •„)",
        "соль":"Ты это как житель Питера говоришь?",
        "кто здесь?":"и правда, кто? Голоса в голове",
        "правда":"правду узнаешь позже, пока просто радуйся(„• ᴗ •„)",
        "кино":"Верь в себя! Если ты действительно хочешь заниматься кино, ты обязательно найдёшь способ сделать всё по-своему!",
        "альтушка":"И снова же - я, или ты?",
        "очки":"Тебе очень идут очки, Дашут, ты в них очень милая (❤⩊❤)",
        "торт":"Обязательно покушай тортик! В следующий раз я обязательно найду способ испечь тебе пирог(´,•ω•,)♡",
        "энергос":"Не-а, низя. Лучше чаю с тортиком (o^ ^o)",
        "мы":"Мы-мы-мы...а кто мы? (◕▿◕)",
        "купрум теллириум":"Это про тебя, потому что ты CuTe (❤⩊❤)",
        "ням":"Тортик уже кушаешь👀? Приятного аппетита!(„• ᴗ •„)",
        "вэсс":"Дизайн шикардосненький, полюбил тату благодаря тебе👉👈",
        "сьюзи":"основная причина дырок в бюджете группы - сожранные ею барабанные палочки",
        "мысль":"Пока человек старается и желает лучшего результата - он обязательно его добъётся. Поэтому верь в себя, а когда тяжело - мы всегда рядом!",
        "прошлое":"Прошлое, оно потому и прошлое. На нём нужно учиться, а не застревать в нём, как бы хорошо нам тогда ни было. Всегда можно сделать лучше!"
    }
    
    FALLBACKS = [
        "Так много вариантов...🤔",
        "Как думаешь, что тут может быть?",
        "Вроде близко...👀",
        "Не-а, что-то иное",
        "Я бы очень хотел тебе подсказать, но, увы и ах"
    ]
    
    def __init__(self, parent: QWidget):
        self.parent = parent
        
        # ---- Поле ввода ----
        self.input = QLineEdit(parent)
        self.input.setPlaceholderText("сюда можно что-то написать...")
        self.input.setFixedWidth(400)
        self.input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 30);
                color: rgba(255, 255, 255, 180);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 50);
                color: white;
                border: 1px solid rgba(255, 255, 255, 120);
            }
        """)
        self.input.returnPressed.connect(self._on_enter)
        
        # ---- Метка ответа ----
        self.answer = QLabel("", parent)
        self.answer.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 180);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }
        """)
        self.answer.setVisible(False)
        
        # ---- Таймер скрытия ----
        self.hide_timer = QTimer(parent)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._hide_answer)
        
        self.reposition()
    
    def reposition(self):
        """Ставим поле в правый нижний угол."""
        margin = 20
        w = self.parent.width()
        h = self.parent.height()
        
        self.input.move(
            w - self.input.width() - margin,
            h - self.input.height() - margin,
        )
        
        self.answer.adjustSize()
        self.answer.move(
            w - self.answer.width() - margin,
            h - self.input.height() - self.answer.height() - margin - 10,
        )
    
    def _on_enter(self):
        text = self.input.text().strip().lower()
        if not text:
            return
        
        if text in self.RESPONSES:
            reply = self.RESPONSES[text]
        else:
            reply = random.choice(self.FALLBACKS)
        
        self.input.clear()
        self.input.clearFocus()   # возвращаем фокус окну
        self._show_answer(reply)
    
    def _show_answer(self, text: str):
        self.answer.setText(text)
        self.answer.adjustSize()
        self.reposition()
        self.answer.setVisible(True)
        self.answer.raise_()
        self.hide_timer.start(3000)
    
    def _hide_answer(self):
        self.answer.setVisible(False)


# ============================================================
#  Главное окно
# ============================================================
class HappyBirthdayDowly(QWidget):
    def __init__(self):
        super().__init__()

        # ---------- Экран и масштаб ----------
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        self.window_width = geo.width()
        self.window_height = geo.height()
        self.scale = min(self.window_width / REFERENCE_WIDTH,
                         self.window_height / REFERENCE_HEIGHT)
        self.scale = max(0.75, min(2.0, self.scale))

        self.setWindowTitle('С днём рождения, Дашенька!')

        # ---------- Сцена и вид ----------
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, self.window_width, self.window_height)

        self.view = QGraphicsView(self.scene)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        box_x = self.window_width / 2
        box_y = self.window_height / 2

        # ---------- Коробка ----------
        box_size = int(220 * self.scale)
        self.gift_box = GiftBox(box_size)
        self.gift_box.setPos(box_x, box_y)
        self.gift_box.setZValue(2)
        self.gift_box.on_click = self._on_box_click
        self.scene.addItem(self.gift_box)

        # ---------- Шарики ----------
        self.balloons: list[Balloon] = []
        self._place_balloons(box_x, box_y, box_size)

        # ---------- Арт ----------
        self.art_item = None
        self._prepare_art()

        # ---------- Сердечки ----------
        self.hearts: list[Heart] = []

        # ---------- Состояние игры ----------
        self.progress = 0.0
        self.shake_timer = 0.0
        self.box_opened = False
        self.bg_time = 0.0

        # ---------- Главный таймер ----------
        self.clock = QElapsedTimer()
        self.clock.start()
        self.last_time = 0.0

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

        # ---------- Layout ----------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        # ---------- Пасхалка ----------
        self.easter_egg = EasterEgg(self)
        self.easter_egg.input.raise_()

    # --------------------------------------------------------
    #  Фон
    # --------------------------------------------------------
    def _update_background(self, dt: float):
        self.bg_time += dt

        color_t = (math.sin(self.bg_time * math.tau / BG_COLOR_PERIOD) + 1) / 2

        def lerp_color(c1: str, c2: str, t: float) -> QColor:
            a, b = QColor(c1), QColor(c2)
            return QColor(
                int(a.red()   + (b.red()   - a.red())   * t),
                int(a.green() + (b.green() - a.green()) * t),
                int(a.blue()  + (b.blue()  - a.blue())  * t),
            )

        top = lerp_color(BG_COLOR_A1, BG_COLOR_B1, color_t)
        bottom = lerp_color(BG_COLOR_A2, BG_COLOR_B2, color_t)

        angle = self.bg_time * math.tau / BG_ROTATION_PERIOD
        cx = self.window_width / 2
        cy = self.window_height / 2
        r = max(self.window_width, self.window_height)

        x1 = cx + math.cos(angle) * r
        y1 = cy + math.sin(angle) * r
        x2 = cx - math.cos(angle) * r
        y2 = cy - math.sin(angle) * r

        gradient = QLinearGradient(x1, y1, x2, y2)
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(1.0, bottom)

        self.scene.setBackgroundBrush(QBrush(gradient))

    # --------------------------------------------------------
    #  Расстановка шариков
    # --------------------------------------------------------
    def _place_balloons(self, box_x: float, box_y: float, box_size: int):
        size = int(64 * self.scale)
        min_dist = size * 1.2
        min_dist_from_box = box_size / 2 + size * 1.2

        r_min = min_dist_from_box
        r_max = BALLOON_RADIUS * self.scale * 1.6

        placed: list[tuple[float, float]] = []

        for i in range(BALLOON_COUNT):
            found = False
            for _ in range(300):
                angle = random.uniform(0, math.tau)
                r = math.sqrt(random.uniform(r_min ** 2, r_max ** 2))

                x = box_x + math.cos(angle) * r
                y = box_y + math.sin(angle) * r * 0.6

                dx_box = x - box_x
                dy_box = (y - box_y) / 0.6
                if math.hypot(dx_box, dy_box) < min_dist_from_box:
                    continue

                too_close = False
                for (px, py) in placed:
                    if math.hypot(x - px, y - py) < min_dist:
                        too_close = True
                        break
                if too_close:
                    continue

                placed.append((x, y))
                self._add_balloon(i, size, x, y)
                found = True
                break

            if not found:
                angle = random.uniform(0, math.tau)
                r = random.uniform(r_min, r_max)
                x = box_x + math.cos(angle) * r
                y = box_y + math.sin(angle) * r * 0.6
                placed.append((x, y))
                self._add_balloon(i, size, x, y)

    def _add_balloon(self, index: int, size: int, x: float, y: float):
        b = Balloon(
            size=size,
            color=Balloon.COLORS[index % len(Balloon.COLORS)],
            base_x=x,
            base_y=y,
            phase=random.uniform(0, math.tau),
            amplitude=18 * self.scale,
            speed=random.uniform(0.9, 1.6),
        )
        b.setZValue(1)
        self.scene.addItem(b)
        self.balloons.append(b)

    # --------------------------------------------------------
    def _prepare_art(self):
        pixmap = QPixmap(ART_PATH)
        if pixmap.isNull():
            pixmap = QPixmap(800, 600)
            pixmap.fill(QColor("#BDE0FE"))
            painter = QPainter(pixmap)
            painter.setPen(QColor("#1a1a2e"))
            painter.setFont(QFont("Segoe UI", 42, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(),
                             Qt.AlignmentFlag.AlignCenter,
                             "Тут будет твой арт")
            painter.end()

        target_w = int(self.window_width * 0.75)
        target_h = int(self.window_height * 0.75)
        pixmap = pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.art_item = QGraphicsPixmapItem(pixmap)
        self.art_item.setTransformOriginPoint(
            pixmap.width() / 2, pixmap.height() / 2
        )
        self.art_item.setPos(
            self.window_width / 2 - pixmap.width() / 2,
            self.window_height / 2 - pixmap.height() / 2,
        )
        self.art_item.setScale(0.0)
        self.art_item.setVisible(False)
        self.art_item.setZValue(3)
        self.scene.addItem(self.art_item)

    # --------------------------------------------------------
    def _on_box_click(self):
        if self.box_opened:
            return

        self.progress = min(1.0, self.progress + CLICK_STEP)
        self.shake_timer = SHAKE_TIME
        self._spawn_hearts()

        if self.progress >= 1.0:
            self._open_box()

    # --------------------------------------------------------
    def _spawn_hearts(self):
        box_x = self.window_width / 2
        box_y = self.window_height / 2
        box_half = self.gift_box.size / 2

        for _ in range(HEARTS_PER_CLICK):
            h = Heart(size=int(44 * self.scale))
            side = random.choice([-1, 1])
            offset_x = random.uniform(box_half * 0.9,
                                      box_half * 3.2) * side
            x = box_x + offset_x
            y = box_y + random.uniform(0, box_half * 0.8)

            h.setPos(x, y)
            h.vy = -random.uniform(350, 650)
            h.vx = offset_x * 0.5
            h.setZValue(4)
            self.scene.addItem(h)
            self.hearts.append(h)

    # --------------------------------------------------------
    def _tick(self):
        now = self.clock.elapsed() / 1000.0
        dt = now - self.last_time
        self.last_time = now
        if dt <= 0:
            return
        if dt > 0.1:
            dt = 0.1

        self._update_background(dt)

        if not self.box_opened and self.progress > 0.0:
            self.progress = max(0.0, self.progress - DECAY_RATE * dt)

        if not self.box_opened:
            zoom = 1.0 + self.progress * (MAX_ZOOM - 1.0)
            self.view.setTransform(QTransform().scale(zoom, zoom))

        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            k = self.shake_timer / SHAKE_TIME
            strength = SHAKE_STRENGTH * self.scale * k
            dx = random.uniform(-strength, strength)
            dy = random.uniform(-strength, strength)
            self.scene.setSceneRect(dx, dy,
                                    self.window_width, self.window_height)
        else:
            self.scene.setSceneRect(0, 0,
                                    self.window_width, self.window_height)

        for b in self.balloons:
            b.advance(dt)

        alive = []
        for h in self.hearts:
            if h.advance(dt):
                alive.append(h)
            else:
                self.scene.removeItem(h)
        self.hearts = alive

    # --------------------------------------------------------
    def _open_box(self):
        self.box_opened = True
        self.gift_box.is_open = True
        self.gift_box.update()

        self.art_item.setVisible(True)

        duration_ms = 900
        steps = 40
        state = {"i": 0}

        def step():
            if state["i"] > steps:
                return
            t = state["i"] / steps
            eased = 1 - (1 - t) ** 3
            self.art_item.setScale(eased)
            state["i"] += 1
            if state["i"] <= steps:
                QTimer.singleShot(duration_ms // steps, step)

        step()

    # --------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "easter_egg"):
            self.easter_egg.reposition()

    # --------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HappyBirthdayDowly()
    window.showFullScreen()
    sys.exit(app.exec())