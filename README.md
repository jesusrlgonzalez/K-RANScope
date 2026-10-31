# RANScope · Inteligencia de calidad para redes de telecomunicaciones

**Proporcionar información analítica para identificar degradaciones potenciales en redes móviles y ayudar a los ingenieros a priorizar diagnósticos técnicos.**

## Qué resuelve
Integrar, depurar y analizar datos técnicos de red, detectar señales de degradación y proporcionar explicaciones verificables para los equipos responsables de calidad del servicio.

Auditoría de contadores de red móvil (RAN/QoE): valida mediciones por celda y ventana, detecta defectos y ordena celdas para diagnóstico de ingeniería.

## Hacia dónde va
Ser una plataforma de inteligencia analítica que conecte métricas de infraestructura radio, calidad de experiencia y modelos predictivos para apoyar la gestión de redes.

**Objetivo:** Desarrollar un sistema que audite indicadores RAN y evalúe modelos de priorización de celdas mediante validaciones independientes por sitio y periodo temporal.

**Valor que persigue:** Reducir tiempo de diagnóstico y mejorar la priorización de intervenciones de red.

## Resultados de la demo
Sobre un conjunto de datos sintéticos diseñado con errores y casos difíciles: **11 470 registros de contadores RAN: 285 defectos inyectados y 285 detectados (cobertura 100 %), modo de solo lectura**.

## Pruébalo en 2 minutos
```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py test     # 81 tests automatizados
python run.py demo     # demo de punta a punta → demo_output/
python run.py api      # API REST → http://127.0.0.1:8000/docs
```

## Diseñado para decisiones responsables
- **Siempre con una persona al mando:** no aplica configuraciones RAN; una alerta no es un incidente.
- **Trazable:** cada registro conserva su motivo de aceptación, revisión o cuarentena.
- **Probado:** 81 tests automatizados en Linux y Windows en cada cambio.
- **Contenedor:** la imagen Docker se construye en cada cambio.

## Estado
Prototipo funcional demostrado con datos sintéticos. El siguiente paso es un **piloto con datos reales** de su organización, bajo acuerdo de uso y confidencialidad.

**¿Le interesa un piloto?** Contacte a **Kriter Systems**.

---
I35 · Kriter Systems · Los datos incluidos son sintéticos y no representan a personas ni empresas reales.
