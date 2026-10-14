# Mingo Risk Monitor

데구르르 체크리스트의 매크로 11개 + AI 11개를 원본 구조대로 보여주고, 별도의 공식통계 자동 프록시를 매일 갱신하는 정적 대시보드입니다.

## 핵심 원칙

- **원본 체크리스트**는 PDF의 2026-10-14 판정(54.5 / 59 / 50), 세부 확인요소, 근거, 완화·강화 조건을 보존합니다.
- **자동 프록시 보조지표**는 숫자 규칙으로만 판정하며, 응답 실패나 검증 불가 데이터는 **B**입니다.
- 모든 판정에는 소스 URL, 관측일, 수집시각, 원자료 값, 판정 이유를 저장합니다.
- `2026-10-14`의 `54.5 / 59 / 50`은 원본 체크리스트 화면의 기본 판정이며 자동 프록시 이력과 계산에는 포함되지 않습니다.
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

## 두 지수의 관계

- 원본 체크리스트: 작성자의 정성·정량 판단을 보존한 기준 스냅샷입니다. 22개 카드 내부의 다중 체크, 판정, 완화·강화 조건, 가격 반응 보드와 한국 디스카운트 보조축을 포함합니다.
- 자동 프록시: FRED가 배포하는 연준·재무부·EIA·BLS·BEA·Census 등의 공식 통계를 이용하는 별도 보조지표입니다. 원본 판정을 대체하거나 같은 시계열로 연결하지 않습니다.
- PDF 작성자의 새로운 판정이 제공되지 않는 한 원본 점수는 자동으로 바뀌지 않습니다. 자동 작업은 보조지표만 매일 09:00 KST에 갱신합니다.

