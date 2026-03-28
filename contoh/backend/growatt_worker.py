from PySide6.QtCore import QThread, Signal


class GrowattWorker(QThread):
    """
    Worker thread untuk Growatt
    - Semua HTTP & API dipindah ke thread
    """

    data_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self._running = True

    def run(self):
        try:
            if not self._running:
                return

            data = self.backend.fetch()
            self.data_ready.emit(data)

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._running = False
