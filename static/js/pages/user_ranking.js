// static/js/pages/user_ranking.js
document.addEventListener("DOMContentLoaded", () => {
    const rankBtn = document.querySelector('.sort-chip[data-sort="rating"]');
    console.log("랭킹 버튼 확인:", rankBtn);

    if (rankBtn) {
        rankBtn.addEventListener("click", async () => {
            console.log("랭킹 탭 클릭됨!");

            // 1. 기존 요소 숨기기
            const mapCanvas = document.getElementById("mapCanvas");
            const resList = document.getElementById("restaurantList");
            if(mapCanvas) mapCanvas.style.display = "none";
            if(resList) resList.style.display = "none";

            // 2. 랭킹 UI 보이기
            const rankingUI = document.getElementById("rankingMainWrapper");
            if (rankingUI) {
                console.log("랭킹 UI 노출 시작");
                rankingUI.style.display = "flex"; // flex로 강제 노출
                rankingUI.classList.remove("hidden");
            } else {
                console.error("오류: rankingMainWrapper를 찾을 수 없습니다!");
                return;
            }

            // 3. 데이터 로드
            await loadRankingData();
        });
    }
});

async function loadRankingData() {
    console.log("데이터 패치 시작...");
    try {
        const [listRes, meRes] = await Promise.all([
            fetch('/api/ranking/list'),
            fetch('/api/ranking/me')
        ]);

        const users = await listRes.json();
        const me = await meRes.json();
        console.log("데이터 수신 성공:", { users, me });

        // 리스트 렌더링
        const listContainer = document.getElementById("userRankingList");
        listContainer.innerHTML = users.map((u, i) => `
            <li style="display:flex; align-items:center; padding:15px; border-bottom:1px solid #eee;">
                <span style="width:30px; font-weight:bold;">${i+1}</span>
                <img src="${u.profile_image_url || '/static/img/main_logo.png'}" width="40" style="border-radius:50%; margin:0 15px;">
                <div>
                    <p style="margin:0; font-weight:bold;">${u.nickname}</p>
                    <p style="margin:0; font-size:12px; color:#888;">${(u.point || 0).toLocaleString()} P</p>
                </div>
            </li>
        `).join('');

        // 대시보드 렌더링
        document.getElementById("my-nickname").innerText = me.nickname;
        document.getElementById("my-tier").innerText = me.tier;
        document.getElementById("my-points").innerText = (me.point || 0).toLocaleString();
        
        const percent = Math.min(((me.point || 0) / 10000) * 100, 100);
        const fill = document.getElementById("my-gauge-fill");
        if(fill) fill.style.width = percent + "%";

    } catch (e) {
        console.error("데이터 렌더링 중 오류:", e);
    }
}