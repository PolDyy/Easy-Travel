import sqlite3


def init_db():
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
       user_id INTEGER PRIMARY KEY NOT NULL UNIQUE,
       user_name TEXT
    );
    """)
    cur.execute("""CREATE TABLE IF NOT EXISTS searches(
       search_id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
       user_id INTEGER REFERENCES users(user_id) NOT NULL
    );
    """)
    cur.execute("""CREATE TABLE IF NOT EXISTS messages(
       search_id INTEGER REFERENCES searches(search_id) NOT NULL,
       message TEXT NOT NULL,
       pictures TEXT
    );
    """)
    conn.commit()
    conn.close()


def user_insert(message):
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    cur.execute(""" INSERT INTO users(user_id, user_name)
    SELECT :user_id, :user_name
    WHERE NOT EXISTS(SELECT user_id FROM users WHERE user_id = :user_id);
    """, {'user_id': message.from_user.id, 'user_name': message.from_user.username})
    conn.commit()
    conn.close()


def search_insert(message):
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    cur.execute(""" INSERT INTO searches(user_id)
    VALUES(:user_id)
    """, {"user_id": message.from_user.id})
    conn.commit()
    conn.close()


def save_mes_and_pict(message, message_to_user, hotel_list):
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    cur.execute(""" INSERT INTO messages(search_id, message, pictures)
                SELECT search_id, :message_text, :mes_pictures
                FROM searches
                WHERE searches.user_id == :user_id
                ORDER BY searches.search_id DESC
                LIMIT 1
                """, {"message_text": message_to_user, "mes_pictures": " ,".join(hotel_list),
                      'user_id': message.from_user.id})
    conn.commit()
    conn.close()


def save_mes(message, message_to_user):
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    cur.execute(""" INSERT INTO messages(search_id, message)
    SELECT search_id, :message_text
    FROM searches
    WHERE searches.user_id == :user_id
    ORDER BY searches.search_id DESC
    LIMIT 1
    """, {"message_text": message_to_user, 'user_id': message.from_user.id})
    conn.commit()
    conn.close()


def history_cleansing(message):
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    len_list = cur.execute("""SELECT COUNT(search_id)
    FROM searches
    GROUP BY user_id   
    HAVING user_id = :user_id
    """, {"user_id": message.from_user.id}).fetchall()
    if int(len_list[0][0]) > 3:
        cur.execute("""DELETE FROM searches
         WHERE search_id = (SELECT MIN(search_id) FROM searches 
         WHERE user_id = :user_id)""", {"user_id": message.from_user.id})
        conn.commit()
    conn.close()


def history_list(message):
    conn = sqlite3.connect('travel_bot.db')
    cur = conn.cursor()
    history = cur.execute(""" SELECT message, pictures
    FROM messages
    WHERE messages.search_id IN(SELECT search_id FROM searches 
    LEFT JOIN users ON users.user_id = searches.user_id
    WHERE users.user_id =:user_id)
    """, {'user_id': message.from_user.id}).fetchall()
    conn.close()
    return history
