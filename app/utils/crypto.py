from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes


def generate_keys():
    key = RSA.generate(2048)
    return (
        key.publickey().export_key().decode(),
        key.export_key().decode()
    )


def encrypt_for_chat(message, sender_public, receiver_public):
    aes_key = get_random_bytes(16)

    aes = AES.new(aes_key, AES.MODE_EAX)
    ciphertext, tag = aes.encrypt_and_digest(message.encode())

    rsa_sender = PKCS1_OAEP.new(RSA.import_key(sender_public))
    wrapped_sender = rsa_sender.encrypt(aes_key)

    rsa_receiver = PKCS1_OAEP.new(RSA.import_key(receiver_public))
    wrapped_receiver = rsa_receiver.encrypt(aes_key)

    return (
        wrapped_sender,
        wrapped_receiver,
        aes.nonce,
        ciphertext,
        tag
    )


def decrypt_chat(wrapped_key, nonce, ciphertext, tag, private_key):
    rsa = PKCS1_OAEP.new(RSA.import_key(private_key))
    aes_key = rsa.decrypt(wrapped_key)

    aes = AES.new(aes_key, AES.MODE_EAX, nonce=nonce)
    message = aes.decrypt_and_verify(ciphertext, tag)

    return message.decode()