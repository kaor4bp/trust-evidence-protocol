# Trust Evidence Protocol

Trust Evidence Protocol (TEP) este un runtime de memorie și raționament
evidence-first pentru agenți de programare.

TEP ajută agentul să nu trateze memoria conversației, presupunerile, indicii
generați sau observațiile vechi ca dovezi. Separă afirmațiile susținute de
surse de permisiuni, restricții, ghiduri, sarcini, context de lucru, planuri,
datorii tehnice, propuneri și ipoteze.

## Ce Oferă TEP

- Context persistent și structurat pentru munca agentului.
- Înregistrări canonice de surse `SRC-*` și afirmații `CLM-*`.
- Lifecycle pentru fapte active, rezolvate, istorice și arhivate.
- Înregistrări explicite pentru planuri, datorii tehnice, întrebări deschise,
  propuneri și context de lucru.
- Indici generați pentru căutare, navigare prin cod, prefiltrare tematică și
  verificări logice.
- Integrare ca plugin Codex cu hooks, comenzi CLI, skill și instrumente MCP
  read-only.
- Teste pentru comportamentul determinist al runtime-ului și conformitatea
  agenților reali.

## Structura Actuală

Pluginul Codex este păstrat aici:

```text
plugins/trust-evidence-protocol/
```

Această structură păstrează layout-ul testat al pluginului în timp ce runtime-ul
este împărțit în module mai mici.

## Modelul de Siguranță

TEP nu transformă memoria automat în adevăr.

View-urile și indicii generați ajută agentul să găsească înregistrări, dar
dovada trebuie să ajungă la afirmații canonice susținute de surse. Afirmațiile
istorice sau rezolvate rămân căutabile, dar nu trebuie să domine raționamentul
curent.

## Mai Multă Documentație

- [Developer docs](../dev/README.md)
- [Reference docs](../reference/README.md)
- [Research docs](../research/README.md)
