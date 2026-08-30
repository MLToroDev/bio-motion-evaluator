# Datos de la validación física

Aquí se depositan los **datos crudos** que produce la ejecución del protocolo
[`docs/guias/protocolo_validacion_exactitud.md`](../../docs/guias/protocolo_validacion_exactitud.md).

| Ruta | Contenido |
|------|-----------|
| `nivel1/` | Capturas y registros del patrón de referencia físico |
| `nivel1_patron.csv` | Tabla consolidada del Nivel 1: ángulo verdadero frente a ángulo medido |
| `nivel2_kinovea.csv` | Tabla del Nivel 2: serie del sistema con la columna manual de Kinovea rellenada |

Los ficheros están vacíos mientras el protocolo no se ejecute. **No se inventan datos:**
un archivo ausente significa que esa medición no se ha realizado.

Para analizar los datos una vez tomados:

```bash
cd backend && PYTHONPATH=. python -c "
import sys; sys.path.insert(0, '../validacion')
from analisis.acuerdo import resumen_acuerdo
"
```

Ver `validacion/analisis/acuerdo.py` para el detalle de los estadísticos disponibles.
