# This is a window viewer, built on Quartz, given a process ID can return a base 64 encoded image of the window
from io import BytesIO
import Quartz, CoreFoundation
import base64

def return_base64_image(pid):
    windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID)
    bounds = []
    for window in windows:
        if (window['kCGWindowOwnerPID'] == pid):
            bounds.append([window['kCGWindowNumber'], window['kCGWindowBounds']])

    largest_bound = max(bounds, key=lambda x: x[1]["Height"] * x[1]["Width"] )

    win_id, rect_dict = largest_bound
    img = Quartz.CGWindowListCreateImageFromArray(
        Quartz.CGRectInfinite,
        [win_id],
        Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageNominalResolution
    )

    url = CoreFoundation.CFURLCreateWithFileSystemPath(
        None, "temp_out.png", CoreFoundation.kCFURLPOSIXPathStyle, False
    )
    type_id = "public.png"  # PNG UTI
    dest = Quartz.CGImageDestinationCreateWithURL(url, type_id, 1, None)
    Quartz.CGImageDestinationAddImage(dest, img, None)
    Quartz.CGImageDestinationFinalize(dest)

    # Read the image data back from the file
    with open("temp_out.png", "rb") as f:
        img_data = f.read()

    # Encode the image data to base64
    img_str = base64.b64encode(img_data).decode()


    return img_str

