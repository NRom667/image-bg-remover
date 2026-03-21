from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from image_bg_remover.ui.theme import dialog_stylesheet


HELP_SECTIONS = (
    (
        "基本の流れ",
        (
            "1. [画像読込] で jpg / jpeg / png 画像を開きます。",
            "2. プレビュー上で左クリックすると残したい場所に前景点を追加できます。",
            "3. 右クリックすると消したい場所に背景点を追加できます。",
            "4. [背景を削除] を押してマスクを作成します。",
            "5. 結果を確認して [結果を保存] から透過 PNG を保存します。",
        ),
    ),
    (
        "プレビュー操作",
        (
            "左クリック: 前景点を追加",
            "右クリック: 背景点を追加",
            "中クリック: 近くの点を削除",
            "点は少数から始め、境界が不十分な場所だけ追加すると調整しやすくなります。",
        ),
    ),
    (
        "きれいに抜くコツ",
        (
            "輪郭が欠けるときは残したい側に前景点を追加します。",
            "背景が残るときは不要な側に背景点を追加します。",
            "境界が硬いときは [フチをぼかす] を有効にし、値を少しずつ上げて確認します。",
        ),
    ),
    (
        "補足",
        (
            "使用するモデルがない場合は [モデル管理] からダウンロードしてください。",
            "保存形式は透過 PNG です。",
        ),
    ),
)


class HelpDialog(QDialog):
    def __init__(self, auto_show_enabled: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("使い方")
        self.resize(720, 620)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title_label = QLabel("使い方", self)
        title_label.setObjectName("helpDialogTitle")

        description_label = QLabel(
            "画像の読み込みから透過 PNG の保存まで、基本操作を確認できます。",
            self,
        )
        description_label.setObjectName("dialogDescriptionLabel")
        description_label.setWordWrap(True)

        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("helpScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget(scroll_area)
        scroll_content.setObjectName("helpScrollContent")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        for heading, paragraphs in HELP_SECTIONS:
            section_frame = QFrame(scroll_content)
            section_frame.setObjectName("helpSectionCard")
            section_layout = QVBoxLayout(section_frame)
            section_layout.setContentsMargins(16, 16, 16, 16)
            section_layout.setSpacing(8)

            heading_label = QLabel(heading, section_frame)
            heading_label.setObjectName("helpSectionTitle")

            body_label = QLabel("\n".join(paragraphs), section_frame)
            body_label.setObjectName("helpSectionBody")
            body_label.setWordWrap(True)
            body_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            section_layout.addWidget(heading_label)
            section_layout.addWidget(body_label)
            content_layout.addWidget(section_frame)

        content_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)

        self.auto_show_checkbox = QCheckBox("次回から自動表示しない", self)
        self.auto_show_checkbox.setChecked(not auto_show_enabled)

        footer_layout.addWidget(self.auto_show_checkbox)
        footer_layout.addStretch(1)

        self.close_button = QPushButton("閉じる", self)
        self.close_button.clicked.connect(self.accept)
        footer_layout.addWidget(self.close_button)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(scroll_area, 1)
        layout.addLayout(footer_layout)

        self._apply_styles()


    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is None:
            return
        parent_center = parent.frameGeometry().center()
        dialog_rect = self.frameGeometry()
        dialog_rect.moveCenter(QPoint(parent_center.x(), parent_center.y()))
        self.move(dialog_rect.topLeft())

    def auto_show_enabled(self) -> bool:
        return not self.auto_show_checkbox.isChecked()

    def _apply_styles(self) -> None:
        self.setStyleSheet(dialog_stylesheet())
