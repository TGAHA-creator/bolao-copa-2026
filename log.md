# Bolão Copa 2026 — Log

## LESSONS (rolling, máx. 10)
- L01: Em oitavas de final com favorito pesado (~76%), o VE do empate (base 8 pts × 18%) supera marginalmente o VE da vitória favorita (base 2 pts × 72%) — apostar no empate é matematicamente ótimo nessa faixa de probabilidade. **[REVISADO por L06: margem muito pequena; favorito preferível]**
- L02: Espanha manteve zero gols sofridos em toda a fase de grupos — sua defesa é a referência do torneio; projetar xG da Áustria com cautela (máx 0.6–0.8).
- L03: Áústria não conseguiu clean sheet em 12 jogos seguidos de Copa — mesmo contra a Espanha, algum gol austríaco deve ser considerado possível. **[Áustria ficou em 0 gols — L03 refutada vs Espanha; L02 confirmada]**
- L04: O modelo Poisson base não considera variâncias de knockout (pressão, margem de segurança, gestão de placares) — jogos eliminatórios tendem a ser mais fechados que a média da fase de grupos sugere. **[REVISADO por L09: Argentina–Egito mostrou o oposto — virada caótica de 3-2; jogos eliminatórios podem ser explosivos]**
- L05: Quando o favorito tem lesão no jogador-chave (ex. Salah com distensão muscular), reduzir o xG ofensivo em 10–20% e reavaliar o VE do azarão — base points mais altos do azarão podem inverter o pick ótimo mesmo com diferença de ranking modesta.
- L06: Margem de VE inferior a 0,05 unidades não justifica apostar no azarão — defaultar para o favorito. (Aprendizado: Espanha vs Áustria, VE draw=1,46 vs VE win=1,44 → apostamos no empate → Espanha venceu 3-0.)
- L07: Com xG ofensivo alto do favorito (≥2,1) e defesa adversária vulnerável, goleada é mais provável que o modelo base projeta — considerar 3-0 como placar alternativo em vez de 1-1. (Aprendizado: Espanha 3-0 Áustria foi subestimada.)
- L08: Times do segundo nível se defendem profundamente em eliminatórias e equilibram mais do que o xG sugere — Egito resistiu 120 minutos vs Austrália, mostrando resiliência acima da projeção.
- L09: Mesmo com jogador-chave ausente (Fattouh) e candidato ao título na frente, o time azarão pode colocar 2 gols. Substitutos inesperados (Mostafa Zico) podem suprir ausências — não zerar o xG do azarão mesmo com múltiplos desfalques. Argentina foi 0-2 abaixo antes de virar 3-2.
- L10: A Copa do Mundo de 2026 encerrou-se em 19/07/2026 com Espanha 1-0 Argentina (prorrogação). Não há mais jogos para prever neste torneio.

## Histórico de jogos avaliados

### 2026-07-01 (palpites) — jogo em 2026-07-02 23:00 GST
- **Espanha vs Áustria** | Palpite: Empate 1-1 | Real: **Espanha 3-0** | **0 pts** | Erro: resultado errado. VE draw (1,46) vs vitória Espanha (1,44) — margem de 0,02 unidades justificou o azarão matematicamente, mas foi insuficiente na prática. Espanha fez goleada com Oyarzabal (2x) e Porro. Lição → L06, L07.

### 2026-07-02 (palpites) — jogo em 2026-07-03 22:00 GST
- **Austrália vs Egito** | Palpite: Austrália 1-0 | Real: **1-1 (Egito pênaltis 4-2)** | **0 pts** | Erro: resultado errado. Apostamos na vitória australiana; Egito resistiu 120 minutos com Salah abaixo do nível, classificou nos pênaltis. Lição → L08.

### 2026-07-06 (palpites) — jogo em 2026-07-07 20:00 GST
- **Argentina vs Egito** | Palpite: Argentina 2-0 | Real: **Argentina 3-2** | **2 pts** | Resultado correto (vitória argentina), placar errado. Argentina foi 0-2 abaixo até o min. 79 (gols de Mostafa Zico, substituto inesperado), depois virou com gols de Romero (79'), Messi (83') e Enzo Fernández (90+2'). Nenhum bônus de placar/gols/margem conquistado. Lição → L09.

### 2026-09-21 (avaliação final de temporada) — Copa do Mundo 2026 encerrada
- **Campeã:** Espanha 1-0 Argentina (prorrogação) — MetLife Stadium, 19/07/2026.
- **Pontuação total da temporada:** 2 pts | Resultados corretos: 1 de 3 | Placares exatos: 0 de 3.
- Nenhum jogo previsto após esta data — torneio encerrado.
