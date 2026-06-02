import streamlit as st
import streamlit.components.v1 as components

# 1. Page Configuration
st.set_page_config(
    page_title="반응속도 테스트 (Reaction Speed Test)",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 2. Inject CSS to hide Streamlit headers and style the container
st.markdown(
    """
    <style>
    /* Streamlit UI 요소 숨기기 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 전체 여백 조절 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    
    /* 폰트 및 제목 스타일 */
    .main-title {
        font-family: 'Outfit', 'Noto Sans KR', sans-serif;
        text-align: center;
        font-weight: 800;
        font-size: 2.5rem;
        background: linear-gradient(135deg, #4f46e5, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    
    /* 가이드 카드 스타일 */
    .guide-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #f3f4f6;
        margin-top: 1.5rem;
    }
    .guide-title {
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Render Premium Header
st.markdown('<div class="main-title">⚡ Reaction Speed Test</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">브라우저 로컬 측정 방식을 적용하여 네트워크 지연 오차가 없는 정밀 반응속도 테스트기입니다.</div>', unsafe_allow_html=True)

# 3. HTML/CSS/JavaScript Game Code (Embedded Component)
GAME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reaction Speed Test Frame</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body, html {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            font-family: 'Outfit', 'Noto Sans KR', sans-serif;
            background-color: #f3f4f6;
            display: flex;
            justify-content: center;
            align-items: center;
            user-select: none;
            overflow: hidden;
            transition: background-color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .tile-container {
            width: 90%;
            max-width: 500px;
            background: #ffffff;
            border-radius: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02);
            padding: 45px 30px;
            text-align: center;
            box-sizing: border-box;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        h1 {
            font-size: 2.2rem;
            color: #111827;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        
        p {
            font-size: 1.05rem;
            color: #4b5563;
            line-height: 1.6;
            margin-bottom: 2.5rem;
            word-break: keep-all;
        }
        
        .btn {
            background: linear-gradient(135deg, #4f46e5, #6366f1);
            color: white;
            border: none;
            padding: 14px 40px;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 12px;
            cursor: pointer;
            box-shadow: 0 10px 20px rgba(79, 70, 229, 0.15);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            outline: none;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 25px rgba(79, 70, 229, 0.3);
            filter: brightness(1.05);
        }
        
        .btn:active {
            transform: translateY(1px);
            box-shadow: 0 5px 10px rgba(79, 70, 229, 0.15);
        }

        /* Screen state styles */
        .state-active-screen {
            cursor: pointer;
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            text-align: center;
            box-sizing: border-box;
            padding: 20px;
            transition: background-color 0.15s ease;
        }

        .screen-title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 1rem;
            text-shadow: 0 4px 12px rgba(0,0,0,0.12);
            animation: pulse 1.2s infinite alternate ease-in-out;
        }

        .screen-subtitle {
            font-size: 1.25rem;
            opacity: 0.9;
            text-shadow: 0 2px 5px rgba(0,0,0,0.08);
        }

        @keyframes pulse {
            from { transform: scale(0.97); }
            to { transform: scale(1.03); }
        }

        /* Result Specifics */
        .result-val {
            font-size: 5rem;
            font-weight: 800;
            color: #4f46e5;
            margin: 1.5rem 0;
            letter-spacing: -2px;
            line-height: 1;
        }
        
        .result-unit {
            font-size: 2rem;
            font-weight: 400;
            color: #6b7280;
            margin-left: 4px;
        }

        .result-comment {
            font-size: 1.25rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 2.5rem;
        }

        .btn-group {
            display: flex;
            gap: 15px;
            justify-content: center;
        }

        .btn-secondary {
            background: #e5e7eb;
            color: #374151;
            box-shadow: none;
        }

        .btn-secondary:hover {
            background: #d1d5db;
            color: #111827;
            box-shadow: 0 5px 12px rgba(0,0,0,0.05);
        }

        /* Stats display */
        .stats-panel {
            margin-top: 30px;
            padding-top: 25px;
            border-top: 1px dashed #e5e7eb;
            display: flex;
            justify-content: space-around;
        }

        .stat-item {
            text-align: center;
        }

        .stat-label {
            font-size: 0.8rem;
            color: #6b7280;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 1.25rem;
            font-weight: 700;
            color: #111827;
        }
        
        .foul-btn-container {
            margin-top: 25px;
        }
    </style>
</head>
<body>

    <!-- Home View -->
    <div id="view-home" class="tile-container">
        <h1>반응속도 테스트</h1>
        <p>시작 버튼을 누르면 화면이 빨간색으로 변합니다.<br>이후 <b>초록색</b>으로 변하는 순간에 <b>스페이스바</b>를 가장 빠르게 누르세요!</p>
        <button class="btn" id="btn-start">테스트 시작 (Start)</button>
        
        <div class="stats-panel" id="home-stats" style="display: none;">
            <div class="stat-item">
                <div class="stat-label">최고 기록</div>
                <div class="stat-value" id="val-best">-</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">최근 평균</div>
                <div class="stat-value" id="val-avg">-</div>
            </div>

        </div>
    </div>

    <!-- Active Screen View (Red/Green/Foul) -->
    <div id="view-active" class="state-active-screen" style="display: none;">
        <div class="screen-title" id="active-title">준비...</div>
        <div class="screen-subtitle" id="active-subtitle">초록색으로 변하면 스페이스바를 누르세요!</div>
        <div class="foul-btn-container" id="foul-btn-area" style="display: none;">
            <button class="btn btn-secondary" id="btn-foul-restart" style="background: white; color: #111827;">다시 시작</button>
        </div>
    </div>

    <!-- Result View -->
    <div id="view-result" class="tile-container" style="display: none;">
        <h1>측정 결과</h1>
        <div class="result-val"><span id="result-ms">0</span><span class="result-unit">ms</span></div>
        <div class="result-comment" id="result-feedback">매우 빠릅니다!</div>
        
        <div class="btn-group">
            <button class="btn btn-secondary" id="btn-home">홈으로 (Home)</button>
            <button class="btn" id="btn-restart">다시 하기 (Restart)</button>
        </div>
    </div>

    <script>
        // State Enumeration
        const STATE_HOME = 0;
        const STATE_WAITING = 1; // Red screen
        const STATE_READY = 2;   // Green screen
        const STATE_FOUL = 3;    // Pressed too early
        const STATE_RESULT = 4;

        let currentState = STATE_HOME;
        let randomTimer = null;
        let startTime = 0;
        let scores = [];

        // DOM elements
        const viewHome = document.getElementById('view-home');
        const viewActive = document.getElementById('view-active');
        const viewResult = document.getElementById('view-result');
        
        const btnStart = document.getElementById('btn-start');
        const btnFoulRestart = document.getElementById('btn-foul-restart');
        const foulBtnArea = document.getElementById('foul-btn-area');
        const btnHome = document.getElementById('btn-home');
        const btnRestart = document.getElementById('btn-restart');
        
        const activeTitle = document.getElementById('active-title');
        const activeSubtitle = document.getElementById('active-subtitle');
        const resultMs = document.getElementById('result-ms');
        const resultFeedback = document.getElementById('result-feedback');
        
        const homeStats = document.getElementById('home-stats');
        const valBest = document.getElementById('val-best');
        const valAvg = document.getElementById('val-avg');


        // Load stats from localStorage
        function loadStats() {
            const savedScores = localStorage.getItem('reaction_scores');
            if (savedScores) {
                scores = JSON.parse(savedScores);
                updateStatsPanel();
            }
        }

        function saveScore(score) {
            scores.push(score);
            localStorage.setItem('reaction_scores', JSON.stringify(scores));
            updateStatsPanel();
        }

        function updateStatsPanel() {
            if (scores.length === 0) {
                homeStats.style.display = 'none';
                return;
            }
            homeStats.style.display = 'flex';
            const best = Math.min(...scores);
            const sum = scores.reduce((a, b) => a + b, 0);
            const avg = Math.round(sum / scores.length);
            
            valBest.innerText = best + ' ms';
            valAvg.innerText = avg + ' ms';

        }

        // State machine transitions
        function transitionTo(state) {
            currentState = state;
            
            // Hide all views
            viewHome.style.display = 'none';
            viewActive.style.display = 'none';
            viewResult.style.display = 'none';
            document.body.style.backgroundColor = '#f3f4f6';
            foulBtnArea.style.display = 'none';

            if (state === STATE_HOME) {
                viewHome.style.display = 'block';
                loadStats();
            } 
            else if (state === STATE_WAITING) {
                viewActive.style.display = 'flex';
                document.body.style.backgroundColor = '#ff4757'; // Red background
                activeTitle.innerText = '준비...';
                activeSubtitle.innerText = '초록색으로 변하면 스페이스바를 누르세요!';
                
                // Clear any existing timer
                if (randomTimer) clearTimeout(randomTimer);
                
                // Set timer for 1 to 10 seconds (1000ms to 10000ms)
                const delay = 1000 + Math.random() * 9000;
                randomTimer = setTimeout(triggerGreenScreen, delay);
            } 
            else if (state === STATE_READY) {
                viewActive.style.display = 'flex';
                document.body.style.backgroundColor = '#2ed573'; // Green background
                activeTitle.innerText = '지금 누르세요!!!';
                activeSubtitle.innerText = '스페이스바!!!';
                startTime = performance.now();
            } 
            else if (state === STATE_FOUL) {
                if (randomTimer) clearTimeout(randomTimer);
                viewActive.style.display = 'flex';
                document.body.style.backgroundColor = '#f59e0b'; // Amber warning background
                activeTitle.innerText = '부정 출발!';
                activeSubtitle.innerText = '초록색으로 변하기 전에 누르면 안 됩니다!';
                foulBtnArea.style.display = 'block';
            } 
            else if (state === STATE_RESULT) {
                viewResult.style.display = 'block';
            }
        }

        function triggerGreenScreen() {
            transitionTo(STATE_READY);
        }

        function handleAction() {
            if (currentState === STATE_WAITING) {
                // Pressed during red screen -> Foul
                transitionTo(STATE_FOUL);
            } 
            else if (currentState === STATE_READY) {
                // Pressed during green screen -> Success!
                const elapsed = Math.round(performance.now() - startTime);
                resultMs.innerText = elapsed;
                
                // Set feedback text and colors
                let feedback = "";
                let color = "#4f46e5";
                if (elapsed < 180) {
                    feedback = "신급 반응 속도! 엄청난 동체시력입니다 ⚡";
                    color = "#10b981"; // Emerald green
                } else if (elapsed < 240) {
                    feedback = "매우 빠름! 뛰어난 반사신경입니다 🚀";
                    color = "#3b82f6"; // Blue
                } else if (elapsed < 300) {
                    feedback = "평균 속도! 준수한 편입니다 👍";
                    color = "#f59e0b"; // Amber
                } else {
                    feedback = "평균보다 살짝 느립니다. 집중해서 다시 해봐요! 🐢";
                    color = "#ef4444"; // Red
                }
                
                resultFeedback.innerText = feedback;
                document.querySelector('.result-val').style.color = color;
                
                saveScore(elapsed);
                transitionTo(STATE_RESULT);
            }
        }

        // Event Listeners
        btnStart.addEventListener('click', () => {
            transitionTo(STATE_WAITING);
        });

        btnFoulRestart.addEventListener('click', (e) => {
            e.stopPropagation(); // Click should not trigger active screen action
            transitionTo(STATE_WAITING);
        });

        btnHome.addEventListener('click', () => {
            transitionTo(STATE_HOME);
        });

        btnRestart.addEventListener('click', () => {
            transitionTo(STATE_WAITING);
        });

        // Keydown listener for spacebar
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' || e.key === ' ') {
                e.preventDefault(); // Stop page scrolling
                
                if (currentState === STATE_FOUL) {
                    transitionTo(STATE_WAITING);
                } else {
                    handleAction();
                }
            }
        });

        // Click on the screen as alternative
        viewActive.addEventListener('mousedown', (e) => {
            if (e.target !== btnFoulRestart) {
                handleAction();
            }
        });

        // Initialize
        transitionTo(STATE_HOME);
    </script>
</body>
</html>
"""

# 4. Render Game Frame in Streamlit
components.html(GAME_HTML, height=650, scrolling=False)

# 5. Statistics Guide
st.markdown(
    """
    <div class="guide-card">
        <div class="guide-title">💡 반응 속도 수준 참고표</div>
        <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.95rem;">
            <tr style="border-bottom: 1px solid #f3f4f6; color: #6b7280;">
                <th style="padding: 8px;">반응 시간</th>
                <th style="padding: 8px;">등급</th>
                <th style="padding: 8px;">설명</th>
            </tr>
            <tr style="border-bottom: 1px solid #f3f4f6;">
                <td style="padding: 8px; font-weight: 700; color: #10b981;">180 ms 미만</td>
                <td style="padding: 8px;">신급 (Godlike)</td>
                <td style="padding: 8px; color: #4b5563;">프로게이머 혹은 타고난 반사신경</td>
            </tr>
            <tr style="border-bottom: 1px solid #f3f4f6;">
                <td style="padding: 8px; font-weight: 700; color: #3b82f6;">180 ~ 240 ms</td>
                <td style="padding: 8px;">매우 빠름 (Excellent)</td>
                <td style="padding: 8px; color: #4b5563;">상위권의 반사신경 소유자</td>
            </tr>
            <tr style="border-bottom: 1px solid #f3f4f6;">
                <td style="padding: 8px; font-weight: 700; color: #f59e0b;">240 ~ 300 ms</td>
                <td style="padding: 8px;">평균 (Average)</td>
                <td style="padding: 8px; color: #4b5563;">인간 평균 수준 (평균 약 250ms)</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: 700; color: #ef4444;">300 ms 초과</td>
                <td style="padding: 8px;">연습 필요 (Slow)</td>
                <td style="padding: 8px; color: #4b5563;">피로도가 높거나 연습이 필요한 상태</td>
            </tr>
        </table>
    </div>
    """,
    unsafe_allow_html=True
)
