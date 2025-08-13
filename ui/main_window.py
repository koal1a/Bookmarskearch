
from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QMenuBar, QAction, QLabel, QCheckBox, QWidget, QHBoxLayout, QMessageBox, QDialog, QPlainTextEdit, QDialogButtonBox, QVBoxLayout
)
from PyQt5.QtCore import Qt
from .left_panel import LeftPanel
from .center_panel import CenterPanel
from .right_panel import RightPanel
from core import settings

class MainWindow(QMainWindow):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.setWindowTitle("검색")
        self.resize(1300, 900)
        self._double_click_flag = False

        self.init_ui()
        self.load_window_settings()

    def init_ui(self):
        self.splitter = QSplitter(Qt.Horizontal)
        self.left_panel = LeftPanel(self.state, self)
        self.center_panel = CenterPanel(self.state, self)
        self.right_panel = RightPanel(self.state, self)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.center_panel)
        self.splitter.addWidget(self.right_panel)

        self.setCentralWidget(self.splitter)

        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()

        # 파일 메뉴
        profile_menu = menubar.addMenu("프로필")
        profile1_action = QAction("프로필1", self)
        profile2_action = QAction("프로필2", self)
        profile1_action.triggered.connect(lambda: self.switch_profile("profile1"))
        profile2_action.triggered.connect(lambda: self.switch_profile("profile2"))
        profile_menu.addAction(profile1_action)
        profile_menu.addAction(profile2_action)

        # 편집 메뉴
        edit_menu = menubar.addMenu("편집")
        edit_search_history_action = QAction("북마크된 검색어 편집", self)
        edit_search_history_action.triggered.connect(self.edit_search_history_dialog)
        edit_menu.addAction(edit_search_history_action)

        # 보기 메뉴
        view_menu = menubar.addMenu("보기")
        reset_frames_action = QAction("프레임 초기화", self)
        reset_frames_action.triggered.connect(self.reset_splitter_sizes)
        view_menu.addAction(reset_frames_action)
        theme_menu = view_menu.addMenu("테마")
        default_theme_action = QAction("기본 테마", self)
        dark_theme_action = QAction("다크 테마", self)
        default_theme_action.triggered.connect(self.set_default_theme)
        dark_theme_action.triggered.connect(self.set_dark_theme)
        theme_menu.addAction(default_theme_action)
        theme_menu.addAction(dark_theme_action)

        # 코너 위젯
        self.current_profile_label = QLabel(f"현재 프로필: {self.state.current_profile}")
        self.current_profile_label.setStyleSheet("font-weight: bold; color: #00ffc8;")
        self.always_on_top_checkbox = QCheckBox("항상 위")
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.addWidget(self.current_profile_label)
        corner_layout.addWidget(self.always_on_top_checkbox)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        menubar.setCornerWidget(corner_widget, Qt.TopRightCorner)
        self.always_on_top_checkbox.stateChanged.connect(self.toggle_always_on_top)

    def set_font_size(self, size):
        settings.save_font_size(size)
        self.update_styles()

    def update_styles(self):
        theme = self.state.get_config_key("theme", "default")
        if theme == "dark":
            from .widgets import DARK_THEME_STYLESHEET
            self.setStyleSheet(DARK_THEME_STYLESHEET)
        else:
            self.setStyleSheet("")
        self.left_panel.init_ui()
        self.center_panel.init_ui()
        self.right_panel.init_ui()

    def switch_profile(self, profile_name):
        self.state.switch_profile(profile_name)
        self.current_profile_label.setText(f"현재 프로필: {profile_name}")
        self.left_panel.update_history_list()
        self.center_panel.update_history_tree()
        self.right_panel.update_url_list()
        QMessageBox.information(self, "프로필 전환", f"{profile_name}로 전환되었습니다.")

    def set_default_theme(self):
        self.setStyleSheet("")
        self.state.set_config_key("theme", "default")

    def set_dark_theme(self):
        from .widgets import DARK_THEME_STYLESHEET
        self.setStyleSheet(DARK_THEME_STYLESHEET)
        self.state.set_config_key("theme", "dark")

    def toggle_always_on_top(self, state):
        is_checked = state == Qt.Checked
        flags = self.windowFlags()
        if is_checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()
        self.state.set_config_key("always_on_top", is_checked)

    def reset_splitter_sizes(self):
        total_width = self.splitter.width()
        self.splitter.setSizes([total_width // 4, total_width // 2, total_width // 4])

    def load_window_settings(self):
        # 테마
        theme = self.state.get_config_key("theme", "default")
        if theme == "dark":
            self.set_dark_theme()
        # 항상 위
        always_on_top = self.state.get_config_key("always_on_top", False)
        self.always_on_top_checkbox.setChecked(always_on_top)
        # 스플리터
        splitter_sizes = self.state.get_config_key("splitter_sizes")
        if splitter_sizes:
            self.splitter.setSizes([int(s) for s in splitter_sizes])

    def closeEvent(self, event):
        # Stop background threads
        self.right_panel.stop_threads()
        # 스플리터 상태 저장
        self.state.set_config_key("splitter_sizes", self.splitter.sizes())
        # 트리 펼침 상태 저장
        self.center_panel.save_tree_expanded_state()
        # 모든 데이터 저장
        self.state.save_all_data()
        super().closeEvent(event)

    def edit_search_history_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("북마크된 검색어 .JSON형식 편집")
        dlg.resize(500, 500)
        layout = QVBoxLayout()
        edit = QPlainTextEdit()
        import json
        edit.setPlainText(json.dumps(self.state.search_history, ensure_ascii=False, indent=2))
        layout.addWidget(edit)
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)
        dlg.setLayout(layout)
        def save_search():
            import json
            try:
                self.state.search_history = json.loads(edit.toPlainText())
                self.state.save_search_history()
                self.center_panel.update_history_tree()
                dlg.accept()
            except Exception as e:
                QMessageBox.warning(self, "오류", f"JSON 형식이 올바르지 않습니다: {e}")
        btn_box.accepted.connect(save_search)
        btn_box.rejected.connect(dlg.reject)
        dlg.exec_()
