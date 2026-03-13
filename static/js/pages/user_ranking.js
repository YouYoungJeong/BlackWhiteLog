document.addEventListener("DOMContentLoaded", () => {
    // =========================================================
    // 1. DOM 분리 및 이동 (index.html 구조를 건드리지 않는 마법)
    // =========================================================
    const sidebar = document.querySelector('.sidebar');
    const mapPanel = document.querySelector('.map-panel');
    
    const rankingListOverlay = document.getElementById('rankingListOverlay');
    const rankingDashboardOverlay = document.getElementById('rankingDashboardOverlay');
    // 뱃지 오버레이
    const badgeChangeOverlay = document.getElementById('badgeChangeOverlay');
    // 왼쪽 랭킹 리스트는 sidebar 영역으로 강제 이동
    if (sidebar && rankingListOverlay) {
        sidebar.appendChild(rankingListOverlay);
    }

    // 오른쪽 대시보드는 mapPanel 영역으로 강제 이동
    if (mapPanel && rankingDashboardOverlay) {
        mapPanel.appendChild(rankingDashboardOverlay);
    }

    // 뱃지 오버레이 지도 패널
    if (mapPanel && badgeChangeOverlay) {
        mapPanel.appendChild(badgeChangeOverlay);
    }
    // =========================================================
    // 2. 탭 전환 로직 (랭킹 vs 추천)
    // =========================================================
    const sortChips = document.querySelectorAll('.sort-chip');
    
    // 숨기거나 보여줘야 할 기존 요소들
    const restaurantList = document.getElementById('restaurantList');
    const mapCanvas = document.getElementById('mapCanvas');
    const mapNotice = document.getElementById('mapNotice');
    const restaurantDetailPanel = document.getElementById('restaurantDetailPanel');

    sortChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const sortType = chip.getAttribute('data-sort');
            
            if (sortType === 'rating') {
                // -----------------------------------
                // [랭킹] 탭을 눌렀을 때
                // -----------------------------------
                // 1. 랭킹 UI 보이기
                rankingListOverlay.classList.remove('hidden-view');
                rankingDashboardOverlay.classList.remove('hidden-view');
                // 탭 이동 시 뱃지 화면은 초기화(숨김)
                badgeChangeOverlay.classList.add('hidden-view');

                // 2. 기존 식당 리스트 & 지도 숨기기
                if (restaurantList) restaurantList.style.display = 'none';
                if (mapCanvas) mapCanvas.style.display = 'none';
                if (mapNotice) mapNotice.style.display = 'none';
                
                // 만약 식당 상세 패널이 열려있다면 닫아주기
                if (restaurantDetailPanel && !restaurantDetailPanel.classList.contains('hidden')) {
                    restaurantDetailPanel.classList.add('hidden');
                }
            } else {
                // -----------------------------------
                // [추천] 등 다른 탭을 눌렀을 때 (원상 복구)
                // -----------------------------------
                // 1. 랭킹 UI 숨기기
                rankingListOverlay.classList.add('hidden-view');
                rankingDashboardOverlay.classList.add('hidden-view');
                badgeChangeOverlay.classList.add('hidden-view');
                
                // 2. 기존 식당 리스트 & 지도 다시 보이기
                if (restaurantList) restaurantList.style.display = 'flex'; // 기존 style.css 속성이 flex임
                if (mapCanvas) mapCanvas.style.display = 'block';
                if (mapNotice) mapNotice.style.display = 'flex';
            }
        });
    });
    // =========================================================
    // 3. 뱃지 변경 창 열기/닫기 로직 (새로 추가)
    // =========================================================
    const btnChange = document.querySelector('.btn-change');
    const btnBackToDash = document.getElementById('btnBackToDash');

    // 1) "변경 >" 버튼 클릭 시
    if (btnChange) {
        btnChange.addEventListener('click', () => {
            rankingDashboardOverlay.classList.add('hidden-view'); // 대시보드 숨김
            badgeChangeOverlay.classList.remove('hidden-view');   // 뱃지 화면 노출
        });
    }

    // 2) "< 뒤로 가기" 버튼 클릭 시
    if (btnBackToDash) {
        btnBackToDash.addEventListener('click', () => {
            badgeChangeOverlay.classList.add('hidden-view');      // 뱃지 화면 숨김
            rankingDashboardOverlay.classList.remove('hidden-view'); // 대시보드 복구
        });
    }
});

// =========================================================
// 4. 뱃지 교체(Swap) 로직 (새로 추가)
// =========================================================
const badgeSlots = document.querySelectorAll('.badge-slot');
const badgeItems = document.querySelectorAll('.badge-item-selectable');
const dashboardBadgeCircles = document.querySelectorAll('.dash-card.badge-card .badge-circle');
const dashboardBadgeNames = document.querySelectorAll('.dash-card.badge-card .badge-item span');

// HTML 수정 없이 이름을 동기화하기 위한 더미 데이터 맵핑
const badgeNameMap = {
    '🍜': '면치기 달인', '🗺️': '강남구 정복자', '📸': '포토그래퍼',
    '🌶️': '맵찔이 탈출', '🥩': '고기 러버',     '🐟': '바다의 왕자',
    '☕': '카페 투어러', '🍔': '패스트푸더',   '🍰': '디저트 요정',
    '🥢': '아시안 미식가', '🍙': '간편식 마스터', '🍻': '회식의 신'
};

// 1) 좌측 장착중인 슬롯 클릭 시 활성화 테두리 변경
badgeSlots.forEach(slot => {
    slot.addEventListener('click', () => {
        // 기존 선택된 슬롯 해제 후 클릭한 슬롯 활성화
        badgeSlots.forEach(s => s.classList.remove('active-slot'));
        slot.classList.add('active-slot');
    });
});

// 2) 우측 보유 뱃지 클릭 시 교체 및 갱신 로직
badgeItems.forEach(item => {
    item.addEventListener('click', () => {
        // 이미 장착된 뱃지면 아무 동작 안 함
        if (item.classList.contains('equipped-mark')) return;

        // 현재 활성화된 슬롯(파란 테두리) 찾기
        const activeSlot = document.querySelector('.badge-slot.active-slot');
        if (!activeSlot) return;

        // 새롭게 선택한 뱃지 데이터 추출
        const newEmoji = item.getAttribute('data-badge');
        const newColor = item.getAttribute('data-color');
        const newBg = item.getAttribute('data-bg');
        const newName = badgeNameMap[newEmoji] || '새로운 업적';

        // 활성화된 슬롯에 원래 껴있던 옛날 뱃지 이모지 확인
        const activeCircle = activeSlot.querySelector('.badge-circle');
        const oldEmoji = activeCircle.textContent.trim();

        // --- UI 3곳(우측 목록, 좌측 슬롯, 대시보드 본화면) 일괄 업데이트 ---

        // ① 우측 리스트 체크마크 이동 (옛날 뱃지 해제 -> 새 뱃지 장착)
        badgeItems.forEach(bItem => {
            if (bItem.getAttribute('data-badge') === oldEmoji) {
                bItem.classList.remove('equipped-mark'); 
            }
        });
        item.classList.add('equipped-mark'); 

        // ② 좌측 선택된 슬롯 아이콘/색상 변경
        activeCircle.textContent = newEmoji;
        activeCircle.style.borderColor = newColor;
        activeCircle.style.background = newBg;

        // ③ 메인 대시보드 화면 동기화 (뒤로가기 했을 때 바로 적용되도록)
        // data-slot 속성값이 "1", "2", "3" 이므로 배열 인덱스(0, 1, 2)에 맞추기 위해 -1
        const slotIndex = parseInt(activeSlot.getAttribute('data-slot')) - 1;
        
        if (dashboardBadgeCircles[slotIndex] && dashboardBadgeNames[slotIndex]) {
            dashboardBadgeCircles[slotIndex].textContent = newEmoji;
            dashboardBadgeCircles[slotIndex].style.borderColor = newColor;
            dashboardBadgeNames[slotIndex].textContent = newName;
        }
    });
});
