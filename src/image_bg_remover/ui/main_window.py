from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from image_bg_remover.config import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_MODELS
from image_bg_remover.masking import build_dummy_mask, build_mask_overlay
from image_bg_remover.state import AppState, ImageViewportMapping
from image_bg_remover.ui.image_preview import ImagePreviewWidget


class ResultPreviewPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._has_content = False
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_has_content(self, has_content: bool) -> None:
        self._has_content = has_content
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            rect = self.rect().adjusted(1, 1, -1, -1)
            painter.fillRect(rect, QColor("#fffdf8"))
            painter.setPen(QColor("#d9cdbb"))
            painter.drawRoundedRect(rect, 18, 18)

            body_rect = rect.adjusted(18, 18, -18, -18)
            painter.setPen(QColor("#7b8794"))
            text = "結果プレビューはフェーズ7で表示します" if not self._has_content else "State connected"
            painter.drawText(body_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
        finally:
            if painter.isActive():
                painter.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()
        self.available_model_keys = {model.key for model in SUPPORTED_MODELS if model.checkpoint_path.exists()}
        self.state.selected_model_key = next(iter(self.available_model_keys), None)

        self.setWindowTitle("Image BG Remover")
        self.resize(1400, 900)
        self.setMinimumSize(920, 620)

        self._build_ui()
        self._populate_models()
        self._sync_ui()
        self._apply_styles()
        self.statusBar().showMessage("Phase 5 mask state ready")

    def _build_ui(self) -> None:
        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("windowScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget(scroll_area)
        scroll_content.setObjectName("scrollContent")
        root_layout = QHBoxLayout(scroll_content)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(20)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(18)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        input_group = QGroupBox("Input Image", scroll_content)
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(14, 20, 14, 14)
        input_layout.setSpacing(10)

        self.input_preview = ImagePreviewWidget(
            placeholder_text="[画像読込] から jpg/png を1枚選択すると、ここに原画像を表示します。",
            parent=input_group,
        )
        self.input_preview.setMinimumHeight(360)
        self.input_preview.mapping_changed.connect(self._handle_mapping_changed)
        self.input_preview.interaction_requested.connect(self._handle_preview_interaction)

        self.image_info_label = QLabel("画像未読込", input_group)
        self.image_info_label.setObjectName("metaLabel")
        self.image_info_label.setWordWrap(True)

        input_layout.addWidget(self.input_preview)
        input_layout.addWidget(self.image_info_label)

        result_group = QGroupBox("Background Removed Preview", scroll_content)
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(14, 20, 14, 14)
        result_layout.setSpacing(10)

        self.result_preview = ResultPreviewPanel(result_group)
        self.result_info_label = QLabel("背景削除結果は未生成です", result_group)
        self.result_info_label.setObjectName("metaLabel")

        result_layout.addWidget(self.result_preview)
        result_layout.addWidget(self.result_info_label)

        content_layout.addWidget(input_group, stretch=4)
        content_layout.addWidget(result_group, stretch=2)

        sidebar = self._build_sidebar()

        root_layout.addLayout(content_layout, stretch=4)
        root_layout.addWidget(sidebar, stretch=0, alignment=Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(scroll_content)
        self.setCentralWidget(scroll_area)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame(self)
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(320)
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Control Panel", sidebar)
        title.setObjectName("sidebarTitle")

        self.load_button = QPushButton("画像読込", sidebar)
        self.load_button.clicked.connect(self._handle_load_image)

        instruction = QLabel(
            "左クリックで前景、右クリックで背景、中クリックでポイントを削除します",
            sidebar,
        )
        instruction.setObjectName("instructionLabel")
        instruction.setWordWrap(True)

        self.reset_button = QPushButton("リセット", sidebar)
        self.reset_button.clicked.connect(self._handle_reset)

        action_group = QGroupBox("Actions", sidebar)
        action_layout = QVBoxLayout(action_group)
        action_layout.setSpacing(10)

        self.create_mask_button = QPushButton("マスク作成", action_group)
        self.create_mask_button.clicked.connect(self._handle_create_mask)
        self.remove_background_button = QPushButton("背景を削除", action_group)
        self.remove_background_button.clicked.connect(self._handle_remove_background)
        self.save_result_button = QPushButton("結果を保存", action_group)
        self.save_result_button.clicked.connect(self._handle_save_result)

        action_layout.addWidget(self.create_mask_button)
        action_layout.addWidget(self.remove_background_button)
        action_layout.addWidget(self.save_result_button)

        model_group = QGroupBox("Model", sidebar)
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(10)

        self.model_combo = QComboBox(model_group)
        self.model_combo.currentIndexChanged.connect(self._handle_model_changed)
        self.manage_models_button = QPushButton("モデル管理", model_group)
        self.manage_models_button.clicked.connect(self._handle_manage_models)

        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.manage_models_button)

        status_group = QGroupBox("State", sidebar)
        status_layout = QGridLayout(status_group)
        status_layout.setHorizontalSpacing(12)
        status_layout.setVerticalSpacing(8)

        self.image_state_value = QLabel(status_group)
        self.mask_state_value = QLabel(status_group)
        self.result_state_value = QLabel(status_group)
        self.mapping_state_value = QLabel(status_group)
        self.foreground_count_value = QLabel(status_group)
        self.background_count_value = QLabel(status_group)
        self.mask_data_value = QLabel(status_group)

        status_layout.addWidget(QLabel("画像", status_group), 0, 0)
        status_layout.addWidget(self.image_state_value, 0, 1)
        status_layout.addWidget(QLabel("マスク", status_group), 1, 0)
        status_layout.addWidget(self.mask_state_value, 1, 1)
        status_layout.addWidget(QLabel("保存対象", status_group), 2, 0)
        status_layout.addWidget(self.result_state_value, 2, 1)
        status_layout.addWidget(QLabel("座標変換", status_group), 3, 0)
        status_layout.addWidget(self.mapping_state_value, 3, 1)
        status_layout.addWidget(QLabel("前景点", status_group), 4, 0)
        status_layout.addWidget(self.foreground_count_value, 4, 1)
        status_layout.addWidget(QLabel("背景点", status_group), 5, 0)
        status_layout.addWidget(self.background_count_value, 5, 1)
        status_layout.addWidget(QLabel("マスク画像", status_group), 6, 0)
        status_layout.addWidget(self.mask_data_value, 6, 1)

        layout.addWidget(title)
        layout.addWidget(self.load_button)
        layout.addWidget(instruction)
        layout.addWidget(self.reset_button)
        layout.addWidget(action_group)
        layout.addWidget(model_group)
        layout.addWidget(status_group)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        return sidebar

    def _populate_models(self) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        model_view = self.model_combo.model()
        for row, model in enumerate(SUPPORTED_MODELS):
            self.model_combo.addItem(model.label, model.key)
            item = model_view.item(row)
            if model.key not in self.available_model_keys:
                item.setEnabled(False)
                item.setToolTip("モデルファイルが未配置です")

        if self.state.selected_model_key is not None:
            index = self.model_combo.findData(self.state.selected_model_key)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        elif self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)

        self.model_combo.blockSignals(False)

    def _handle_load_image(self) -> None:
        file_filter = "Images (*.jpg *.jpeg *.png)"
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "画像を選択",
            str(Path.home()),
            file_filter,
        )
        if not selected_file:
            return

        image_path = Path(selected_file)
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            QMessageBox.warning(self, "非対応形式", "jpg/jpeg/png のみ対応しています。")
            return

        image = QImage(str(image_path))
        if image.isNull():
            QMessageBox.warning(self, "読込失敗", "画像を読み込めませんでした。")
            return

        self.state.set_image(image_path, image)
        self.input_preview.set_image(image)
        self.input_preview.set_mask_overlay(None)
        self.input_preview.set_points(self.state.foreground_points, self.state.background_points)
        self._sync_ui()
        self.statusBar().showMessage(f"画像を読み込みました: {image_path.name}")

    def _handle_reset(self) -> None:
        self.state.full_reset()
        self.input_preview.set_image(None)
        self.input_preview.set_mask_overlay(None)
        self.input_preview.set_points([], [])
        self._sync_ui()
        self.statusBar().showMessage("状態をリセットしました")

    def _handle_create_mask(self) -> None:
        if not self.state.image_loaded or self.state.source_image is None:
            return
        if not self.state.foreground_points and not self.state.background_points:
            QMessageBox.information(self, "マスク作成", "先に前景点または背景点を追加してください。")
            return

        mask = build_dummy_mask(self.state.source_image, self.state.foreground_points, self.state.background_points)
        overlay = build_mask_overlay(mask)
        self.state.set_mask(mask, overlay)
        self.input_preview.set_mask_overlay(overlay)
        self._sync_ui()
        self.statusBar().showMessage("ダミーマスクを作成しました")

    def _handle_remove_background(self) -> None:
        if not self.state.mask_created:
            return
        self.statusBar().showMessage("背景削除処理はフェーズ7で実装します")

    def _handle_save_result(self) -> None:
        if not self.state.background_removed:
            return
        self.statusBar().showMessage("保存処理はフェーズ8で実装します")

    def _handle_manage_models(self) -> None:
        available = ", ".join(sorted(self.available_model_keys)) or "なし"
        QMessageBox.information(
            self,
            "モデル管理",
            f"利用可能モデル: {available}\nダウンロード UI はフェーズ9で実装します。",
        )

    def _handle_model_changed(self, index: int) -> None:
        if index < 0:
            self.state.selected_model_key = None
            return
        self.state.selected_model_key = self.model_combo.itemData(index)
        self.statusBar().showMessage(f"モデル選択: {self.model_combo.currentText()}")

    def _handle_mapping_changed(self, mapping: ImageViewportMapping | None) -> None:
        self.state.image_mapping = mapping
        self._sync_ui()

    def _handle_preview_interaction(self, button, image_x: float, image_y: float, delete_threshold: float) -> None:
        if not self.state.image_loaded:
            return

        if button == Qt.MouseButton.LeftButton:
            self.state.add_point(image_x, image_y, "positive")
            self.statusBar().showMessage(f"前景点を追加しました: ({image_x:.0f}, {image_y:.0f})")
        elif button == Qt.MouseButton.RightButton:
            self.state.add_point(image_x, image_y, "negative")
            self.statusBar().showMessage(f"背景点を追加しました: ({image_x:.0f}, {image_y:.0f})")
        elif button == Qt.MouseButton.MiddleButton:
            removed = self.state.remove_nearest_point(image_x, image_y, delete_threshold)
            if removed is None:
                self.statusBar().showMessage("削除対象のポイントが見つかりません")
            else:
                point_kind = "前景点" if removed.kind == "positive" else "背景点"
                self.statusBar().showMessage(f"{point_kind}を削除しました: ({removed.x:.0f}, {removed.y:.0f})")
        else:
            return

        self.input_preview.set_mask_overlay(self.state.mask_overlay)
        self.input_preview.set_points(self.state.foreground_points, self.state.background_points)
        self._sync_ui()

    def _sync_ui(self) -> None:
        has_image = self.state.image_loaded and self.state.source_image is not None
        has_mask = self.state.mask_created and self.state.current_mask is not None
        has_result = self.state.background_removed and self.state.background_removed_image is not None
        has_mapping = self.state.image_mapping is not None

        self.reset_button.setEnabled(has_image or has_mask or has_result)
        self.create_mask_button.setEnabled(has_image)
        self.remove_background_button.setEnabled(has_mask)
        self.save_result_button.setEnabled(has_result)

        self.image_state_value.setText("読込済み" if has_image else "未読込")
        self.mask_state_value.setText("作成済み" if has_mask else "未作成")
        self.result_state_value.setText("保存可能" if has_result else "未生成")
        self.mapping_state_value.setText("保持中" if has_mapping else "未計算")
        self.foreground_count_value.setText(str(len(self.state.foreground_points)))
        self.background_count_value.setText(str(len(self.state.background_points)))
        self.mask_data_value.setText("あり" if self.state.current_mask is not None else "なし")

        self.result_preview.set_has_content(has_result)

        if has_image and self.state.source_image is not None and self.state.image_path is not None:
            source = self.state.source_image
            info_lines = [
                f"ファイル: {self.state.image_path.name}",
                f"原画像サイズ: {source.width()} x {source.height()}",
                f"前景点: {len(self.state.foreground_points)} / 背景点: {len(self.state.background_points)}",
            ]
            if self.state.image_mapping is not None:
                mapping = self.state.image_mapping
                info_lines.append(f"表示サイズ: {mapping.display_width:.0f} x {mapping.display_height:.0f}")
                info_lines.append(f"表示オフセット: ({mapping.display_x:.0f}, {mapping.display_y:.0f})")
            if self.state.current_mask is not None:
                info_lines.append(f"マスクサイズ: {self.state.current_mask.width()} x {self.state.current_mask.height()}")
            self.image_info_label.setText("\n".join(info_lines))
        else:
            self.image_info_label.setText("画像未読込")

        if has_mask:
            self.result_info_label.setText("ダミーマスクを保持中です。背景削除はフェーズ7で接続します")
        elif has_result:
            self.result_info_label.setText("保存可能な結果があります")
        else:
            self.result_info_label.setText("背景削除結果は未生成です")

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f1ece2;
            }
            QScrollArea#windowScrollArea {
                border: none;
                background: #f1ece2;
            }
            QWidget#scrollContent {
                background: #f1ece2;
            }
            QFrame#sidebar {
                background: #fffaf1;
                border: 1px solid #e5dccd;
                border-radius: 20px;
            }
            QLabel {
                color: #334e68;
                font-size: 14px;
            }
            QLabel#sidebarTitle {
                color: #102a43;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#instructionLabel, QLabel#metaLabel {
                color: #486581;
                background: #f7f1e6;
                border: 1px solid #eadfce;
                border-radius: 14px;
                padding: 12px;
            }
            QGroupBox {
                color: #243b53;
                font-size: 13px;
                font-weight: 600;
                border: 1px solid #e6dccb;
                border-radius: 16px;
                margin-top: 10px;
                padding: 16px 12px 12px 12px;
                background: #fffdf9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QPushButton, QComboBox {
                min-height: 42px;
                border-radius: 12px;
                border: 1px solid #d9cdbb;
                padding: 8px 12px;
                background: #fffdf8;
                color: #102a43;
                font-size: 14px;
            }
            QPushButton:hover, QComboBox:hover {
                border: 1px solid #bfa98a;
                background: #fff6e8;
            }
            QPushButton:disabled {
                color: #9aa5b1;
                background: #f4efe6;
                border: 1px solid #e0d7ca;
            }
            QComboBox::drop-down {
                width: 28px;
                border: none;
            }
            QScrollBar:vertical {
                background: #efe7d9;
                width: 14px;
                margin: 8px 4px 8px 0;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background: #c9b59b;
                min-height: 32px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QStatusBar {
                background: #fffaf1;
                color: #486581;
            }
            """
        )
