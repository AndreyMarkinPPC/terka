class Entity:

    def to_dict(self) -> dict:
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if hasattr(value, "name"):
                result[key] = value.name
            else:
                result[key] = value
        return result
