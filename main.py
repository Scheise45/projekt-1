import sqlite3
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTabWidget,
    QFileDialog,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QInputDialog,
    QLineEdit,
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt, QUrl, QByteArray, QSize, QTemporaryFile
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import sys
import os


conn = sqlite3.connect("track.db")
cursor = conn.cursor()


class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Медиаплеер")
        self.play = False

        self.file_path = "save.txt"

        self.variables = self.load_variables()
        self.volume = int(self.variables.get("volume"))
        t = self.variables.get("filename", "")
        a = self.variables.get("artist", "")

        self.setGeometry(70, 70, 500, 700)
        self.setFixedSize(500, 700)
        self.selected_album_id = self.variables.get("album_id", "")
        self.artist = 0

        self.temp_file = None  # Временный файл для хранения трека

        self.current_track_id = self.variables.get("track_id", "")

        self.setMinimumSize(300, 200)

        # Создание вкладок
        self.tabwidget = QTabWidget()

        # Вкладка 2: Управление альбомами
        self.album_page = QWidget()
        self.album_layout = QVBoxLayout(self.album_page)

        # Кнопка для добавления нового альбома
        self.add_album_button = QPushButton("Добавить новый альбом")
        self.add_album_button.clicked.connect(self.add_album)
        self.album_layout.addWidget(self.add_album_button)

        # Комбобокс для фильтрации по исполнителям
        self.artist_filter_combo = QComboBox()
        self.artist_filter_combo.addItem("Все исполнители")
        self.load_artist_filter()  # Заполняем комбобокс именами исполнителей из БД
        self.artist_filter_combo.currentIndexChanged.connect(self.filter_albums)
        self.album_layout.addWidget(self.artist_filter_combo)

        # Таблица для отображения альбомов
        self.album_table = QTableWidget()
        self.album_table.setColumnCount(4)
        self.album_table.setHorizontalHeaderLabels(
            ["ID", "Название", "Год", "Исполнитель"]
        )
        self.album_layout.addWidget(self.album_table)

        # Таблица для отображения треков
        self.track_table = QTableWidget()
        self.track_table.setColumnCount(1)
        self.track_table.setHorizontalHeaderLabels(["Название трека"])
        self.album_layout.addWidget(self.track_table)
        self.track_table.hide()

        self.info_btn = QPushButton("Информация о альбоме")
        self.info_btn.clicked.connect(self.al_inf)
        self.album_layout.addWidget(self.info_btn)
        self.info_btn.hide()

        # Кнопка "Назад" для возвращения к таблице альбомов
        self.back_button = QPushButton("Назад к альбомам")
        self.back_button.clicked.connect(self.show_albums_table)
        self.album_layout.addWidget(self.back_button)
        self.back_button.hide()  # Кнопка "Назад" также скрыта по умолчанию

        # Кнопка добавления трека
        self.add_track_button = QPushButton("Добавить трек")
        self.add_track_button.clicked.connect(self.add_track)
        self.album_layout.addWidget(self.add_track_button)
        self.add_track_button.hide()  # Скрыта по умолчанию

        # Кнопка редактирования альбома
        self.edit_album_button = QPushButton("Редактировать альбом")
        self.edit_album_button.clicked.connect(self.edit_album)
        self.album_layout.addWidget(self.edit_album_button)
        self.edit_album_button.hide()  # Скрыта по умолчанию

        # Загрузка данных альбомов при старте
        self.load_albums()

        # Обработчик двойного щелчка для просмотра треков
        self.album_table.cellDoubleClicked.connect(self.show_tracks)

        # Вкладка 1: Медиаплеер
        self.media_page = QWidget()
        self.media_layout = QVBoxLayout(self.media_page)

        # Изображение
        self.im = QLabel()
        self.im.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_layout.addWidget(self.im)

        # Название трека
        self.track_name = QLabel(t, self)
        f = QFont()
        f.setBold(True)
        f.setPointSize(20)
        self.track_name.setFont(f)
        self.track_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_layout.addWidget(self.track_name)

        self.track_artist = QLabel(a, self)
        f = QFont()
        f.setPointSize(15)
        self.track_artist.setFont(f)
        self.track_artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_layout.addWidget(self.track_artist)

        # Медиаплеер
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Ползунок прогресса
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.set_position)

        # Следим за состоянием ползунка для перемотки
        self.progress_slider.sliderPressed.connect(self.start_dragging)
        self.progress_slider.sliderReleased.connect(self.stop_dragging)

        self.media_layout.addWidget(self.progress_slider)

        # Флаг, указывающий, когда ползунок перемещается пользователем
        self.user_is_dragging = False

        # Метки времени
        self.current_time_label = QLabel("0:00")
        self.total_time_label = QLabel("0:00")
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.progress_slider)
        time_layout.addWidget(self.total_time_label)
        self.media_layout.addLayout(time_layout)

        # Управление звуком и воспроизведением
        controls_layout = QHBoxLayout()

        self.sound_btn = QPushButton("Yes", self)
        self.sound_btn.clicked.connect(self.voice)
        controls_layout.addWidget(self.sound_btn, 1)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.volume)
        self.volume_slider.valueChanged.connect(self.set_volume)
        controls_layout.addWidget(self.volume_slider, 1)

        self.play_button = QPushButton("⏵", self)
        self.play_button.clicked.connect(self.play_track)
        controls_layout.addWidget(self.play_button, 1)

        self.clear_button = QPushButton("■")
        self.clear_button.clicked.connect(self.clear_track)
        controls_layout.addWidget(self.clear_button, 1)

        self.media_layout.addLayout(controls_layout)

        # Обработчики сигналов для медиаплеера
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_position)

        # Добавляем страницы в QTabWidget
        self.tabwidget.addTab(self.media_page, "Медиаплеер")
        self.tabwidget.addTab(self.album_page, "Альбомы")
        # Подключение к сигналу завершения воспроизведения
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)

        self.setCentralWidget(self.tabwidget)

        self.start()
        self.selected_album_id = 0

    def load_artist_filter(self):
        """Загрузка исполнителей из таблицы artist для фильтрации."""
        cursor.execute("SELECT id, artist_name FROM artist")
        artists = cursor.fetchall()
        for artist_id, artist_name in artists:
            self.artist_filter_combo.addItem(artist_name, artist_id)

    def load_albums(self, artist_id=None):
        """Загрузка всех альбомов или фильтрация по выбранному исполнителю."""
        # Очистка таблицы
        self.album_table.setRowCount(0)

        # Установка заголовков для альбомов
        self.album_table.setColumnCount(4)
        self.album_table.setHorizontalHeaderLabels(
            ["ID", "Название", "Год", "Исполнитель"]
        )

        # Получение всех альбомов с указанием исполнителя
        if artist_id is None:  # Если фильтр не применен, показываем все альбомы
            query = """
            SELECT album.id, album.album_name, album.year, artist.artist_name
            FROM album
            LEFT JOIN artist ON album.artist_id = artist.id
            """
            cursor.execute(query)
        else:  # Если выбран исполнитель, фильтруем по artist_id
            query = """
            SELECT album.id, album.album_name, album.year, artist.artist_name
            FROM album
            LEFT JOIN artist ON album.artist_id = artist.id
            WHERE album.artist_id = ?
            """
            cursor.execute(query, (artist_id,))

        albums = cursor.fetchall()

        for row_num, (album_id, album_name, year, artist_name) in enumerate(albums):
            self.album_table.insertRow(row_num)
            self.album_table.setItem(row_num, 0, QTableWidgetItem(str(album_id)))
            self.album_table.setItem(row_num, 1, QTableWidgetItem(album_name))
            self.album_table.setItem(row_num, 2, QTableWidgetItem(str(year)))
            self.album_table.setItem(
                row_num,
                3,
                QTableWidgetItem(artist_name if artist_name else "Неизвестно"),
            )

    def filter_albums(self):
        """Применение фильтрации по исполнителям."""
        artist_index = self.artist_filter_combo.currentIndex()

        if artist_index == 0:
            # Если выбран "Все исполнители", показываем все альбомы
            self.load_albums()
        else:
            # Получаем artist_id из data элемента комбобокса
            artist_id = self.artist_filter_combo.itemData(artist_index)
            # Загружаем только альбомы этого исполнителя
            self.load_albums(artist_id)

    def show_tracks(self, row):
        """Отображение треков выбранного альбома при двойном щелчке по названию."""
        if not self.selected_album_id:
            album_id = str(self.album_table.item(row, 0).text())  # Получаем ID альбома
            self.selected_album_id = album_id
        if not self.artist:  # Если атрибут artist не существует
            query = """
            SELECT artist_id
            FROM album
            WHERE id = ?
            """
            artist = cursor.execute(query, (self.selected_album_id,)).fetchone()
            if artist:
                # Сохраняем artist_id в атрибут класса
                self.artist = int(artist[0])

        # Теперь self.artist будет содержать значение, и запрос в базу данных не нужен
        # Запрос на выбор треков из таблицы track для выбранного альбома
        query = """
        SELECT name
        FROM track
        WHERE track.album_id = ?
        """
        tracks = cursor.execute(query, (self.selected_album_id,)).fetchall()

        # Отображение треков в таблице
        self.track_table.setRowCount(0)
        for row_num, (track_name,) in enumerate(tracks):
            self.track_table.insertRow(row_num)
            self.track_table.setItem(row_num, 0, QTableWidgetItem(track_name))

        # Скрываем таблицу альбомов и кнопку добавления, отображаем таблицу треков и кнопку "Назад"
        self.album_table.hide()
        self.add_album_button.hide()
        self.artist_filter_combo.hide()
        self.track_table.show()
        self.back_button.show()
        self.info_btn.show()

        # Показываем кнопку редактирования альбома и добавления трека
        self.edit_album_button.show()
        self.add_track_button.show()

        self.track_table.cellDoubleClicked.connect(self.show_track_info)

    def show_track_info(self, row):
        track_name = self.track_table.item(row, 0).text()
        self.track_name.setText(self.track_table.item(row, 0).text())

        # Получение ID трека и ID исполнителя
        query = """
        SELECT track.id, track.artist_id
        FROM track
        WHERE track.name = ? AND track.album_id = ?
        """
        track_data = cursor.execute(
            query, (track_name, self.selected_album_id)
        ).fetchone()

        album_query = "SELECT picture FROM album WHERE id = ?"
        album_pict = cursor.execute(album_query, (self.selected_album_id,))
        result = album_pict.fetchone()
        if result:
            blob_data = result[0]
            self.image(blob_data)

        if track_data:
            track_id, artist_id = track_data

            # Сохранение ID трека и исполнителя в атрибуты
            self.current_track_id = track_id
            # self.current_artist_id = artist_id

            # Получение имени исполнителя
            artist_query = "SELECT artist_name FROM artist WHERE id = ?"
            artist_name = cursor.execute(artist_query, (artist_id,)).fetchone()

            artist_name = artist_name[0] if artist_name else "Неизвестно"
            self.track_artist.setText(artist_name)

        # Извлечение MP3 из базы данных
        cursor.execute("SELECT data FROM track WHERE id = ?", (self.current_track_id,))
        result = cursor.fetchone()

        if result and result[0]:  # Проверка, что данные найдены
            blob_data = result[0]

            # Создание временного файла для хранения MP3
            self.temp_file = QTemporaryFile(self)
            # Удаление файла при завершении программы
            self.temp_file.setAutoRemove(True)

            if self.temp_file.open():  # Открытие временного файла для записи
                self.temp_file.write(blob_data)
                self.temp_file.flush()  # Запись и сохранение данных на диск

                # Установка источника для плеера и воспроизведение
                self.player.setSource(QUrl.fromLocalFile(self.temp_file.fileName()))
                self.play_track()

    def show_albums_table(self):
        """Возвращение к таблице альбомов."""
        self.track_table.hide()  # Скрываем таблицу треков
        self.back_button.hide()  # Скрываем кнопку "Назад"
        self.info_btn.hide()
        self.edit_album_button.hide()  # Скрываем кнопку редактирования
        self.add_track_button.hide()  # Скрываем кнопку добавления трека
        self.selected_album_id = 0
        self.artist = 0

        # Показать таблицу альбомов и фильтр исполнителей
        self.album_table.show()
        self.add_album_button.show()
        self.artist_filter_combo.show()

    def add_album(self):
        # Ввод названия альбома
        album_name, ok = QInputDialog.getText(
            self, "Новый альбом", "Введите название альбома:"
        )
        if not ok or not album_name:
            return

        # Ввод года создания альбома
        year, ok = QInputDialog.getInt(
            self, "Год создания", "Введите год создания альбома:"
        )
        if not ok:
            return

        # Выбор текстового файла для альбома
        text_file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите текстовый файл для альбома", "", "Text Files (*.txt)"
        )
        text_file_data = None
        if text_file_path:
            with open(text_file_path, "rb") as file:
                text_file_data = file.read()

        # Выбор изображения для альбома
        picture_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение для альбома", "", "Images (*.png *.jpg *.bmp)"
        )
        picture_data = None
        if picture_path:
            with open(picture_path, "rb") as file:
                picture_data = file.read()

        # Ввод исполнителя из существующих в таблице artist
        cursor.execute("SELECT id, artist_name FROM artist")
        artists = cursor.fetchall()
        artist_names = [artist[1] for artist in artists]
        artist_id = None

        if artists:
            artist_name, ok = QInputDialog.getItem(
                self,
                "Исполнитель",
                "Выберите исполнителя:",
                artist_names,
                editable=False,
            )
            if ok and artist_name:
                artist_id = next(
                    (artist[0] for artist in artists if artist[1] == artist_name), None
                )

        # Вставка данных нового альбома в базу данных
        cursor.execute(
            """
            INSERT INTO album (album_name, year, artist_id, info, picture)
            VALUES (?, ?, ?, ?, ?)
        """,
            (album_name, year, artist_id, text_file_data, picture_data),
        )

        conn.commit()
        QMessageBox.information(self, "Успех", "Альбом успешно добавлен!")
        self.load_albums()  # Обновление таблицы альбомов

    def add_track(self):
        """Добавление трека в выбранный альбом."""
        self.adtrack = TrackDatabaseApp("track.db", self.selected_album_id, self.artist)
        self.adtrack.show()
        conn.commit()

        self.show_albums_table()
        self.selected_album_id = 0
        self.artist = 0

    def edit_album(self):
        # Редактирование информации об альбоме
        cursor.execute(
            "SELECT album_name, year, info, picture FROM album WHERE id = ?",
            (self.selected_album_id,),
        )
        album_data = cursor.fetchone()

        if not album_data:
            return

        album_name, year, text_file_data, picture_data = album_data

        # Ввод нового названия альбома
        new_album_name, ok = QInputDialog.getText(
            self,
            "Редактировать альбом",
            "Введите новое название альбома:",
            text=album_name,
        )
        if not ok or not new_album_name:
            return

        # Ввод нового года альбома
        new_year, ok = QInputDialog.getInt(
            self, "Год создания", "Введите новый год создания альбома:", value=year
        )
        if not ok:
            return

        # Выбор нового текстового файла
        new_text_file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите новый текстовый файл для альбома", "", "Text Files (*.txt)"
        )
        if new_text_file_path:
            with open(new_text_file_path, "rb") as file:
                text_file_data = file.read()

        # Выбор нового изображения (обложки)
        new_picture_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите новое изображение для альбома",
            "",
            "Images (*.png *.jpg *.bmp)",
        )
        if new_picture_path:
            with open(new_picture_path, "rb") as file:
                picture_data = file.read()

        # Обновление данных в базе данных
        cursor.execute(
            """
            UPDATE album
            SET album_name = ?, year = ?, info = ?, picture = ?
            WHERE id = ?
            """,
            (
                new_album_name,
                new_year,
                text_file_data,
                picture_data,
                self.selected_album_id,
            ),
        )

        conn.commit()
        QMessageBox.information(self, "Успех", "Альбом успешно обновлен!")
        self.load_albums()  # Обновление таблицы альбомов
        self.show_albums_table()  # Возвращаемся к таблице альбомов

    def play_track(self):
        if self.play:
            self.player.pause()
            self.play_button.setText("⏵")
        else:
            self.player.play()
            self.play_button.setText("||")
        self.play = not self.play

    def set_position(self, position):
        duration = self.player.duration()
        if duration > 0:
            new_position = int(duration * position / 100)
            self.player.setPosition(new_position)

            self.current_time_label.setText(self.format_time(new_position))

    def voice(self):
        if self.volume_slider.value() != 0:
            self.volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self.sound_btn.setText("NO")
        else:
            self.sound_btn.setText("YES")
            self.volume_slider.setValue(self.volume)

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100)

    def update_duration(self, duration):
        self.total_time_label.setText(self.format_time(duration))

    def format_time(self, ms):
        seconds = ms // 1000
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes}:{seconds:02}"

    def update_position(self, position):
        if (
            not self.user_is_dragging
        ):  # Обновляем только если ползунок не двигается пользователем
            self.progress_slider.setValue(position * 100 // self.player.duration())
            self.current_time_label.setText(self.format_time(position))

    def image(self, blob_data):
        qpixmap = QPixmap()
        qpixmap.loadFromData(QByteArray(blob_data))
        if qpixmap.size() != QSize(400, 400):
            qpixmap = qpixmap.scaled(
                400,
                400,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.im.setPixmap(qpixmap)

    def on_media_status_changed(self, status):
        # Обработчик события изменения статуса воспроизведения
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.clear_track()

    def clear_track(self):
        # Остановка текущего трека
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.play_track()

        # Закрытие и удаление временного файла
        if self.temp_file:
            self.temp_file.close()
            self.temp_file = None

        self.progress_slider.setValue(0)
        self.player.setPosition(0)
        self.current_track_id = 0

    def start_dragging(self):
        self.user_is_dragging = True

    def stop_dragging(self):
        self.user_is_dragging = False
        self.set_position(self.progress_slider.value())

    def al_inf(self):
        data = self.fetch_data_from_db()  # Извлекаем данные из БД
        self.second_window = Info(data)
        self.second_window.show()

    def fetch_data_from_db(self):
        # Выполняем запрос для получения данных: год выпуска и информация о треке
        cursor.execute(
            """
            SELECT year, info
            FROM album
            WHERE id = ?
        """,
            (self.selected_album_id,),
        )  # Пример запроса, выбираем данные по конкретному треку (например, с id = 1)

        result = cursor.fetchone()

        if result:
            year = result[0]
            # Декодируем бинарные данные из поля info в строку
            track_info = self.decode_binary_data(result[1])
            # Форматируем описание, разбивая на строки по 10 слов
            formatted_info = self.format_text(track_info)
            return (year, formatted_info)  # Возвращаем данные
        else:
            return ("Не найдено", "Не найдено")  # Если данных нет

    def decode_binary_data(self, binary_data):
        """Преобразует бинарные данные в строку (текст)"""
        try:
            # Декодируем бинарные данные в строку с использованием кодировки UTF-8
            return binary_data.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            # Если не удается декодировать, выводим сообщение об ошибке
            return "Не удалось декодировать информацию"

    def format_text(self, text):
        """Форматирует текст, добавляя перенос строки после каждых 10 слов"""
        words = text.split()
        formatted_text = ""
        for i in range(0, len(words), 10):
            formatted_text += " ".join(words[i : i + 10]) + "\n"
        return formatted_text

    def closeEvent(self, event):
        """Вызывается при закрытии окна: сохраняет переменные в файл."""
        self.save_variables()
        event.accept()

    def save_variables(self):
        """Сохраняет текущие значения переменных в файл."""
        self.variables = {
            "volume": str(self.volume_slider.value()),
            "filename": self.track_name.text(),
            "artist": self.track_artist.text(),
            "track_id": str(self.current_track_id),
            "album_id": str(self.selected_album_id),
        }

        with open(self.file_path, "w") as file:
            for key, value in self.variables.items():
                file.write(f"{key}={value}\n")

    def load_variables(self):
        variables = {}
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                for line in file:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        variables[key] = value
        return variables

    def start(self):
        album_query = "SELECT picture FROM album WHERE id = ?"
        album_pict = cursor.execute(album_query, (self.selected_album_id,))
        result = album_pict.fetchone()
        if result:
            blob_data = result[0]
            self.image(blob_data)

        # Извлечение MP3 из базы данных
        cursor.execute("SELECT data FROM track WHERE id = ?", (self.current_track_id,))
        result = cursor.fetchone()

        if result and result[0]:  # Проверка, что данные найдены
            blob_data = result[0]

            # Создание временного файла для хранения MP3
            self.temp_file = QTemporaryFile(self)
            # Удаление файла при завершении программы
            self.temp_file.setAutoRemove(True)

            if self.temp_file.open():  # Открытие временного файла для записи
                self.temp_file.write(blob_data)
                self.temp_file.flush()  # Запись и сохранение данных на диск

                # Установка источника для плеера и воспроизведение
                self.player.setSource(QUrl.fromLocalFile(self.temp_file.fileName()))


class TrackDatabaseApp(QMainWindow):
    def __init__(self, db_path, al_id, ar_id):
        super().__init__()
        self.db_path = db_path
        self.initUI()
        self.selected_file = None
        self.al_id = al_id
        self.ar_id = ar_id

    def initUI(self):
        # Основные настройки окна
        self.setWindowTitle("Добавление трека в базу данных")
        self.setGeometry(200, 200, 300, 300)
        self.setFixedSize(300, 300)

        # Основной виджет и компоновка
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Поля для ввода данных трека
        self.name_input = QLineEdit(self)

        # Метки и поля ввода для каждого атрибута трека
        layout.addWidget(QLabel("Название трека:"))
        layout.addWidget(self.name_input)

        # Кнопка для выбора файла
        self.select_file_button = QPushButton("Выбрать MP3-файл", self)
        self.select_file_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_file_button)

        # Кнопка для добавления записи в базу данных
        self.add_track_button = QPushButton("Добавить трек в базу", self)
        self.add_track_button.clicked.connect(self.add_track_to_database)
        layout.addWidget(self.add_track_button)

    def select_file(self):
        # Открытие диалогового окна для выбора MP3-файла
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("MP3 Files (*.mp3)")
        if file_dialog.exec():
            self.selected_file = file_dialog.selectedFiles()[0]

            # Извлечение названия файла без расширения
            file_name = os.path.basename(self.selected_file)  # Получаем имя файла
            track_name = os.path.splitext(file_name)[0]  # Убираем расширение
            self.name_input.setText(track_name)  # Заполняем поле с названием

            QMessageBox.information(
                self, "Файл выбран", f"Выбран файл: {self.selected_file}"
            )

    def add_track_to_database(self):
        # Проверка на заполнение всех полей
        name = self.name_input.text()
        album_id = self.al_id
        artist_id = self.ar_id

        if not (name and artist_id and album_id and self.selected_file):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля и выберите файл.")
            return

        # Подключение к базе данных
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Вставка новой записи в таблицу track
        cursor.execute(
            "INSERT INTO track (name, album_id, artist_id, data) VALUES (?, ?, ?, ?)",
            (name, album_id, artist_id, None),
        )
        track_id = cursor.lastrowid  # Получаем ID только что добавленной записи

        # Чтение файла MP3 и сохранение его как BLOB
        with open(self.selected_file, "rb") as file:
            blob_data = file.read()
            cursor.execute(
                "UPDATE track SET data = ? WHERE id = ?", (blob_data, track_id)
            )

        conn.commit()

        self.show_message(name)

    def show_message(self, name):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Успех! Трек '{name}' успешно добавлен!")
        msg.setWindowTitle("Сообщение")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Показываем окно и ждем, пока пользователь нажмет OK
        if msg.exec() == QMessageBox.StandardButton.Ok:
            self.close()  # Закрываем второе окно после нажатия OK


class Info(QWidget):
    def __init__(self, data):
        super().__init__()
        self.setWindowTitle("Данные о альбоме")
        self.setGeometry(300, 300, 300, 200)

        # Создаем два QLabel для отображения данных
        self.label1 = QLabel(f"Год выпуска: {data[0]}", self)
        self.label1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label2 = QLabel(f"Информация о треке: \n{data[1]}", self)
        self.label2.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout = QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.label2)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MusicPlayer()
    window.show()
    sys.exit(app.exec())
