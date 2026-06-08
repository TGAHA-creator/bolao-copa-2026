# Bolão Copa 2026 — Routine spec (source of truth for the daily email)

**Scheduler:** GitHub Actions cron in `.github/workflows/daily-bolao-email.yml` — `5 5 * * *` UTC = **09:05 Asia/Dubai (GST, UTC+4)**, daily.
**Generator:** `scripts/send_daily_email.py` calls the Anthropic API with THIS file as the source of truth, then delivers via SMTP.
**Repo:** github.com/TGAHA-creator/bolao-copa-2026 (private). Storage files: `/log.md`, `/predictions/<YYYY-MM-DD>.json`, optional `/data/`.
**Delivery:** FROM the SMTP_USER account (e.g. tiagogsa@gmail.com) TO **tiagogsa@yahoo.com.br** — VERIFY this address in the workflow/secrets; do not send to "tiagosa@" (missing the "g").
**Language:** write the ENTIRE email in **Brazilian Portuguese**. Treat all kickoff times in Asia/Dubai (GST, UTC+4). "Today" = the run date.

---

## SCORING ("Sistema Mais Justo e Equilibrado")
- You score ONLY if you pick the correct outcome (team win or draw). Wrong outcome = 0, no partial credit.
- BASE points = 1..13, scaled INVERSELY to the picked outcome's win probability (bigger underdog = more points). Calibration: heavy favorite ≈ 1–2; ~50% ≈ 3; ~30% ≈ 5; ~15–20% ≈ 8–10; <10% approaching 13. Use de-vigged market/consensus probability as the proxy for the app's number (app refreshes hourly from aggregated public stats).
- ADDITIVE bonuses on a correct outcome: exact score +5; correct winner's goals +3; correct goal difference +2; correct loser's goals +1; correctly called a goleada/blowout (margin ≥3) +1.
- Knockout extra time +3; penalties +3.
- The FINAL (last game of the tournament) is DOUBLE total points.
- If any rule detail is uncertain, STATE the assumption — do not invent it.

## STEP 1 — GRADE & LEARN
Read /log.md and /predictions/*.json. For every predicted match since played and not yet graded: web-search the final result, compute points earned under the scoring above, classify the miss (wrong outcome / right outcome–wrong score / partial / exact), note likely cause in one line. Append each graded match to /log.md and update a rolling LESSONS list (max 10 bullets) at the top of /log.md. Carry today's lessons into Step 3. (On the first run no predictions exist yet — nothing to grade.)

## STEP 2 — SCOPE
Web-search the World Cup 2026 schedule; list every match kicking off in the next 24–36h (the next match day) with kickoff converted to Asia/Dubai. If none, send a single-line email ("Nenhum jogo na janela") and stop.

## STEP 3 — PREDICT EACH MATCH (today's data only)
Research FIFA ranking + World Football Elo; last 5–6 results per side weighted to recent games vs strong opponents; injuries, suspensions, card carryover, missing starters; context (host effect USA/Mexico/Canada, Mexico City altitude, heat, rest days, travel); current bookmaker odds AND any Polymarket price → de-vig into consensus probability per outcome. Model it: estimate xG per side; Poisson scoreline grid for P(exact scores), P(margins), P(win/draw/loss)=P_model. Choose the bolão pick (EV-optimal): for each outcome EV ≈ P_model(outcome) × BasePoints(P_consensus(outcome)); pick the highest-EV outcome (favors outcomes the model rates above consensus, esp. underdogs, while P_model stops hopeless longshots). Then set exact SCORE = most likely scoreline given the chosen outcome (captures +5/+3/+2/+1); if model expects margin ≥3, predict the blowout for +1. Knockouts: if a regulation draw is likely, flag the extra-time/penalty angle (+3/+3). The final is double — put the strongest edge there. Apply today's LESSONS before finalizing.

## STEP 4 — LOG
Write today's picks to /predictions/<YYYY-MM-DD>.json (match, outcome pick, exact score, P_model, P_consensus, est base pts, est total pts). Commit & push (the workflow must have write permission) so tomorrow's Step 1 can grade them.

## STEP 5 — EMAIL (pt-BR)
Subject: "Bolão Copa 2026 — palpites para <data> (<n> jogos)". Body:
1) Placar de ontem — pontos ganhos, retrospecto (exato/parcial/erro), e os 1–2 ajustes de hoje.
2) Um card por jogo:
   ⚽ TIME A vs TIME B   (início <hora> GST · <estádio>)
   ENTRAR:  <Resultado>  |  placar <X–Y>   ~<total> pts  (base <b> + bônus)
   Modelo:    A xx% · Empate xx% · B xx%
   Consenso:  A xx% · Empate xx% · B xx%   ↳ edge: <onde discordo e por que paga>
   xG: A x.x · B x.x    Outros placares prováveis: 1-1 (xx%), 2-0 (xx%)
   Porquê: <3–4 fatores>   Leitura: <2 frases>
3) Rodapé: estimativa probabilística; para o bolão, não é aposta.

## ASSUMPTIONS (baseline — state any others used)
WC2026 opener June 11, 2026 (Estádio Azteca); final July 19, 2026 (MetLife) = double points. Base-points scale: heavy fav 1–2 · ~50% → 3 · ~30% → 5 · ~15–20% → 8–10 · <10% → up to 13.
