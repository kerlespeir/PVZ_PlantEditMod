from __future__ import annotations

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class CppHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor("#569CD6"))
        keyword_fmt.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "class", "public", "private", "protected", "virtual", "override",
            "int", "void", "bool", "char", "float", "double", "auto", "const",
            "if", "else", "for", "while", "return", "new", "delete",
            "nullptr", "true", "false", "this", "using", "namespace",
            "include", "pragma", "once", "struct", "enum", "static",
        ]
        for kw in keywords:
            pattern = QRegularExpression(rf"\b{kw}\b")
            self._rules.append((pattern, keyword_fmt))

        type_fmt = QTextCharFormat()
        type_fmt.setForeground(QColor("#4EC9B0"))
        types = [
            "HybridPlant", "Plant", "Component", "GameAPI",
            "PeaHead", "SunHead", "PotatoMineHead", "WallNutHead",
            "std::unique_ptr", "std::make_unique", "std::vector",
            "PVZ_REGISTER_HYBRID", "PVZ_REGISTER_PLANT",
        ]
        for t in types:
            pattern = QRegularExpression(QRegularExpression.escape(t))
            self._rules.append((pattern, type_fmt))

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#B5CEA8"))
        self._rules.append((QRegularExpression(r"\b\d+\b"), number_fmt))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#CE9178"))
        self._rules.append((QRegularExpression(r'"[^"]*"'), string_fmt))

        self._comment_fmt = QTextCharFormat()
        self._comment_fmt.setForeground(QColor("#6A9955"))
        self._rules.append((QRegularExpression(r"//[^\n]*"), self._comment_fmt))

        self._preproc_fmt = QTextCharFormat()
        self._preproc_fmt.setForeground(QColor("#C586C0"))
        self._rules.append((QRegularExpression(r"#\w+"), self._preproc_fmt))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
