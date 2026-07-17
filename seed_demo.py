from datetime import date, timedelta
import sqlite3

from werkzeug.security import generate_password_hash


DB_NAME = "taskhub.db"
SCHEMA_FILE = "models.sql"


def create_demo_database():
    connection = sqlite3.connect(DB_NAME)
    connection.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_FILE, "r", encoding="utf-8") as file:
        schema = file.read()

    connection.executescript("""
        DROP TABLE IF EXISTS tasks;
        DROP TABLE IF EXISTS projects;
        DROP TABLE IF EXISTS users;
    """)

    connection.executescript(schema)

    password_hash = generate_password_hash("123456")

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO users (full_name, username, email, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Basri Emir Özkaynakcı",
            "emir",
            "emir@test.com",
            password_hash
        )
    )

    user_id = cursor.lastrowid

    projects = [
        (
            "Bitirme Tezi Yönetimi",
            "Literatür taraması, anket süreci, veri analizi ve final raporu adımlarının takip edildiği proje."
        ),
        (
            "Web Uygulaması Geliştirme",
            "Flask, SQLite ve Bootstrap kullanılarak geliştirilen görev takip sisteminin geliştirme süreci."
        ),
        (
            "Uzman Semineri Sunumu",
            "Sunum içeriği, örnekler ve final anlatım metninin hazırlanması."
        )
    ]

    project_ids = {}

    for title, description in projects:
        cursor.execute(
            """
            INSERT INTO projects (user_id, title, description)
            VALUES (?, ?, ?)
            """,
            (user_id, title, description)
        )

        project_ids[title] = cursor.lastrowid

    today = date.today()

    tasks = [
        (
            "Bitirme Tezi Yönetimi",
            "Literatür kaynaklarını düzenle",
            "Kaynakların APA formatına uygunluğu ve konu bütünlüğü kontrol edilecek.",
            "Orta",
            "Tamamlandı",
            ""
        ),
        (
            "Bitirme Tezi Yönetimi",
            "Anket verilerini kontrol et",
            "Google Forms çıktıları incelenip eksik veya hatalı yanıtlar ayıklanacak.",
            "Yüksek",
            "Devam Ediyor",
            str(today + timedelta(days=2))
        ),
        (
            "Bitirme Tezi Yönetimi",
            "Bulgular bölümünü yaz",
            "SPSS çıktılarına göre tablo açıklamaları ve yorumlar hazırlanacak.",
            "Yüksek",
            "Yapılacak",
            str(today + timedelta(days=5))
        ),
        (
            "Web Uygulaması Geliştirme",
            "Kullanıcı giriş sistemini test et",
            "Kayıt, giriş, çıkış ve kullanıcı adı ile giriş akışı kontrol edilecek.",
            "Orta",
            "Tamamlandı",
            ""
        ),
        (
            "Web Uygulaması Geliştirme",
            "Dashboard tasarımını düzenle",
            "Yönetim paneli, riskli görevler alanı ve proje kartları son kez kontrol edilecek.",
            "Yüksek",
            "Devam Ediyor",
            str(today - timedelta(days=1))
        ),
        (
            "Web Uygulaması Geliştirme",
            "Son testleri yap",
            "Proje oluşturma, görev ekleme, arama ve silme işlemleri baştan sona test edilecek.",
            "Yüksek",
            "Yapılacak",
            str(today + timedelta(days=3))
        ),
        (
            "Uzman Semineri Sunumu",
            "Sunum başlıklarını belirle",
            "Sunumun giriş, gelişme ve sonuç akışı netleştirilecek.",
            "Düşük",
            "Tamamlandı",
            ""
        ),
        (
            "Uzman Semineri Sunumu",
            "Slayt tasarımını düzenle",
            "Sunum görselleri, başlıklar ve geçiş yapısı sadeleştirilecek.",
            "Orta",
            "Devam Ediyor",
            str(today + timedelta(days=4))
        ),
        (
            "Uzman Semineri Sunumu",
            "Sunum provasını yap",
            "Final anlatımı için süre ve konuşma akışı kontrol edilecek.",
            "Yüksek",
            "Yapılacak",
            str(today + timedelta(days=6))
        )
    ]

    for project_title, title, description, priority, status, due_date in tasks:
        cursor.execute(
            """
            INSERT INTO tasks (project_id, title, description, priority, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project_ids[project_title],
                title,
                description,
                priority,
                status,
                due_date
            )
        )

    connection.commit()
    connection.close()

    print("Demo veritabanı başarıyla oluşturuldu.")
    print("Giriş bilgileri:")
    print("Kullanıcı adı: emir")
    print("E-posta: emir@test.com")
    print("Şifre: 123456")


if __name__ == "__main__":
    create_demo_database()