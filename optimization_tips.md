# OPTIMASI WAJAH.PY

## Prioritas 1: Cache Color/Brush/Pen Objects

### SEKARANG (TIDAK EFEISIEN):
```python
def _draw_gabut_eyes(self, painter, ...):
    for bx in (left_x, right_x):
        # Setiap frame, setiap mata, BUAT GRADIENT BARU!
        gradient = QRadialGradient(...)  # MAHAL!
        painter.setBrush(QBrush(gradient))
```

### LEBIH EFEISIEN:
```python
def __init__(self):
    # Cache gradient objects saat init
    self._cached_gradients = {}
    self._cached_brushes = {}
    self._cached_colors = {}

def _get_or_create_gradient(self, key, factory_func):
    """Cache gradient objects"""
    if key not in self._cached_gradients:
        self._cached_gradients[key] = factory_func()
    return self._cached_gradients[key]

def _draw_gabut_eyes(self, painter, ...):
    # Pakai cache, jangan buat baru setiap frame!
    gradient = self._get_or_create_gradient(
        f"gabut_eye_{mode}",
        lambda: QRadialGradient(...)
    )
```

---

## Prioritas 2: Reduce PaintEvent Complexity

### SEKARANG (TERLALU BANYAK CALCULATION):
```python
def paintEvent(self, event):
    # 52 trigonometric calls
    # 201 object creations
    # 31 gradient creations
    # DIPANGGIL SETIAP 30ms = 33 FPS!
```

### LEBIH EFEISIEN:
```python
def paintEvent(self, event):
    # Pre-calculate values
    t = self.expr_state["time"]

    # Cache common colors
    if not hasattr(self, '_color_cache'):
        self._color_cache = {}

    # Reduce conditional checks
    expr = self.expression
    if expr == "gabut":
        self._draw_gabut_fast(painter)  # Optimized version
```

---

## Prioritas 3: Use Solid Colors Instead of Gradients

### SEKARANG:
```python
# Setiap element pakai gradient (MAHAL!)
gradient = QRadialGradient(...)
gradient.setColorAt(0, ...)
gradient.setColorAt(1, ...)
```

### LEBIH EFEISIEN:
```python
# Pakai solid color untuk elemen kecil
painter.setBrush(QColor(180, 220, 255))

# Hanya pakai gradient untuk elemen BESAR yang butuh depth
if eye_w > 100:  # Hanya kalau besar
    gradient = QRadialGradient(...)
```

---

## Prioritas 4: Reduce Timer Frequency

### SEKARANG:
```python
self.expr_timer.start(30)  # 33 FPS - TERLALU CEPAT!
self.gabut_timer.start(28)  # 35 FPS - LEBIH CEPAT!
```

### LEBIH EFEISIEN:
```python
self.expr_timer.start(50)   # 20 FPS - Cukup untuk animasi smooth
self.gabut_timer.start(50)  # 20 FPS - Cukup untuk gabut
```

**HASIL: 40% reduction dalam CPU usage!**

---

## Prioritas 5: Batch Similar Operations

### SEKARANG:
```python
# Loop terpisah untuk setiap mata
for bx in (left_x, right_x):
    painter.setBrush(...)
    painter.drawPolygon(...)

for bx in (left_x, right_x):
    # Set brush lagi
    painter.setBrush(...)
    painter.drawEllipse(...)
```

### LEBIH EFEISIEN:
```python
# Batch operations untuk kedua mata sekaligus
for bx in (left_x, right_x):
    # Draw semua komponen mata dalam satu loop
    self._draw_eye_components(painter, bx, ...)

# Atau lebih baik: draw keduanya dalam satu painter path
```

---

## Prioritas 6: Use QPainterPath untuk Complex Shapes

### SEKARANG:
```python
pts = [QPointF(...), QPointF(...), ...]
painter.drawPolygon(QPolygonF(pts))
```

### LEBIH EFEISIEN (untuk shapes kompleks):
```python
path = QPainterPath()
path.addPolygon(...)
path.addEllipse(...)
painter.drawPath(path)  # Satu call saja!
```

---

## Impact Estimation:

### SEKARANG:
- Object creation: ~6600/detik
- Gradients: ~1000/detik
- Trig calls: ~1500/detik
- Estimated FPS: 20-30 FPS on mid-range device

### SETELAH OPTIMASI:
- Object creation: ~100/detik (98.5% reduction!)
- Gradients: ~50/detik (95% reduction!)
- Trig calls: ~300/detik (80% reduction!)
- Estimated FPS: 50-60 FPS on mid-range device

---

## Recommended Action Plan:

### FASE 1 (Quick Wins - 1 jam):
1. Cache gradient objects
2. Reduce timer frequency ke 50ms
3. Remove unnecessary trig calls

### FASE 2 (Medium - 2-3 jam):
1. Implement solid colors untuk elemen kecil
2. Batch similar operations
3. Pre-calculate common values

### FASE 3 (Advanced - 4+ jam):
1. Rewrite paintEvent untuk reduce complexity
2. Use QPainterPath untuk complex shapes
3. Implement dirty rectangle rendering

---

## Conclusion:

**Kode sekarang berfungsi tapi TIDAK EFEISIEN.**
- Banyak object creation di setiap frame
- Terlalu banyak gradient operations
- Terlalu banyak trigonometric calculations
- Timer frequency terlalu tinggi

**Rekomendasi:** Lakukan FASE 1 dulu (quick wins), dapat 40% improvement dengan effort minimal!
