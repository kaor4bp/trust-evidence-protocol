# Trust Evidence Protocol

Trust Evidence Protocol (TEP) es un runtime de memoria y razonamiento
evidence-first para agentes de programación.

TEP ayuda a que un agente no trate la memoria del chat, las suposiciones, los
índices generados o las observaciones antiguas como pruebas. Separa las
afirmaciones respaldadas por fuentes de permisos, restricciones, directrices,
tareas, contexto de trabajo, planes, deuda, propuestas e hipótesis.

## Qué Proporciona TEP

- Contexto persistente y estructurado para el trabajo del agente.
- Registros canónicos de fuentes `SRC-*` y afirmaciones `CLM-*`.
- Ciclo de vida para hechos activos, resueltos, históricos y archivados.
- Registros explícitos de planes, deuda técnica, preguntas abiertas,
  propuestas y contexto de trabajo.
- Índices generados para búsqueda, navegación por código, prefiltrado temático
  y comprobaciones lógicas.
- Integración como plugin de Codex con hooks, comandos CLI, skill y herramientas
  MCP de solo lectura.
- Pruebas de comportamiento determinista del runtime y conformidad de agentes
  reales.

## Estructura Actual

El plugin de Codex se mantiene en:

```text
plugins/trust-evidence-protocol/
```

Esta estructura conserva el layout probado del plugin mientras el runtime se
divide en módulos más pequeños.

## Modelo de Seguridad

TEP no convierte la memoria en verdad de forma automática.

Las vistas e índices generados ayudan al agente a encontrar registros, pero la
prueba debe resolverse en afirmaciones canónicas respaldadas por fuentes. Las
afirmaciones históricas o resueltas siguen siendo buscables, pero no deben
dominar el razonamiento actual.

## Más Documentación

- [Developer docs](../dev/README.md)
- [Reference docs](../reference/README.md)
- [Research docs](../research/README.md)
