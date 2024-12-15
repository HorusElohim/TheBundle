from ....core import data


class TorrentData(data.Data):
    name: str = data.Field(default="")
    seeds: int = data.Field(default=0)
    leeches: int = data.Field(default=0)
    uploaded_at: str = data.Field(default="")
    size: str = data.Field(default="")
    uploader: str = data.Field(default="")
    detail_url: str = data.Field(default="")
    magnet_link: str = data.Field(default="")

    @data.field_validator("seeds", "leeches")
    def check_non_negative(cls, value):
        if value < 0:
            raise ValueError("Seeds/Leeches must be non-negative")
        return value
