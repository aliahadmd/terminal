import warnings
from cryptography.utils import CryptographyDeprecationWarning

warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

from terminal import Terminal

if __name__ == "__main__":
    app = Terminal()
    app.mainloop()