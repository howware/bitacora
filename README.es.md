<h1 align="center">bitácora · tu bullet journal, sin app</h1>

<p align="center">
  <b>Dile a tu agente de IA lo que hiciste y lo que pasó hoy. Lleva tus hábitos, tus notas y tus colecciones, y
  una vez al mes te acompaña a revisarlo, como la migración de un bullet journal.</b>
</p>

<p align="center">
  <a href="https://github.com/howware/bitacora/actions/workflows/ci.yml"><img src="https://github.com/howware/bitacora/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/versión-0.2.0-blue" alt="Versión 0.2.0">
  <a href="https://howware.org/es/"><img src="https://img.shields.io/badge/howware-0.2-5a45d6" alt="howware 0.2"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/licencia-Apache%202.0-green" alt="Apache 2.0">
</p>

<p align="center"><a href="README.md">English</a> · <a href="docs/building.md">Cómo se construyó</a></p>

> **Un [howware](https://howware.org/es/):** tu saber hacer, puesto a trabajar con IA. Aquí el saber hacer son los
> trackers, las notas y las colecciones de un bullet journal, y **tus propias decisiones**: qué registras, con qué
> meta y por qué. No hay app ni
> casillas que dibujar: tú lo dices, una herramienta pequeña mantiene exactos los números y una memoria que es tuya
> lo guarda todo.

```text
› Anoche dormí como seis y media, fui al gym y fue la boda de mi primo. Se me ocurrió hacer un jardín vertical.
✓ Domingo 11: sueño 6 h 30 min, gym sí.
  ○ Fue la boda de mi primo · ! Hacer un jardín vertical

› Terminé Rayuela, le pongo 4. ¿Cuántos libros llevo este año?
✓ Libros: Rayuela, leído el 11 de oct, 4/5. Este año: 7 leídos, promedio 4.1/5.

› Enséñame septiembre.
         123456789012345678901234567890
         mmjvsdlmmjvsdlmmjvsdlmmjvsdlmm
Sueño    ○●●○●●○○●○○·○○●●○●●○○●○○●○○●●○
Gimnasio ●●●○○○●●●●○·○●●●●○○○●●●●○○○●●●
Regar    ○○●○○●○○●○○·○○●○○●○○●○○●○○●○○●
escrito  ●●●●●●●●●●●·●●●●●●●●●●●●●●●●●●
  ● hecho · ○ registrado, sin llegar a la meta · · sin dato

› (1 de octubre) 
  ¿Hacemos la reflexión de septiembre?
```

## Qué hace

| Dices | Hace |
|---|---|
| «Quiero llevar cuántas horas duermo, mi meta son 7» | Crea un **tracker** contigo: su tipo (cantidad, sí/no o escala del 1 al 5), su unidad y su meta, que es opcional (diaria, N veces por semana o cada N días) |
| «Dormí 6 y media, fui al gym» | **Registra** el día en una línea y te lo confirma con la fecha y los valores exactos |
| «Fue la boda de mi primo» · «Se me ocurrió…» | Guarda una **nota** del día con tus palabras y su signo: `–` nota, `○` evento, `!` idea, `*` importante. El agente elige el tipo y tú lo corriges; los tipos y sus signos son tuyos (por ejemplo, `♡` gratitud) |
| «¿Cuándo fue que fui a Guanajuato?» | **Busca** en tus notas, sin importar acentos ni mayúsculas |
| «Quiero llevar los libros que leo» · «Terminé Rayuela» | **Colecciones** que vas armando (libros, películas, ideas, lugares…), con los estados que elijas, una calificación y la fecha en que terminaste algo; «¿cuántos leí este año?» lo cuenta la herramienta |
| «Tengo que llamar al plomero» | Si usas también [todo](https://github.com/howware/todo) en la misma carpeta, va a tus **pendientes**; si no, queda como nota `•` |
| «¿Cómo voy con el gym?» · «Enséñame el mes» | **Rachas, cumplimiento y promedios**, y la **cuadrícula del mes** en texto |
| (al empezar el mes) | Te ofrece la **reflexión mensual**: los números, tus notas y colecciones del mes, qué salió bien, qué no, qué sigue (la *migración*), una intención, **tres momentos del mes** que eliges de tus notas y hasta dos coincidencias de tu propio registro |

**No te pide que anotes.** Escribir es parte del hábito: un día sin registro ni notas se queda vacío, y no cuenta
como fallo.
La herramienta lleva aparte cuántos días escribiste, y cuántos de ellos llenaste después.

**Está diseñado para no dar consejos de salud.** Registra, cuenta y te muestra tus datos. Las coincidencias («los días que fuiste al
gym, tu ánimo promedió 3.8 contra 2.9») son eso, coincidencias en tu registro, no causas.

## Cómo funciona

| Parte | Aquí |
|---|---|
| Protocolo | [`skill/bitacora/SKILL.md`](skill/bitacora/SKILL.md): el método y las reglas para el agente, en palabras claras |
| Herramienta | [`bitacora.py`](skill/bitacora/scripts/bitacora.py): solo lo que debe ser exacto: la fecha, validar cada valor contra su tracker, un registro por tracker y día, una nota por texto y día, rachas, cumplimiento, huecos, la búsqueda, los estados y conteos de las colecciones, la cuadrícula y las coincidencias |
| Memoria | El adaptador [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI): todo tu diario, en un archivo local, con historia. Puede ser la misma memoria de [todo](https://github.com/howware/todo): así tus pendientes y tu bitácora viven juntos |

## Instalación

```bash
git clone https://github.com/howware/long-term-memory-for-AI
python long-term-memory-for-AI/tools/install_skill.py --target ~/.claude/skills/project-memory
git clone https://github.com/howware/bitacora
python bitacora/tools/install_skill.py
```

Crea una carpeta para tu bitácora, abre ahí Claude Code (agrega a su `CLAUDE.md` la instrucción de memoria
persistente de [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI/blob/main/README.es.md#configurar-un-proyecto))
y di *«Quiero llevar mi bitácora aquí.»*

**¿Ya usas la 0.1?** Reinstala el skill; en la siguiente conversación el agente corre `setup` solo y conserva todo.
**¿Quieres tu bitácora junto con tus pendientes de `todo`?** En la carpeta de `todo`, `bitacora.py copy-from` copia tu
bitácora completa (no duplica si lo corres dos veces y no toca la carpeta original); el agente te guía.

## Privacidad y límites

| Diseñado para quedarse en tu computadora | Lo que ve el agente de IA |
|---|---|
| El archivo de la memoria con tus trackers, los registros de cada día, tus notas, tus colecciones y tus reflexiones | Tus trackers, sus metas y por qué los llevas; los valores, rachas y estadísticas cuando los consulta; tus notas y colecciones cuando las consulta o busca; el texto de tus reflexiones; lo que escribes |

**Lo que no puede hacer ni garantizar:**
- Lo que ve el agente sale de tu computadora hacia tu proveedor de IA, bajo sus términos. Algunos hábitos (el sueño,
  el ánimo) pueden ser datos de salud: registra solo lo que estés dispuesto a compartir con él.
- El archivo de la memoria no está cifrado.
- **Borrar oculta, no elimina:** una nota o un elemento borrado deja de aparecer, pero sigue en el archivo de la
  memoria, marcado como anulado.
- **No hay notificaciones.** La reflexión se ofrece cuando abres una conversación.
- El protocolo le indica al agente no dar consejos de salud, pero las respuestas de una IA no se pueden
  garantizar; sus patrones no son causas.

## Desarrollo

```bash
python -m unittest discover -s tests -v
git ls-files -z | xargs -0 python tools/check_private_data.py
```

Las pruebas usan solo datos sintéticos. Ver [AGENTS.md](AGENTS.md).

## Licencia

[Apache 2.0](LICENSE). Sin afiliación con Ryder Carroll; Bullet Journal® es su marca.
