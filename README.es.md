<h1 align="center">bitácora · tus hábitos, sin app</h1>

<p align="center">
  <b>Dile a tu agente de IA lo que hiciste hoy. Lleva tus trackers, tus rachas y tu cuadrícula del mes, y una vez
  al mes te acompaña a revisarlo, como la migración de un bullet journal.</b>
</p>

<p align="center">
  <a href="https://github.com/howware/bitacora/actions/workflows/ci.yml"><img src="https://github.com/howware/bitacora/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/versión-0.1.0-blue" alt="Versión 0.1.0">
  <a href="https://howware.org/es/"><img src="https://img.shields.io/badge/howware-0.2-5a45d6" alt="howware 0.2"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/licencia-Apache%202.0-green" alt="Apache 2.0">
</p>

<p align="center"><a href="README.md">English</a> · <a href="docs/building.md">Cómo se construyó</a></p>

> **Un [howware](https://howware.org/es/):** tu saber hacer, puesto a trabajar con IA. Aquí el saber hacer son los
> trackers de un bullet journal y **tus propias decisiones**: qué registras, con qué meta y por qué. No hay app ni
> casillas que dibujar: tú lo dices, una herramienta pequeña mantiene exactos los números y una memoria que es tuya
> lo guarda todo.

```text
› Anoche dormí como seis y media, fui al gym y regué las plantas.
✓ Domingo 11: sueño 6 h 30 min, gym sí, regar sí.

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
| «¿Cómo voy con el gym?» · «Enséñame el mes» | **Rachas, cumplimiento y promedios**, y la **cuadrícula del mes** en texto |
| (al empezar el mes) | Te ofrece la **reflexión mensual**: los números, qué salió bien, qué no, qué trackers siguen, cambian o se retiran (la *migración*), una intención y hasta dos coincidencias de tu propio registro |

**No te pide que anotes.** Escribir es parte del hábito: un día sin registro se queda vacío, y no cuenta como fallo.
La herramienta lleva aparte cuántos días escribiste, y cuántos de ellos llenaste después.

**Está diseñado para no dar consejos de salud.** Registra, cuenta y te muestra tus datos. Las coincidencias («los días que fuiste al
gym, tu ánimo promedió 3.8 contra 2.9») son eso, coincidencias en tu registro, no causas.

## Cómo funciona

| Parte | Aquí |
|---|---|
| Protocolo | [`skill/bitacora/SKILL.md`](skill/bitacora/SKILL.md): el método y las reglas para el agente, en palabras claras |
| Herramienta | [`bitacora.py`](skill/bitacora/scripts/bitacora.py): solo lo que debe ser exacto: la fecha, validar cada valor contra su tracker, un registro por tracker y día, rachas, cumplimiento, huecos, la cuadrícula y las coincidencias |
| Memoria | El adaptador [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI): tus trackers, tus registros y tus reflexiones, en un archivo local, con historia |

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

## Privacidad y límites

| Diseñado para quedarse en tu computadora | Lo que ve el agente de IA |
|---|---|
| El archivo de la memoria con tus trackers, los registros de cada día y tus reflexiones | Tus trackers, sus metas y por qué los llevas; los valores, rachas y estadísticas cuando los consulta; el texto de tus reflexiones; lo que escribes |

**Lo que no puede hacer ni garantizar:**
- Lo que ve el agente sale de tu computadora hacia tu proveedor de IA, bajo sus términos. Algunos hábitos (el sueño,
  el ánimo) pueden ser datos de salud: registra solo lo que estés dispuesto a compartir con él.
- El archivo de la memoria no está cifrado.
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
