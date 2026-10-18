from app.security.passwords import check_password, hash_password


def test_hash_no_guarda_texto_plano():
    h = hash_password("Secreta123")
    assert h != "Secreta123"
    assert h.startswith("$2")


def test_check_password_correcta_e_incorrecta():
    h = hash_password("Secreta123")
    assert check_password("Secreta123", h)
    assert not check_password("otra-clave", h)
