"""Driver minimale per l'LCD della Logitech G15 (v1) via HID, senza software Logitech.

Protocollo (da libg15): output report 0x03 di 992 byte = 32 byte di header
+ 960 byte di pixel. I pixel sono organizzati in 6 bande da 8 righe:
ogni byte e' una colonna verticale di 8 pixel (bit 0 = riga in alto).
"""
import hid
from PIL import Image

WIDTH, HEIGHT = 160, 43
VID = 0x046D
LCD_PIDS = (0xC222, 0xC227)  # G15 v1, G15 v2 (stesso formato; v2 non testata)
HEADER = 32
REPORT_LEN = 992


class G15LCD:
    def __init__(self):
        self.dev = None
        self.open()

    def open(self):
        for d in hid.enumerate(VID):
            if d["product_id"] in LCD_PIDS and d["usage_page"] == 0xFF00:
                dev = hid.device()
                dev.open_path(d["path"])
                self.dev = dev
                return
        raise RuntimeError("LCD G15 non trovato")

    def close(self):
        if self.dev:
            self.dev.close()
            self.dev = None

    def show(self, img: Image.Image):
        """Mostra un'immagine 160x43 (qualsiasi modo; i pixel non neri sono accesi)."""
        img = img.convert("1")
        if img.size != (WIDTH, HEIGHT):
            img = img.resize((WIDTH, HEIGHT))
        px = img.load()
        buf = bytearray(REPORT_LEN)
        buf[0] = 0x03
        for y in range(HEIGHT):
            band = HEADER + (y // 8) * WIDTH
            bit = 1 << (y % 8)
            for x in range(WIDTH):
                if px[x, y]:
                    buf[band + x] |= bit
        try:
            self.dev.write(bytes(buf))
        except (OSError, ValueError, AttributeError):
            # tastiera scollegata/ricollegata: riapri e riprova una volta
            self.close()
            self.open()
            self.dev.write(bytes(buf))


if __name__ == "__main__":
    from PIL import ImageDraw
    img = Image.new("1", (WIDTH, HEIGHT), 0)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=1)
    d.text((6, 6), "Ciao dalla G15!", fill=1)
    d.text((6, 22), "Claude Code status", fill=1)
    G15LCD().show(img)
    print("ok")
