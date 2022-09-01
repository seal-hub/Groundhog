import json
from typing import List, Union


def unsafe_json_load(content: str) -> Union[dict, None]:
    try:
        return json.loads(content)
    except Exception as e:
        return None

class JSONSerializable:
    def toJSONStr(self, excluded_attributes: List[str] = None) -> str:
        if excluded_attributes is None:
            excluded_attributes = []

        def get_items(o) -> dict:
            res = {}
            for (k, v) in o.__dict__.items():
                if k in excluded_attributes:
                    continue
                if issubclass(type(v), JSONSerializable) and v != self:  # TODO: Possible infinite recursion
                    v = v.toJSON()
                res[k] = v
            return res

        return json.dumps(self,
                          default=get_items,
                          sort_keys=True)

    def toJSON(self, excluded_attributes: List[str] = None) -> dict:
        return json.loads(self.toJSONStr(excluded_attributes))

    def __str__(self):
        return f"{type(self).__name__}({self.toJSONStr()[1:-1]})"

    def __repr__(self):
        return f"{type(self).__name__}({self.toJSONStr()[1:-1]})"
