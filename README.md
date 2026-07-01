# Secure Chat Application

A secure real-time chat application built using Python, Flask, Flask-SocketIO, JavaScript, and SQLite.

This project was developed collaboratively as an academic cybersecurity project.

## Features

* User registration and login
* Real-time private messaging
* Chat rooms
* RSA-2048 key generation
* AES-EAX message encryption
* RSA-OAEP encrypted AES keys
* Digital signatures and integrity verification
* Encrypted private-key storage
* Unread message tracking
* Conversation search
* CSV message export

## Technologies Used

* Python
* Flask
* Flask-SocketIO
* SQLite
* HTML, CSS, and JavaScript
* PyCryptodome

## How It Works

Each message is encrypted using a randomly generated AES key. The AES key is then encrypted using the RSA public keys of both the sender and receiver.

Digital signatures are used to verify the authenticity and integrity of messages.

## Installation

git clone <repository-url>
cd <repository-folder>
pip install -r requirements.txt
python app.py

Open the application in your browser:

http://127.0.0.1:5000

## Security Limitation

The application stores users’ encrypted private keys on the server. Therefore, it demonstrates encrypted messaging but should not be considered a fully trustless end-to-end encrypted system.

A production version should generate and store private keys only on the user’s device and include stronger key management and secure key exchange mechanisms.

## Contributors

* Gautam Thakur
* Mehakdeep Kaur

Both contributors participated in the development, testing, and documentation of the project.

## Disclaimer

This project was created for academic and educational purposes. It is a security prototype and should not be treated as a production-ready messaging application.
