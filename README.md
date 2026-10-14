# Mingo Risk Monitor

데구르르 체크리스트의 매크로 11개 + AI 11개 위험 항목을 공식 소스 중심으로 매일 수집하고, 재현 가능한 규칙으로 G/A/R/B를 판정하는 정적 대시보드입니다.

## 핵심 원칙

- **G/A/R은 숫자 규칙으로만 판정**합니다. 응답 실패, 필드 변경, 검증 불가 정성 지표는 **B**입니다.
- 모든 판정에는 소스 URL, 관측일, 수집시각, 원자료 값, 판정 이유를 저장합니다.
- `2026-10-14`의 `54.5 / 59 / 50`은 `data/reference/2026-10-14.json`에만 보존되며 라이브 이력과 점수 계산에 포함되지 않습니다.
- GitHub Actions의 cron은 UTC 기준 `00:00` = KST `09:00`입니다.

## 구조

```text
collector/              수집·검증·판정 엔진
config/indicators.json  22개 항목과 공식 소스/규칙
data/history/           일별 검증 가능한 스냅샷
data/latest.json        최신 라이브 스냅샷
data/reference/         과거 참고 스냅샷(라이브와 분리)
docs/                   GitHub Pages 다크 대시보드
tests/                  판정 및 안전장치 테스트
```

## 로컬 실행

Python 3.11+만 필요합니다(외부 패키지 없음).

```bash
python -m collector.run
python -m unittest discover -s tests -v
python -m http.server 8000 -d docs
```

네트워크 없이 구조만 검증하려면:

```bash
python -m collector.run --fixture tests/fixtures/observations.json --date 2026-10-15
```

## GitHub 설정

1. 저장소 Settings → Pages → Source를 **GitHub Actions**로 설정합니다.
2. Actions에 `contents: write`, Pages 배포에 `pages: write`, `id-token: write` 권한이 필요하며 워크플로에 선언되어 있습니다.
3. 첫 실행은 Actions → **Daily risk monitor** → Run workflow로 수동 실행해 확인합니다.

## 판정 모델

- 항목별 점수: G=0, A=1, R=2, B=제외
- 축/종합 부담률: 검증된 항목 점수의 평균을 0–100으로 환산
- 확인률: G/A/R 판정 항목 수 ÷ 전체 항목 수
- B가 많을수록 점수보다 확인률을 먼저 보도록 UI에 표시합니다.

세부 규칙과 임계값은 [`config/indicators.json`](config/indicators.json)에 공개되어 있어 판정을 재현할 수 있습니다.

## 현재 자동화 범위

22개 전 항목을 FRED가 배포하는 연준·재무부·EIA·BLS·BEA·Census 등 공식 통계로 자동 판정합니다. 직접 관측이 어려운 정성 개념은 주문, 신용비용, 산업이익, 재고/출하, 생산자물가, 완제품재고, 시장 위험선호 같은 운영 대리변수로 치환했습니다. 각 카드에 대리변수와 해석 한계를 노출하며, 공식 소스 수집 자체가 실패한 경우에만 B가 됩니다.

