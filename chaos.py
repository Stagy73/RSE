def chaos_total(schema):
    """
    Chaos si :
    - moins de 2 chevaux
    - ou trop de dispersion
    """
    if len(schema) < 2:
        return True

    if len(schema) > 8:
        return True

    return False
