"""PyQt6 navigation shell and game controller."""
from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPushButton, QPlainTextEdit,
    QScrollArea, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from database.database_manager import (
    add_challenge, add_user, get_challenges, get_leaderboard, get_results,
    get_selected_user_id, get_user_achievements, get_users, rename_user,
    save_result, select_user, delete_user,
)
from game.key_mapper import reverse_scrambled
from game.typing_calculator import format_duration
from game.typing_test import GameSession, Phase
from models import Difficulty, ModeCode


class TypingInput(QLineEdit):
    """A typing field that can be made append-only for blind modes."""

    def __init__(self) -> None:
        super().__init__()
        self.append_only = False
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.append_only:
            blocked = {
                Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Left,
                Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
                Qt.Key.Key_Home, Qt.Key.Key_End,
            }
            if event.key() in blocked or event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.append_only:
            self.setCursorPosition(len(self.text()))
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.append_only:
            super().mouseMoveEvent(event)


class MainMenu(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("InkSpeed - Typing Test and Practice")
        self.resize(1100, 760)
        self.current_user_id = get_selected_user_id()
        self.session: GameSession | None = None
        self._build()
        self.refresh_all()

    def _build(self) -> None:
        root, layout = QWidget(), QVBoxLayout()
        root.setObjectName("appRoot")
        root.setLayout(layout)
        header = QWidget()
        header.setObjectName("header")
        nav = QHBoxLayout(header)
        nav.setContentsMargins(0, 0, 0, 0)
        logo = QLabel('<b>Ink<span style="color:#e74b28">Speed</span></b>')
        logo.setObjectName("logo")
        nav.addWidget(logo)
        nav.addSpacing(28)
        self.pages = QStackedWidget()
        self.pages.setMaximumWidth(900)
        self.pages.setMinimumWidth(760)
        for title, page_index in (
            (("Play", 0), ("History", 2), ("Leaderboard", 3), ("Challenges", 4), ("Achievements", 5))
        ):
            button = QPushButton(title)
            button.setObjectName("navButton")
            button.clicked.connect(lambda _=False, i=page_index: self.pages.setCurrentIndex(i))
            nav.addWidget(button)
        nav.addStretch()
        self.header_user = QLabel()
        self.header_user.setObjectName("headerUser")
        nav.addWidget(self.header_user)
        layout.addWidget(header)
        body = QScrollArea()
        body.setWidgetResizable(True)
        body.setObjectName("bodyScroll")
        body_host = QWidget()
        body_host.setObjectName("bodyHost")
        body_layout = QHBoxLayout(body_host)
        body_layout.setContentsMargins(16, 0, 16, 0)
        body_layout.addWidget(self.pages, 0, alignment=Qt.AlignmentFlag.AlignTop)
        body.setWidget(body_host)
        layout.addWidget(body)
        for page in (
            self._players_page(), self._play_page(), self._history_page(),
            self._leaderboard_page(), self._challenges_page(), self._achievements_page(),
        ):
            self.pages.addWidget(page)
        self.setCentralWidget(root)

    def _players_page(self) -> QWidget:
        page, layout = QWidget(), QVBoxLayout()
        page.setObjectName("page")
        layout.setContentsMargins(48, 8, 48, 40)
        page.setLayout(layout)
        eyebrow = QLabel("TYPING TEST & PRACTICE")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)
        hero = QLabel("Type fast.<br>Leave a mark.")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        player_card = QWidget()
        player_card.setObjectName("card")
        card_layout = QVBoxLayout(player_card)
        card_layout.addWidget(QLabel("Player"))
        player_hint = QLabel("No password needed — just a username (4–20 characters).")
        player_hint.setObjectName("muted")
        card_layout.addWidget(player_hint)
        self.players = QListWidget()
        self.players.setObjectName("playerList")
        self.player_scroll = QScrollArea()
        self.player_scroll.setWidgetResizable(True)
        self.player_scroll.setMaximumHeight(180)
        self.player_scroll.setWidget(self.players)
        card_layout.addWidget(self.player_scroll)
        row = QHBoxLayout()
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username (4-20 characters)")
        for text, handler in (("Add player", self._add_player),):
            button = QPushButton(text)
            button.clicked.connect(handler)
            row.addWidget(button)
        self.rename_button = QPushButton("Rename")
        self.rename_button.clicked.connect(self._rename_player)
        row.addWidget(self.rename_button)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._delete_player)
        row.addWidget(self.delete_button)
        row.insertWidget(0, self.username)
        card_layout.addLayout(row)
        layout.addWidget(player_card)
        mode_title = QLabel("Choose a mode")
        mode_title.setObjectName("sectionTitle")
        layout.addWidget(mode_title)
        mode_row = QHBoxLayout()
        for index, (number, name, description) in enumerate((
            ("01", "Classic", "A standard timed typing test."),
            ("02", "Memory Rush", "Memorize, then type it blind. Survive the rounds."),
            ("03", "Key Chaos", "Memorize, then type through scrambled keys."),
        )):
            card = QWidget()
            card.setObjectName("modeCard")
            card_layout = QVBoxLayout(card)
            label = QLabel(number)
            label.setObjectName("eyebrow")
            card_layout.addWidget(label)
            title = QLabel(name)
            title.setObjectName("cardTitle")
            card_layout.addWidget(title)
            description_label = QLabel(description)
            description_label.setObjectName("muted")
            description_label.setWordWrap(True)
            card_layout.addWidget(description_label)
            card_layout.addStretch()
            play = QPushButton("Play →")
            play.setObjectName("primaryButton")
            play.clicked.connect(lambda _=False, i=index: self._open_mode(i))
            card_layout.addWidget(play)
            mode_row.addWidget(card)
        layout.addLayout(mode_row)
        layout.addStretch()
        self.players.itemClicked.connect(self._select_player)
        return page

    def _open_mode(self, index: int) -> None:
        if not self._require_user():
            return
        self.mode.setCurrentIndex(index)
        self.pages.setCurrentIndex(1)

    def _play_page(self) -> QWidget:
        page, layout = QWidget(), QVBoxLayout()
        page.setObjectName("page")
        layout.setContentsMargins(48, 8, 48, 40)
        page.setLayout(layout)
        self.play_heading = QLabel("Set up your run.")
        self.play_heading.setObjectName("pageTitle")
        layout.addWidget(self.play_heading)
        controls = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(["Classic", "Memory Rush", "Key Chaos"])
        self.duration = QSpinBox()
        self.duration.setRange(15, 300)
        self.duration.setValue(60)
        self.difficulty = QComboBox()
        self.difficulty.addItems(["Any", "Easy", "Medium", "Hard"])
        start = QPushButton("Start")
        start.clicked.connect(self._start_game)
        for label, widget in (
            ("Mode", self.mode), ("Seconds", self.duration), ("Difficulty", self.difficulty)
        ):
            controls.addWidget(QLabel(label))
            controls.addWidget(widget)
        controls.addWidget(start)
        layout.addLayout(controls)
        self.status = QLabel("Choose a player and start a game.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.passage = QLabel()
        self.passage.setObjectName("passage")
        self.passage.setWordWrap(True)
        layout.addWidget(self.passage)
        self.input = TypingInput()
        self.input.setObjectName("typingInput")
        self.input.setEnabled(False)
        self.input.textChanged.connect(self._typed_changed)
        layout.addWidget(self.input)
        self.ready = QPushButton("I'm ready")
        self.ready.clicked.connect(self._ready)
        self.ready.hide()
        layout.addWidget(self.ready)
        self.legend = QLabel()
        self.legend.setWordWrap(True)
        layout.addWidget(self.legend)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick)
        return page

    def _history_page(self) -> QWidget:
        page, layout = QWidget(), QVBoxLayout()
        layout.setContentsMargins(48, 8, 48, 40)
        page.setLayout(layout)
        layout.addWidget(QLabel("<h1>History</h1>"))
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(
            ["Date", "Mode", "WPM", "Accuracy", "Errors", "Score", "Duration"]
        )
        layout.addWidget(self.history_table)
        return page

    def _leaderboard_page(self) -> QWidget:
        page, layout = QWidget(), QVBoxLayout()
        layout.setContentsMargins(48, 8, 48, 40)
        page.setLayout(layout)
        layout.addWidget(QLabel("<h1>Leaderboard</h1>"))
        self.leaderboard_mode = QComboBox()
        self.leaderboard_mode.addItems(["Classic", "Memory Rush", "Key Chaos"])
        self.leaderboard_mode.currentIndexChanged.connect(self.refresh_leaderboard)
        layout.addWidget(self.leaderboard_mode)
        self.leaderboard = QListWidget()
        layout.addWidget(self.leaderboard)
        return page

    def _challenges_page(self) -> QWidget:
        page, layout = QWidget(), QVBoxLayout()
        layout.setContentsMargins(48, 8, 48, 40)
        page.setLayout(layout)
        layout.addWidget(QLabel("<h1>Challenges</h1>"))
        form = QFormLayout()
        self.challenge_category = QLineEdit()
        self.challenge_difficulty = QComboBox()
        self.challenge_difficulty.addItems(["Easy", "Medium", "Hard"])
        self.challenge_text = QPlainTextEdit()
        form.addRow("Category", self.challenge_category)
        form.addRow("Difficulty", self.challenge_difficulty)
        form.addRow("Passage", self.challenge_text)
        layout.addLayout(form)
        add = QPushButton("Add challenge")
        add.clicked.connect(self._add_challenge)
        layout.addWidget(add)
        self.challenge_list = QListWidget()
        layout.addWidget(self.challenge_list)
        return page

    def _achievements_page(self) -> QWidget:
        page, layout = QWidget(), QVBoxLayout()
        layout.setContentsMargins(48, 8, 48, 40)
        page.setLayout(layout)
        layout.addWidget(QLabel("<h1>Achievements</h1>"))
        self.achievements = QListWidget()
        layout.addWidget(self.achievements)
        return page

    def _require_user(self) -> bool:
        if self.current_user_id is None:
            QMessageBox.warning(self, "Player required", "Select a player first.")
            return False
        return True

    def _add_player(self) -> None:
        try:
            user = add_user(self.username.text())
            self.current_user_id = user.user_id
            select_user(user.user_id)
            self.username.clear()
            self.refresh_all()
        except Exception as error:
            QMessageBox.warning(self, "Unable to add player", str(error))

    def _select_player(self, item) -> None:
        self.current_user_id = int(item.data(32))
        select_user(self.current_user_id)
        self.refresh_all()

    def _rename_player(self) -> None:
        if not self._require_user():
            return
        name, ok = QInputDialog.getText(self, "Rename player", "New username:")
        if ok:
            try:
                rename_user(self.current_user_id, name)
                self.refresh_all()
            except Exception as error:
                QMessageBox.warning(self, "Unable to rename player", str(error))

    def _delete_player(self) -> None:
        if not self._require_user():
            return
        if QMessageBox.question(self, "Delete player", "Delete this player and results?") != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_user(self.current_user_id)
        except Exception as error:
            QMessageBox.warning(self, "Unable to delete player", str(error))
            return
        self.current_user_id = None
        select_user(None)
        self.refresh_all()

    def _start_game(self) -> None:
        if not self._require_user():
            return
        mode = list(ModeCode)[self.mode.currentIndex()]
        difficulty = (
            None if self.difficulty.currentIndex() == 0
            else Difficulty(self.difficulty.currentText().lower())
        )
        self.session = GameSession(
            mode, get_challenges(), self.duration.value(), difficulty, self._game_finished
        )
        self.session.start()
        self.input.clear()
        self.input.append_only = mode != ModeCode.CLASSIC
        self.input.setEnabled(self.session.phase == Phase.TYPING)
        self.ready.setVisible(self.session.phase == Phase.MEMORIZE)
        self.passage.setText(self.session.target)
        self._render_session()
        self.timer.start()

    def _ready(self) -> None:
        if self.session:
            self.session.skip_memorize()
            self.input.append_only = self.session.mode != ModeCode.CLASSIC
            self.input.setEnabled(True)
            self.ready.hide()
            self.passage.setText("Type the passage from memory.")

    def _typed_changed(self, text: str) -> None:
        if not self.session or self.session.phase != Phase.TYPING:
            return
        current = self.session.typed
        if len(text) < len(current):
            if self.session.mode == ModeCode.CLASSIC:
                self.session.backspace()
            else:
                self.input.blockSignals(True)
                self.input.setText(current)
                self.input.setCursorPosition(len(current))
                self.input.blockSignals(False)
                return
        elif len(text) > len(current):
            for char in text[len(current):]:
                self.session.type_char(char)
        elif text != current:
            self.input.blockSignals(True)
            self.input.setText(current)
            self.input.setCursorPosition(len(current))
            self.input.blockSignals(False)
        self._render_session()

    def _tick(self) -> None:
        if not self.session:
            return
        self.session.tick()
        self._render_session()
        if self.session.phase == Phase.DONE:
            self.timer.stop()

    def _render_session(self) -> None:
        if not self.session:
            return
        if self.session.phase == Phase.MEMORIZE:
            self.passage.setText(self.session.target)
            self.status.setText(f"Memorize: {self.session.time_left:.1f}s")
        elif self.session.phase == Phase.TYPING:
            typed = self.session.typed
            rendered = []
            for index, character in enumerate(self.session.target):
                if index < len(typed):
                    color = "#16804b" if typed[index] == character else "#d43b35"
                elif index == len(typed):
                    color = "#e74b28"
                else:
                    color = "#8d8f99"
                rendered.append(
                    f'<span style="color:{color}">{character if character != " " else "&nbsp;"}</span>'
                )
            rendered_text = "".join(rendered)
            if self.session.mode != ModeCode.CLASSIC:
                rendered_text = rendered_text.replace("</span>", "</span>&#8203;")
            self.passage.setText(rendered_text)
            self.status.setText(
                f"Time {format_duration(self.session.time_left)} | "
                f"WPM {self.session.live_wpm} | Accuracy {self.session.live_accuracy}%"
            )
        if self.session.key_map:
            self.legend.setText(" | ".join(
                f"{wanted}: {pressed}"
                for wanted, pressed in sorted(reverse_scrambled(self.session.key_map).items())
            ))

    def _game_finished(self, draft) -> None:
        if self.current_user_id is None:
            return
        outcome = save_result(self.current_user_id, draft)
        self.status.setText(
            f"Finished: {draft.wpm} WPM, {draft.accuracy}% accuracy, "
            f"score {outcome.result.score}. Unlocked: "
            f"{', '.join(a.name for a in outcome.unlocked) or 'none'}"
        )
        self.input.setEnabled(False)
        self.refresh_all()

    def _add_challenge(self) -> None:
        try:
            add_challenge(
                self.challenge_category.text(),
                Difficulty(self.challenge_difficulty.currentText().lower()),
                self.challenge_text.toPlainText(),
            )
            self.challenge_category.clear()
            self.challenge_text.clear()
            self.refresh_challenges()
        except Exception as error:
            QMessageBox.warning(self, "Unable to add challenge", str(error))

    def refresh_all(self) -> None:
        user = next((u for u in get_users() if u.user_id == self.current_user_id), None)
        self.header_user.setText(f"@{user.username}" if user else "no player")
        self.refresh_players()
        self.refresh_history()
        self.refresh_leaderboard()
        self.refresh_challenges()
        self.refresh_achievements()

    def refresh_players(self) -> None:
        self.players.clear()
        users = get_users()
        for user in users:
            self.players.addItem(f"{user.username} ({user.user_id})")
            item = self.players.item(self.players.count() - 1)
            item.setData(32, user.user_id)
            if user.user_id == self.current_user_id:
                self.players.setCurrentItem(item)
        self.players.setVisible(bool(users))
        has_user = self.current_user_id is not None
        self.rename_button.setVisible(has_user)
        self.delete_button.setVisible(has_user)

    def refresh_history(self) -> None:
        results = get_results(self.current_user_id) if self.current_user_id else []
        self.history_table.setRowCount(len(results))
        for row, result in enumerate(results):
            values = (
                result.created_at.strftime("%Y-%m-%d %H:%M"), result.mode.value,
                result.wpm, f"{result.accuracy}%", result.errors, result.score,
                format_duration(result.duration_seconds),
            )
            for column, value in enumerate(values):
                self.history_table.setItem(row, column, QTableWidgetItem(str(value)))

    def refresh_leaderboard(self) -> None:
        self.leaderboard.clear()
        mode = list(ModeCode)[self.leaderboard_mode.currentIndex()]
        for rank, result in enumerate(get_leaderboard(mode), 1):
            self.leaderboard.addItem(
                f"{rank}. User {result.user_id} - {result.score} "
                f"({result.wpm} WPM, {result.accuracy}%)"
            )

    def refresh_challenges(self) -> None:
        self.challenge_list.clear()
        for challenge in get_challenges():
            self.challenge_list.addItem(
                f"{challenge.category} / {challenge.difficulty.value}: {challenge.text}"
            )

    def refresh_achievements(self) -> None:
        self.achievements.clear()
        if self.current_user_id is None:
            return
        for achievement in get_user_achievements(self.current_user_id):
            self.achievements.addItem(
                f"{achievement.code} - unlocked {achievement.unlocked_at}"
            )
