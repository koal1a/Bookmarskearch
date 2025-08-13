
import os
import time
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, 
    QTreeWidget, QTreeWidgetItem, QMenu, QSizePolicy, QDialog, QPlainTextEdit, QDialogButtonBox, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon
import webbrowser
from core import actions, settings, favicon_manager
from .dialogs import EditUrlDialog, UrlGroupManageDialog


class FaviconFetcher(QThread):
    favicon_ready = pyqtSignal(str, str)

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._is_running = True

    def run(self):
        # Create a copy of the items to avoid issues with concurrent modification
        urls_to_fetch = list(self.state.saved_urls.items())
        for url, data in urls_to_fetch:
            if not self._is_running:
                break

            favicon_path = data.get("favicon_path")
            if favicon_path and os.path.exists(favicon_path):
                # If path exists, emit it so the UI can update
                self.favicon_ready.emit(url, favicon_path)
                continue

            new_icon_path = favicon_manager.get_favicon(url)
            if new_icon_path:
                self.favicon_ready.emit(url, new_icon_path)

            time.sleep(0.1) # Be a good citizen

    def stop(self):
        self._is_running = False

class RightPanel(QFrame):
    def __init__(self, state, main_window):
        super().__init__()
        self.state = state
        self.main_window = main_window
        self.setFrameShape(QFrame.Box)
        self.init_ui()
        self.start_favicon_fetcher()

    def stop_threads(self):
        if hasattr(self, 'favicon_fetcher') and self.favicon_fetcher.isRunning():
            self.favicon_fetcher.stop()
            self.favicon_fetcher.wait()

    def on_favicon_ready(self, url, icon_path):
        if url in self.state.saved_urls:
            self.state.saved_urls[url]['favicon_path'] = icon_path
            self.update_url_list_item(url, icon_path)

    def start_favicon_fetcher(self):
        self.favicon_fetcher = FaviconFetcher(self.state)
        self.favicon_fetcher.favicon_ready.connect(self.on_favicon_ready)
        self.favicon_fetcher.start()

    def init_ui(self):
        if self.layout() is not None:
            # Clear existing widgets
            while self.layout().count():
                item = self.layout().takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        else:
            layout = QVBoxLayout()
            self.setLayout(layout)

        layout = self.layout()

        desc_label = QLabel("💻 사이트")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font_size = settings.get_font_size()
        desc_label.setStyleSheet(f"font-weight: bold; font-size: {font_size+6}pt; padding-bottom: 10px; border-bottom: 1px solid #3a3f4b;") # 헤더 스타일
        layout.addWidget(desc_label)

        url_add_layout = QVBoxLayout()
        url_label = QLabel("아래에 입력하는 URL을 추가합니다")
        url_add_layout.addWidget(url_label)
        additional_label = QLabel("URL추가형식:https://www.google.com/search?q=")
        url_add_layout.addWidget(additional_label)
        
        url_input_hbox = QHBoxLayout()
        self.url_entry = QLineEdit()
        self.url_entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        url_input_hbox.addWidget(self.url_entry)
        url_button = QPushButton("URL를 저장합니다")
        url_button.setFixedHeight(30)
        url_button.setFixedHeight(30)
        url_button.clicked.connect(self.save_url)
        url_add_layout.addWidget(url_button)
        layout.addLayout(url_add_layout)

        saved_url_label = QLabel("저장된 URL입니다:")
        
        url_list_header_hbox = QHBoxLayout()
        url_list_header_hbox.addWidget(saved_url_label)
        open_all_url_btn = QPushButton("전체 열기")
        close_all_url_btn = QPushButton("전체 닫기")
        open_all_url_btn.setFixedHeight(25)
        close_all_url_btn.setFixedHeight(25)
        open_all_url_btn.setStyleSheet(f"font-size: {font_size-2}pt;")
        close_all_url_btn.setStyleSheet(f"font-size: {font_size-2}pt;")
        open_all_url_btn.clicked.connect(self.expand_all_url_tree)
        close_all_url_btn.clicked.connect(self.collapse_all_url_tree)
        url_list_header_hbox.addWidget(open_all_url_btn)
        url_list_header_hbox.addWidget(close_all_url_btn)

        self.preset_buttons = []
        for i in range(1, 5):
            btn = QPushButton(str(i))
            btn.setFixedSize(25, 25)
            btn.clicked.connect(lambda _, num=i: self.load_preset(num))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, num=i: self.show_preset_context_menu(pos, num, btn))
            url_list_header_hbox.addWidget(btn)
            self.preset_buttons.append(btn)

        url_list_header_hbox.addStretch()
        layout.addLayout(url_list_header_hbox)

        self.url_list = QTreeWidget()
        self.url_list.setHeaderLabels(["이름", "URL", "메모", "활성화"])
        self.url_list.setColumnHidden(1, True)
        self.url_list.setColumnHidden(3, True)
        self.url_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.url_list.customContextMenuRequested.connect(self.show_url_context_menu)
        self.url_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.url_list.itemChanged.connect(self.url_item_check_changed)
        self.url_list.itemDoubleClicked.connect(self.open_url_from_list) # 더블클릭 시그널 연결
        layout.addWidget(self.url_list)

        preset_hbox = QHBoxLayout()
        self.preset_buttons = []
        presets = self.state.get_url_check_presets()
        for i in range(1, 5):
            preset_data = presets.get(str(i), {})
            name = preset_data.get("name", str(i))
            btn = QPushButton(name)
            btn.setFixedSize(100, 25)
            if preset_data:
                btn.setStyleSheet("background-color: #61afef; color: #282c34;")
            btn.clicked.connect(lambda _, num=i: self.load_preset(num))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, num=i, b=btn: self.show_preset_context_menu(pos, num, b))
            preset_hbox.addWidget(btn)
            self.preset_buttons.append(btn)
        layout.addLayout(preset_hbox)

        btn_hbox = QHBoxLayout()
        uncheck_all_button = QPushButton("전체 체크 해제")
        uncheck_all_button.setFixedHeight(30)
        uncheck_all_button.clicked.connect(self.uncheck_all_urls)
        btn_hbox.addWidget(uncheck_all_button)
        edit_all_url_btn = QPushButton("전체 URL 편집")
        edit_all_url_btn.setFixedHeight(30)
        edit_all_url_btn.clicked.connect(self.edit_all_urls_dialog)
        btn_hbox.addWidget(edit_all_url_btn)
        layout.addLayout(btn_hbox)

        url_group_manage_btn = QPushButton("URL 그룹 관리")
        url_group_manage_btn.setFixedHeight(30)
        url_group_manage_btn.clicked.connect(self.url_group_manage_dialog)
        layout.addWidget(url_group_manage_btn)

        self.setLayout(layout)
        self.update_url_list()

        # URL 리스트 컬럼 폭 복원
        url_col_widths = self.state.get_config_key("url_list_col_widths", None)
        url_header = self.url_list.header()
        if url_col_widths and url_header is not None:
            for i, w in enumerate(url_col_widths):
                try:
                    url_header.resizeSection(i, w)
                except Exception:
                    pass
        
        # URL 리스트 컬럼 폭 변경 감지 연결
        if url_header is not None:
            url_header.sectionResized.connect(self.save_url_list_col_widths)

    def show_preset_context_menu(self, position, preset_num, button):
        menu = QMenu()
        save_action = menu.addAction("현재 체크 상태 저장")
        rename_action = menu.addAction("이름 바꾸기")
        delete_action = menu.addAction("프리셋 삭제")
        save_action.triggered.connect(lambda: self.save_preset(preset_num))
        rename_action.triggered.connect(lambda: self.rename_preset(preset_num, button))
        delete_action.triggered.connect(lambda: self.delete_preset(preset_num, button))
        menu.exec_(button.mapToGlobal(position))

    def save_preset(self, preset_num):
        presets = self.state.get_url_check_presets()
        checked_urls = []
        root = self.url_list.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    checked_urls.append(child.text(1))
        preset_data = presets.get(str(preset_num), {})
        preset_data["urls"] = checked_urls
        presets[str(preset_num)] = preset_data
        self.state.save_url_check_presets(presets)
        self.preset_buttons[preset_num-1].setStyleSheet("background-color: #61afef; color: #282c34;")

    def load_preset(self, preset_num):
        presets = self.state.get_url_check_presets()
        preset_data = presets.get(str(preset_num))
        if preset_data and "urls" in preset_data:
            preset_urls = preset_data["urls"]
            root = self.url_list.invisibleRootItem()
            for i in range(root.childCount()):
                group_item = root.child(i)
                for j in range(group_item.childCount()):
                    child = group_item.child(j)
                    url = child.text(1)
                    if url in preset_urls:
                        child.setCheckState(0, Qt.Checked)
                    else:
                        child.setCheckState(0, Qt.Unchecked)

    def delete_preset(self, preset_num, button):
        presets = self.state.get_url_check_presets()
        if str(preset_num) in presets:
            del presets[str(preset_num)]
            self.state.save_url_check_presets(presets)
            button.setText(str(preset_num))
            button.setStyleSheet("")

    def rename_preset(self, preset_num, button):
        presets = self.state.get_url_check_presets()
        preset_data = presets.get(str(preset_num), {})
        current_name = preset_data.get("name", str(preset_num))
        new_name, ok = QInputDialog.getText(self, "이름 바꾸기", "새 이름을 입력하세요:", text=current_name)
        if ok and new_name:
            preset_data["name"] = new_name
            presets[str(preset_num)] = preset_data
            self.state.save_url_check_presets(presets)
            button.setText(new_name)

    def update_url_list_item(self, url, icon_path):
        root = self.url_list.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                if child.text(1) == url:
                    if os.path.exists(icon_path):
                        child.setIcon(0, QIcon(icon_path))
                    return

    def update_url_list(self):
        self.url_list.itemChanged.disconnect()
        self.url_list.clear()
        changed = False
        for data in self.state.saved_urls.values():
            if 'group' not in data:
                data['group'] = '기본'
                changed = True
        if changed:
            self.state.save_saved_urls()

        grouped = {}
        for url, data in self.state.saved_urls.items():
            group = data.get('group', '기본')
            grouped.setdefault(group, []).append((url, data))
        
        font_size = settings.get_font_size()
        for group, items in grouped.items():
            group_item = QTreeWidgetItem([group])
            group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable) # 그룹 항목 선택 불가
            group_item.setBackground(0, QColor("#3a3f4b")) # 그룹 배경색
            group_item.setForeground(0, QColor("#61afef")) # 그룹 글자색
            group_item.setFont(0, QFont("Segoe UI", font_size, QFont.Bold)) # 그룹 폰트
            for url, data in items:
                name = data.get('name', '')
                note = data.get('note', '')
                active = data.get('active', True)
                child = QTreeWidgetItem([name, url, note, "O" if active else "X"])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked if active else Qt.CheckState.Unchecked)

                favicon_path = data.get('favicon_path')
                if favicon_path and os.path.exists(favicon_path):
                    child.setIcon(0, QIcon(favicon_path))

                group_item.addChild(child)
            self.url_list.addTopLevelItem(group_item)
        self.url_list.itemChanged.connect(self.url_item_check_changed)
        QTimer.singleShot(0, self.restore_url_tree_expanded_state)
        QTimer.singleShot(0, self.restore_url_tree_expanded_state)

    def save_url(self):
        url = self.url_entry.text().strip()
        actions.save_url(self.state, url)
        self.update_url_list()
        self.url_entry.clear()

    def show_url_context_menu(self, position):
        menu = QMenu()
        selected_item = self.url_list.itemAt(position)
        if selected_item and selected_item.parent(): # 그룹 아이템 제외
            edit_action = menu.addAction("수정")
            delete_action = menu.addAction("삭제")
            refetch_icon_action = menu.addAction("아이콘 새로고침")
            edit_action.triggered.connect(lambda: self.edit_url_item(selected_item))
            delete_action.triggered.connect(lambda: self.delete_url_item(selected_item))
            refetch_icon_action.triggered.connect(lambda: self.refetch_icon(selected_item))

        edit_all_action = menu.addAction("전체 URL 편집")
        edit_all_action.triggered.connect(self.edit_all_urls_dialog)
        
        viewport = self.url_list.viewport()
        if viewport:
            menu.exec_(viewport.mapToGlobal(position))

    def refetch_icon(self, item):
        url = item.text(1)
        if url in self.state.saved_urls:
            # Remove old icon path and clear the icon in the UI
            self.state.saved_urls[url].pop('favicon_path', None)
            item.setIcon(0, QIcon()) # Clear icon
            # Restart the fetcher to get the new icon
            # A more targeted fetch would be better, but this is simpler
            self.stop_threads()
            self.start_favicon_fetcher()

    def edit_url_item(self, item):
        url_to_edit = item.text(1)
        if url_to_edit in self.state.saved_urls:
            data = self.state.saved_urls[url_to_edit]
            dlg = EditUrlDialog(url_to_edit, data["name"], data.get("note", ""), data.get("group", "기본"), self.state.url_groups, self)
            if dlg.exec_():
                new_url, new_name, new_note, new_group = dlg.get_values()
                if new_url != url_to_edit:
                    self.state.saved_urls[new_url] = self.state.saved_urls.pop(url_to_edit)
                self.state.saved_urls[new_url]["name"] = new_name
                self.state.saved_urls[new_url]["note"] = new_note
                self.state.saved_urls[new_url]["group"] = new_group
                self.state.save_saved_urls()
                self.update_url_list()

    def delete_url_item(self, item):
        url = item.text(1)
        actions.delete_url_item(self.state, url)
        self.update_url_list()

    def uncheck_all_urls(self):
        actions.uncheck_all_urls(self.state)
        self.update_url_list()

    def url_item_check_changed(self, item, column):
        if column == 0 and item.parent():
            url = item.text(1)
            is_checked = item.checkState(0) == Qt.CheckState.Checked
            actions.toggle_url_state(self.state, url, is_checked)

    def edit_all_urls_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("전체 URL 편집")
        dlg.resize(500, 500)
        layout = QVBoxLayout()
        edit = QPlainTextEdit()
        url_lines = [f"{url}|{data['name']}|{data.get('note','')}|{data.get('group','기본')}" for url, data in self.state.saved_urls.items()]
        edit.setPlainText("\n".join(url_lines))
        layout.addWidget(edit)
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)
        dlg.setLayout(layout)
        def save_urls():
            lines = edit.toPlainText().splitlines()
            new_urls = {}
            for line in lines:
                parts = line.strip().split('|')
                if len(parts) >= 1 and parts[0]:
                    url = parts[0]
                    # Get existing data or create a new dictionary
                    data = self.state.saved_urls.get(url, {"active": True, "favicon_path": None})

                    # Update data from the line parts
                    data['name'] = parts[1] if len(parts) > 1 and parts[1] else url.split('//')[-1].split('/')[0]
                    data['note'] = parts[2] if len(parts) > 2 else ''
                    data['group'] = parts[3] if len(parts) > 3 and parts[3] else '기본'

                    new_urls[url] = data
            self.state.saved_urls = new_urls
            self.state.save_saved_urls()
            self.update_url_list()
            dlg.accept()
        btn_box.accepted.connect(save_urls)
        btn_box.rejected.connect(dlg.reject)
        dlg.exec_()

    def url_group_manage_dialog(self):
        dlg = UrlGroupManageDialog(self.state.url_groups, self)
        if dlg.exec_():
            self.state.url_groups = dlg.get_groups()
            self.state.save_url_groups()
            self.update_url_list()

    def save_url_list_col_widths(self, logicalIndex, oldSize, newSize):
        header = self.url_list.header()
        if header is not None:
            widths = [header.sectionSize(i) for i in range(header.count())]
            self.state.set_config_key("url_list_col_widths", widths)

    def open_url_from_list(self, item):
        # 그룹 아이템이 아닌 경우에만 동작
        if item.parent() is not None:
            url = item.text(1) # URL은 두 번째 컬럼에 있음
            if url:
                import webbrowser
                webbrowser.open(url)

    def expand_all_url_tree(self):
        self.url_list.expandAll()
        self.save_url_tree_expanded_state()

    def collapse_all_url_tree(self):
        self.url_list.collapseAll()
        self.save_url_tree_expanded_state()

    def get_url_item_path(self, item):
        path = []
        while item is not None and item.parent() is not None:
            path.insert(0, item.text(1) if item.text(1) else item.text(0))
            item = item.parent()
        if item is not None:
            path.insert(0, item.text(0))
        return "/".join(path)

    def save_url_tree_expanded_state(self):
        expanded = []
        def recurse(item):
            if item is None: return
            for i in range(item.childCount()):
                child = item.child(i)
                if child and child.isExpanded():
                    expanded.append(self.get_url_item_path(child))
                recurse(child)
        root = self.url_list.invisibleRootItem()
        if root:
            for i in range(root.childCount()):
                group = root.child(i)
                if group and group.isExpanded():
                    expanded.append(self.get_url_item_path(group))
                recurse(group)
        self.state.set_config_key("url_tree_expanded", expanded)

    def find_url_item_by_path(self, path):
        parts = path.split("/")
        root = self.url_list.invisibleRootItem()
        def find_recursive(parent, parts):
            if not parts: return parent
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child and (child.text(1) == parts[0] or child.text(0) == parts[0]):
                    return find_recursive(child, parts[1:])
            return None
        return find_recursive(root, parts)

    def restore_url_tree_expanded_state(self):
        expanded = self.state.get_config_key("url_tree_expanded", [])
        for path in expanded:
            item = self.find_url_item_by_path(path)
            if item:
                item.setExpanded(True)

    def expand_all_url_tree(self):
        self.url_list.expandAll()
        self.save_url_tree_expanded_state()

    def collapse_all_url_tree(self):
        self.url_list.collapseAll()
        self.save_url_tree_expanded_state()

    def get_url_item_path(self, item):
        path = []
        while item is not None and item.parent() is not None:
            path.insert(0, item.text(1) if item.text(1) else item.text(0))
            item = item.parent()
        if item is not None:
            path.insert(0, item.text(0))
        return "/".join(path)

    def save_url_tree_expanded_state(self):
        expanded = []
        def recurse(item):
            if item is None: return
            for i in range(item.childCount()):
                child = item.child(i)
                if child and child.isExpanded():
                    expanded.append(self.get_url_item_path(child))
                recurse(child)
        root = self.url_list.invisibleRootItem()
        if root:
            for i in range(root.childCount()):
                group = root.child(i)
                if group and group.isExpanded():
                    expanded.append(self.get_url_item_path(group))
                recurse(group)
        self.state.set_config_key("url_tree_expanded", expanded)

    def find_url_item_by_path(self, path):
        parts = path.split("/")
        root = self.url_list.invisibleRootItem()
        def find_recursive(parent, parts):
            if not parts: return parent
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child and (child.text(1) == parts[0] or child.text(0) == parts[0]):
                    return find_recursive(child, parts[1:])
            return None
        return find_recursive(root, parts)

    def restore_url_tree_expanded_state(self):
        expanded = self.state.get_config_key("url_tree_expanded", [])
        for path in expanded:
            item = self.find_url_item_by_path(path)
            if item:
                item.setExpanded(True)

    def expand_all_url_tree(self):
        self.url_list.expandAll()
        self.save_url_tree_expanded_state()

    def collapse_all_url_tree(self):
        self.url_list.collapseAll()
        self.save_url_tree_expanded_state()

    def get_url_item_path(self, item):
        path = []
        while item is not None and item.parent() is not None:
            path.insert(0, item.text(1) if item.text(1) else item.text(0))
            item = item.parent()
        if item is not None:
            path.insert(0, item.text(0))
        return "/".join(path)

    def save_url_tree_expanded_state(self):
        expanded = []
        def recurse(item):
            if item is None: return
            for i in range(item.childCount()):
                child = item.child(i)
                if child and child.isExpanded():
                    expanded.append(self.get_url_item_path(child))
                recurse(child)
        root = self.url_list.invisibleRootItem()
        if root:
            for i in range(root.childCount()):
                group = root.child(i)
                if group and group.isExpanded():
                    expanded.append(self.get_url_item_path(group))
                recurse(group)
        self.state.set_config_key("url_tree_expanded", expanded)

    def find_url_item_by_path(self, path):
        parts = path.split("/")
        root = self.url_list.invisibleRootItem()
        def find_recursive(parent, parts):
            if not parts: return parent
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child and (child.text(1) == parts[0] or child.text(0) == parts[0]):
                    return find_recursive(child, parts[1:])
            return None
        return find_recursive(root, parts)

    def restore_url_tree_expanded_state(self):
        expanded = self.state.get_config_key("url_tree_expanded", [])
        for path in expanded:
            item = self.find_url_item_by_path(path)
            if item:
                item.setExpanded(True)

    def expand_all_url_tree(self):
        self.url_list.expandAll()
        self.save_url_tree_expanded_state()

    def collapse_all_url_tree(self):
        self.url_list.collapseAll()
        self.save_url_tree_expanded_state()

    def get_url_item_path(self, item):
        path = []
        while item is not None and item.parent() is not None:
            path.insert(0, item.text(1) if item.text(1) else item.text(0))
            item = item.parent()
        if item is not None:
            path.insert(0, item.text(0))
        return "/".join(path)

    def save_url_tree_expanded_state(self):
        expanded = []
        def recurse(item):
            if item is None: return
            for i in range(item.childCount()):
                child = item.child(i)
                if child and child.isExpanded():
                    expanded.append(self.get_url_item_path(child))
                recurse(child)
        root = self.url_list.invisibleRootItem()
        if root:
            for i in range(root.childCount()):
                group = root.child(i)
                if group and group.isExpanded():
                    expanded.append(self.get_url_item_path(group))
                recurse(group)
        self.state.set_config_key("url_tree_expanded", expanded)

    def find_url_item_by_path(self, path):
        parts = path.split("/")
        root = self.url_list.invisibleRootItem()
        def find_recursive(parent, parts):
            if not parts: return parent
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child and (child.text(1) == parts[0] or child.text(0) == parts[0]):
                    return find_recursive(child, parts[1:])
            return None
        return find_recursive(root, parts)

    def restore_url_tree_expanded_state(self):
        expanded = self.state.get_config_key("url_tree_expanded", [])
        for path in expanded:
            item = self.find_url_item_by_path(path)
            if item:
                item.setExpanded(True)

    def expand_all_url_tree(self):
        self.url_list.expandAll()
        self.save_url_tree_expanded_state()

    def collapse_all_url_tree(self):
        self.url_list.collapseAll()
        self.save_url_tree_expanded_state()

    def get_url_item_path(self, item):
        path = []
        while item is not None and item.parent() is not None:
            path.insert(0, item.text(1) if item.text(1) else item.text(0))
            item = item.parent()
        if item is not None:
            path.insert(0, item.text(0))
        return "/".join(path)

    def save_url_tree_expanded_state(self):
        expanded = []
        def recurse(item):
            if item is None: return
            for i in range(item.childCount()):
                child = item.child(i)
                if child and child.isExpanded():
                    expanded.append(self.get_url_item_path(child))
                recurse(child)
        root = self.url_list.invisibleRootItem()
        if root:
            for i in range(root.childCount()):
                group = root.child(i)
                if group and group.isExpanded():
                    expanded.append(self.get_url_item_path(group))
                recurse(group)
        self.state.set_config_key("url_tree_expanded", expanded)

    def find_url_item_by_path(self, path):
        parts = path.split("/")
        root = self.url_list.invisibleRootItem()
        def find_recursive(parent, parts):
            if not parts: return parent
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child and (child.text(1) == parts[0] or child.text(0) == parts[0]):
                    return find_recursive(child, parts[1:])
            return None
        return find_recursive(root, parts)

    def restore_url_tree_expanded_state(self):
        expanded = self.state.get_config_key("url_tree_expanded", [])
        for path in expanded:
            item = self.find_url_item_by_path(path)
            if item:
                item.setExpanded(True)

    def expand_all_url_tree(self):
        self.url_list.expandAll()
        self.save_url_tree_expanded_state()

    def collapse_all_url_tree(self):
        self.url_list.collapseAll()
        self.save_url_tree_expanded_state()

    def get_url_item_path(self, item):
        path = []
        while item is not None and item.parent() is not None:
            path.insert(0, item.text(1) if item.text(1) else item.text(0))
            item = item.parent()
        if item is not None:
            path.insert(0, item.text(0))
        return "/".join(path)

    def save_url_tree_expanded_state(self):
        expanded = []
        def recurse(item):
            if item is None: return
            for i in range(item.childCount()):
                child = item.child(i)
                if child and child.isExpanded():
                    expanded.append(self.get_url_item_path(child))
                recurse(child)
        root = self.url_list.invisibleRootItem()
        if root:
            for i in range(root.childCount()):
                group = root.child(i)
                if group and group.isExpanded():
                    expanded.append(self.get_url_item_path(group))
                recurse(group)
        self.state.set_config_key("url_tree_expanded", expanded)

    def find_url_item_by_path(self, path):
        parts = path.split("/")
        root = self.url_list.invisibleRootItem()
        def find_recursive(parent, parts):
            if not parts: return parent
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child and (child.text(1) == parts[0] or child.text(0) == parts[0]):
                    return find_recursive(child, parts[1:])
            return None
        return find_recursive(root, parts)

    def restore_url_tree_expanded_state(self):
        expanded = self.state.get_config_key("url_tree_expanded", [])
        for path in expanded:
            item = self.find_url_item_by_path(path)
            if item:
                item.setExpanded(True)
