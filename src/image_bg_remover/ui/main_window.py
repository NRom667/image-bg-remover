from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QThread, Qt, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPixmap
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
from image_bg_remover.inference import InferenceResult, SamInferenceEngine
from image_bg_remover.masking import apply_mask_to_image
from image_bg_remover.state import AppState, ImageViewportMapping
from image_bg_remover.ui.image_preview import ImagePreviewWidget


class ResultPreviewPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self._pixmap: QPixmap | None = None
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_image(self, image: QImage | None) -> None:
        self._image = image
        self._pixmap = QPixmap.fromImage(image) if image is not None else None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            rect = self.rect().adjusted(1, 1, -1, -1)
            painter.fillRect(rect, QColor("#fffdf8"))
            painter.setPen(QColor("#d9cdbb"))
            painter.drawRoundedRect(rect, 18, 18)

            body_rect = QRectF(rect.adjusted(18, 18, -18, -18))
            self._draw_checker_background(painter, body_rect)

            if self._pixmap is None:
                painter.setPen(QColor("#7b8794"))
                painter.drawText(body_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, "結果プレビューは未生成です")
                return

            scale = min(body_rect.width() / self._pixmap.width(), body_rect.height() / self._pixmap.height())
            display_width = self._pixmap.width() * scale
            display_height = self._pixmap.height() * scale
            display_x = body_rect.x() + (body_rect.width() - display_width) / 2
            display_y = body_rect.y() + (body_rect.height() - display_height) / 2
            target_rect = QRectF(display_x, display_y, display_width, display_height)
            painter.drawPixmap(target_rect, self._pixmap, QRectF(self._pixmap.rect()))
        finally:
            if painter.isActive():
                painter.end()

    def _draw_checker_background(self, painter: QPainter, rect: QRectF) -> None:
        tile = 14
        light = QColor("#fbf7ef")
        dark = QColor("#ede3d2")
        y = rect.top()
        row = 0
        while y < rect.bottom():
            x = rect.left()
            col = row
            while x < rect.right():
                painter.fillRect(QRectF(x, y, tile, tile), light if col % 2 == 0 else dark)
                x += tile
                col += 1
            y += tile
            row += 1


class InferenceWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._engine: SamInferenceEngine | None = None

    @Slot(str, object, object, object)
    def run_inference(self, model_key: str, source_image: QImage, foreground_points, background_points) -> None:
        try:
            if self._engine is None:
                self._engine = SamInferenceEngine()
            result = self._engine.predict_mask(
                model_key,
                source_image,
                list(foreground_points),
                list(background_points),
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class MainWindow(QMainWindow):
    inference_requested = Signal(str, object, object, object)

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()
        self.inference_running = False
        self.available_model_keys = {model.key for model in SUPPORTED_MODELS if model.checkpoint_path.exists()}
        self.state.selected_model_key = next(iter(self.available_model_keys), None)

        self.inference_thread = QThread(self)
        self.inference_worker = InferenceWorker()
        self.inference_worker.moveToThread(self.inference_thread)
        self.inference_requested.connect(self.inference_worker.run_inference)
        self.inference_worker.finished.connect(self._handle_inference_finished)
        self.inference_worker.failed.connect(self._handle_inference_failed)
        self.inference_thread.start()

        self.setWindowTitle("Image BG Remover")
        self.resize(1400, 900)
        self.setMinimumSize(920, 620)

        self._build_ui()
        self._populate_models()
        self._sync_ui()
        self._apply_styles()
        self.statusBar().showMessage("Phase 8 save ready")

    def closeEvent(self, event) -> None:  # noqa: N802
        self.inference_thread.quit()
        self.inference_thread.wait(3000)
        super().closeEvent(event)

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
        self.busy_value = QLabel(status_group)

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
        status_layout.addWidget(QLabel("処理中", status_group), 7, 0)
        status_layout.addWidget(self.busy_value, 7, 1)

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
        if self.inference_running:
            return

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
        self.result_preview.set_image(None)
        self._sync_ui()
        self.statusBar().showMessage(f"画像を読み込みました: {image_path.name}")

    def _handle_reset(self) -> None:
        if self.inference_running:
            return
        self.state.full_reset()
        self.input_preview.set_image(None)
        self.input_preview.set_mask_overlay(None)
        self.input_preview.set_points([], [])
        self.result_preview.set_image(None)
        self._sync_ui()
        self.statusBar().showMessage("状態をリセットしました")

    def _handle_create_mask(self) -> None:
        if self.inference_running:
            return
        if not self.state.image_loaded or self.state.source_image is None:
            return
        if self.state.selected_model_key is None:
            QMessageBox.warning(self, "モデル未選択", "利用可能なモデルを選択してください。")
            return
        if not self.state.foreground_points and not self.state.background_points:
            QMessageBox.information(self, "マスク作成", "先に前景点または背景点を追加してください。")
            return

        self._set_inference_running(True)
        self.statusBar().showMessage(f"{self.model_combo.currentText()} でマスクを作成中...")
        self.inference_requested.emit(
            self.state.selected_model_key,
            self.state.source_image.copy(),
            list(self.state.foreground_points),
            list(self.state.background_points),
        )

    def _handle_remove_background(self) -> None:
        if self.inference_running:
            return
        if self.state.current_mask is None or self.state.source_image is None:
            return

        result_image = apply_mask_to_image(self.state.source_image, self.state.current_mask)
        self.state.set_background_removed_image(result_image)
        self.result_preview.set_image(result_image)
        self._sync_ui()
        self.statusBar().showMessage("背景を削除しました")

    def _handle_save_result(self) -> None:
        if self.inference_running:
            return
        if self.state.background_removed_image is None:
            return

        default_path = self._build_default_save_path()
        selected_file, _ = QFileDialog.getSaveFileName(
            self,
            "結果を保存",
            str(default_path),
            "PNG Image (*.png)",
        )
        if not selected_file:
            return

        save_path = Path(selected_file)
        if save_path.suffix.lower() != ".png":
            save_path = save_path.with_suffix(".png")

        success = self.state.background_removed_image.save(str(save_path), "PNG")
        if not success:
            QMessageBox.critical(self, "保存失敗", "透過PNGの保存に失敗しました。")
            self.statusBar().showMessage("保存に失敗しました")
            return

        self.statusBar().showMessage(f"結果を保存しました: {save_path.name}")

    def _build_default_save_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.state.image_path is not None:
            base_dir = self.state.image_path.parent
            base_name = self.state.image_path.stem
        else:
            base_dir = Path.home()
            base_name = "result"
        return base_dir / f"{base_name}_{timestamp}.png"

    def _handle_manage_models(self) -> None:
        if self.inference_running:
            return
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
        if not self.state.image_loaded or self.inference_running:
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
        self.result_preview.set_image(self.state.background_removed_image)
        self._sync_ui()

    def _handle_inference_finished(self, result: InferenceResult) -> None:
        self.state.set_mask(result.mask, result.overlay)
        self.input_preview.set_mask_overlay(result.overlay)
        self.result_preview.set_image(self.state.background_removed_image)
        self._set_inference_running(False)
        self._sync_ui()
        self.statusBar().showMessage(f"マスクを作成しました: model={result.model_key}, score={result.score:.3f}")

    def _handle_inference_failed(self, message: str) -> None:
        self._set_inference_running(False)
        self._sync_ui()
        QMessageBox.critical(self, "マスク作成失敗", message)
        self.statusBar().showMessage("マスク作成に失敗しました")

    def _set_inference_running(self, running: bool) -> None:
        self.inference_running = running
        if running:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QGuiApplication.restoreOverrideCursor()
        self._sync_ui()

    def _sync_ui(self) -> None:
        has_image = self.state.image_loaded and self.state.source_image is not None
        has_mask = self.state.mask_created and self.state.current_mask is not None
        has_result = self.state.background_removed and self.state.background_removed_image is not None
        has_mapping = self.state.image_mapping is not None
        idle = not self.inference_running

        self.load_button.setEnabled(idle)
        self.reset_button.setEnabled(idle and (has_image or has_mask or has_result))
        self.create_mask_button.setEnabled(idle and has_image)
        self.remove_background_button.setEnabled(idle and has_mask)
        self.save_result_button.setEnabled(idle and has_result)
        self.model_combo.setEnabled(idle)
        self.manage_models_button.setEnabled(idle)

        self.image_state_value.setText("読込済み" if has_image else "未読込")
        self.mask_state_value.setText("作成済み" if has_mask else "未作成")
        self.result_state_value.setText("保存可能" if has_result else "未生成")
        self.mapping_state_value.setText("保持中" if has_mapping else "未計算")
        self.foreground_count_value.setText(str(len(self.state.foreground_points)))
        self.background_count_value.setText(str(len(self.state.background_points)))
        self.mask_data_value.setText("あり" if self.state.current_mask is not None else "なし")
        self.busy_value.setText("はい" if self.inference_running else "いいえ")

        self.result_preview.set_image(self.state.background_removed_image)

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

        if self.inference_running:
            self.result_info_label.setText("SAM2.1 でマスク作成中です")
        elif has_result and self.state.background_removed_image is not None:
            result = self.state.background_removed_image
            self.result_info_label.setText(f"背景削除結果: {result.width()} x {result.height()} の透過画像")
        elif has_mask:
            self.result_info_label.setText("SAM2.1 マスクを保持中です。[背景を削除] で透過画像を生成できます")
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
            QPushButton:disabled, QComboBox:disabled {
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
