class FyersSession:
    _fyers = None

    @classmethod
    def set(cls, fyers):
        cls._fyers = fyers

    @classmethod
    def get(cls):
        if cls._fyers is None:
            raise RuntimeError("FyersSession not initialized")
        return cls._fyers
