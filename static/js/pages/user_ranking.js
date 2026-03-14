document.addEventListener("DOMContentLoaded", () => {
    // =========================================================
    // DOM 분리 및 이동 (구조 보존)
    // =========================================================
    const sidebar = document.querySelector('.sidebar');
    const mapPanel = document.querySelector('.map-panel');
    
    const rankingListOverlay = document.getElementById('rankingListOverlay');
    const rankingDashboardOverlay = document.getElementById('rankingDashboardOverlay');
    const badgeChangeOverlay = document.getElementById('badgeChangeOverlay');
    
    if (sidebar && rankingListOverlay) sidebar.appendChild(rankingListOverlay);
    if (mapPanel && rankingDashboardOverlay) mapPanel.appendChild(rankingDashboardOverlay);
    if (mapPanel && badgeChangeOverlay) mapPanel.appendChild(badgeChangeOverlay);

    // =========================================================
    // 탭 전환 로직 (랭킹 vs 추천)
    // =========================================================
    const sortChips = document.querySelectorAll('.sort-chip');
    const restaurantList = document.getElementById('restaurantList');
    const mapCanvas = document.getElementById('mapCanvas');
    const mapNotice = document.getElementById('mapNotice');
    const restaurantDetailPanel = document.getElementById('restaurantDetailPanel');

    sortChips.forEach(chip => {
        chip.addEventListener('click', async () => {
            const sortType = chip.getAttribute('data-sort');
            
            if (sortType === 'rating') {
                rankingListOverlay.classList.remove('hidden-view');
                rankingDashboardOverlay.classList.remove('hidden-view');
                badgeChangeOverlay.classList.add('hidden-view');

                if (restaurantList) restaurantList.style.display = 'none';
                if (mapCanvas) mapCanvas.style.display = 'none';
                if (mapNotice) mapNotice.style.display = 'none';
                if (restaurantDetailPanel && !restaurantDetailPanel.classList.contains('hidden')) {
                    restaurantDetailPanel.classList.add('hidden');
                }

                // 랭킹 탭을 누르면 DB 데이터를 가져와 렌더링합니다.
                await loadRankingData();

            } else {
                rankingListOverlay.classList.add('hidden-view');
                rankingDashboardOverlay.classList.add('hidden-view');
                badgeChangeOverlay.classList.add('hidden-view');
                
                if (restaurantList) restaurantList.style.display = 'flex';
                if (mapCanvas) mapCanvas.style.display = 'block';
                if (mapNotice) mapNotice.style.display = 'flex';
            }
        });
    });

    // =========================================================
    // 뱃지 변경 창 열기/닫기 로직 (이벤트 위임 방식으로 안전하게 처리)
    // =========================================================
    document.body.addEventListener('click', (e) => {
        if (e.target.closest('.btn-change')) {
            rankingDashboardOverlay.classList.add('hidden-view');
            badgeChangeOverlay.classList.remove('hidden-view');
        } else if (e.target.closest('#btnBackToDash')) {
            badgeChangeOverlay.classList.add('hidden-view');
            rankingDashboardOverlay.classList.remove('hidden-view');
        }
    });
});

// =========================================================
// 데이터 Fetch 및 화면 렌더링 로직
// =========================================================
async function loadRankingData() {
    try {
        const [listRes, meRes] = await Promise.all([
            fetch('/api/ranking/list'),
            fetch('/api/ranking/me')
        ]);

        const users = await listRes.json();
        const me = await meRes.json();

        // 좌측 패널: 실시간 랭킹 리스트
        const listContainer = document.querySelector(".ranking-list-body");
        if (listContainer && users.length > 0) {
            listContainer.innerHTML = users.map((u, i) => {
                let rankClass = "bronze";
                if (i === 0) rankClass = "gold";
                else if (i === 1) rankClass = "silver";
                else if (i > 2) rankClass = "";

                const isMe = u.user_id === me.user_id;
                const highlightClass = isMe ? "my-rank-highlight" : (i < 3 ? "top-rank" : "");
                const meBadge = isMe ? `<span class="me-badge">ME</span>` : "";

                return `
                    <div class="rank-item ${highlightClass}">
                        <span class="rank-num ${rankClass}">${i + 1}</span>
                        <div class="rank-info">
                            <strong>${u.nickname} ${meBadge}</strong>
                            <span class="rank-tier">💍 ${u.tier}</span>
                        </div>
                        <div class="rank-pts">${(u.point || 0).toLocaleString()} <span>pts</span></div>
                    </div>
                `;
            }).join('');
        }
        const allBadges = me.achievements_data.all_achievements;
        const myBadges = me.achievements_data.user_achievements;
        const myBadgeIds = myBadges.map(b => b.achievement_id);

        // (DB연동 없이) 보유한 뱃지 중 앞에서부터 최대 3개를 장착한 것으로 간주
        const displayBadges = myBadges.slice(0, 3);

        // 우측 패널: 나의 랭킹 대시보드 내 정보
        const profileName = document.querySelector('.profile-card h3');
        const tierBadge = document.querySelector('.tier-badge');
        const tierDesc = document.querySelector('.tier-desc'); // 칭호 요소
        const gaugePts = document.querySelector('.gauge-pts strong');
        const gaugeFill = document.querySelector('.gauge-bar-fill');
        const gaugeLabels = document.querySelectorAll('.gauge-labels span'); // 게이지 양끝 티어
        const gaugeDesc = document.querySelector('.gauge-desc'); // 승급까지 남은 점수 설명

        // 이름
        if (profileName) profileName.innerText = me.nickname;
        // 업적 이름으로 하기
        if (tierDesc) {
            tierDesc.innerText = myBadges.length > 0 ? myBadges[0].name : "초보 미식가";
        }
        // 다음 티어 계산
        const tierList = ['BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND'];
        const tierNames = {'BRONZE':'브론즈', 'SILVER':'실버', 'GOLD':'골드', 'PLATINUM':'플래티넘', 'DIAMOND':'다이아몬드'};
        // DB에서 가져온 영문 티어를 인덱스로 변환
        let currentTierStr = me.tier || 'BRONZE';
        let currentTierIdx = tierList.indexOf(currentTierStr.toUpperCase());
        if(currentTierIdx === -1) currentTierIdx = 0;
        const currentTierName = tierNames[tierList[currentTierIdx]];
        const nextTierIdx = Math.min(currentTierIdx + 1, tierList.length - 1);
        const nextTierName = tierNames[tierList[nextTierIdx]];

        // 프로필 밑 티어
        if (tierBadge) tierBadge.innerText = `${currentTierName} 티어`;

        // 게이지 바 양끝 티어 이름 동적 변경 (좌: 내 티어, 우: 다음 티어)
        if (gaugeLabels.length >= 2) {
            gaugeLabels[0].innerText = currentTierName;
            gaugeLabels[1].innerText = currentTierIdx === nextTierIdx ? 'MAX' : nextTierName;
        }
        
        // 게이지 바 아래 설명 (다음 티어 이름은 반영, 점수는 1580점 하드코딩 유지)
        if (gaugeDesc) {
            if (currentTierIdx === nextTierIdx) {
                gaugeDesc.innerHTML = `최고 등급에 도달했습니다!`;
            } else {
                gaugeDesc.innerHTML = `${nextTierName} 승급까지 <strong>1,580점</strong> 남았습니다!`;
            }
        }

        // 포인트 점수 및 게이지 % 바 채우기
        if (gaugePts) gaugePts.innerText = (me.point || 0).toLocaleString();
        const percent = Math.min(((me.point || 0) / 10000) * 100, 100);
        if (gaugeFill) gaugeFill.style.width = percent + "%";

        // 대시보드 메인 화면: 내가 보유한 대표 뱃지 렌더링 (최대 3개)
        const dashboardBadgeList = document.querySelector('.badge-list');
        if (dashboardBadgeList) {
            const displayBadges = myBadges.slice(0, 3);
            if (displayBadges.length === 0) {
                dashboardBadgeList.innerHTML = `<p style="color:var(--subtext); font-size:13px; text-align:center; width:100%;">아직 획득한 뱃지가 없습니다.</p>`;
            } else {
                dashboardBadgeList.innerHTML = displayBadges.map(badge => `
                    <div class="badge-item dash-badge-item">
                        <div class="badge-circle" style="border: 2px solid #ddd; overflow:hidden;">
                            <img src="${badge.icon_url}" alt="${badge.name}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='/static/img/main_logo.png'">
                        </div>
                        <span>${badge.name}</span>
                    </div>
                `).join('');
            }
        }

        // 뱃지 변경 창: 모든 뱃지 리스트 렌더링
        const allBadgesGrid = document.querySelector('.all-badges-grid');
        if (allBadgesGrid) {
            allBadgesGrid.innerHTML = allBadges.map(badge => {
                const hasBadge = myBadgeIds.includes(badge.achievement_id);
                const opacityStyle = hasBadge ? "1" : "0.3"; 
                // 장착된 뱃지인지 확인 (최대 3개 안에 포함되는지)
                const equippedClass = (hasBadge && myBadges.slice(0,3).some(b => b.achievement_id === badge.achievement_id)) ? "equipped-mark" : "";

                return `
                    <div class="badge-item-selectable ${equippedClass}" 
                         data-id="${badge.achievement_id}" 
                         data-name="${badge.name}" 
                         data-url="${badge.icon_url}"
                         style="opacity: ${opacityStyle};">
                        <div class="badge-circle" style="border: 2px solid #ddd; overflow:hidden; background: #fff;">
                            <img src="${badge.icon_url}" alt="${badge.name}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='/static/img/main_logo.png'">
                        </div>
                    </div>
                `;
            }).join('');
        }

        // 뱃지 변경 창: 좌측 선택 슬롯 (최대 3개 고정)
        const equippedSlotsContainer = document.querySelector('.equipped-slots');
        if (equippedSlotsContainer) {
            let slotsHtml = "";
            for(let i=0; i<3; i++) {
                let activeClass = i === 0 ? "active-slot" : ""; // 첫 번째 슬롯 기본 활성화
                let badge = myBadges[i];
                if (badge) {
                    slotsHtml += `
                        <div class="badge-slot ${activeClass}" data-slot="${i+1}">
                            <div class="badge-circle" style="border: 2px solid #ddd; overflow:hidden;">
                                <img src="${badge.icon_url}" data-id="${badge.achievement_id}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='/static/img/main_logo.png'">
                            </div>
                        </div>
                    `;
                } else {
                    slotsHtml += `
                        <div class="badge-slot ${activeClass}" data-slot="${i+1}">
                            <div class="badge-circle" style="border: 2px solid transparent; background: #f5f5f5;"></div>
                        </div>
                    `;
                }
            }
            equippedSlotsContainer.innerHTML = slotsHtml;
        }

        // 렌더링이 완료된 후, 동적으로 생성된 요소들에 대해 교체(Swap) 이벤트를 연결합니다.
        bindBadgeSwapEvents();

    } catch (e) {
        console.error("데이터 렌더링 중 오류:", e);
    }
}

// =========================================================
// 이미지 기반 뱃지 교체(Swap) 로직
// =========================================================
function bindBadgeSwapEvents() {
    const badgeSlots = document.querySelectorAll('.badge-slot');
    const badgeItems = document.querySelectorAll('.badge-item-selectable');

    // 좌측 장착중인 슬롯 클릭 시 활성화 테두리 변경
    badgeSlots.forEach(slot => {
        slot.addEventListener('click', () => {
            badgeSlots.forEach(s => s.classList.remove('active-slot'));
            slot.classList.add('active-slot');
        });
    });

    // 우측 보유 뱃지 클릭 시 교체 및 갱신 로직
    badgeItems.forEach(item => {
        item.addEventListener('click', () => {
            // 획득하지 못한 뱃지(투명도 0.3)는 클릭 방지
            if (item.style.opacity === "0.3") return alert("아직 획득하지 못한 업적입니다.");
            // 이미 장착된 뱃지면 아무 동작 안 함
            if (item.classList.contains('equipped-mark')) return;

            const activeSlot = document.querySelector('.badge-slot.active-slot');
            if (!activeSlot) return;

            // 새롭게 선택한 뱃지 데이터 추출
            const newId = item.getAttribute('data-id');
            const newUrl = item.getAttribute('data-url');
            const newName = item.getAttribute('data-name');
            const slotNum = activeSlot.getAttribute('data-slot'); // "1", "2", "3"

            // 활성화된 슬롯에 원래 껴있던 옛날 뱃지 ID 확인
            const activeCircle = activeSlot.querySelector('.badge-circle');
            const oldImg = activeCircle.querySelector('img');
            const oldId = oldImg ? oldImg.getAttribute('data-id') : null;

            //  우측 리스트 체크마크 이동
            if (oldId) {
                badgeItems.forEach(bItem => {
                    if (bItem.getAttribute('data-id') === oldId) bItem.classList.remove('equipped-mark'); 
                });
            }
            item.classList.add('equipped-mark');

            //  좌측 선택된 슬롯 아이콘 변경
            activeCircle.innerHTML = `<img src="${newUrl}" data-id="${newId}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='/static/img/main_logo.png'">`;
            activeCircle.style.border = "2px solid #ddd";
            activeCircle.style.background = "transparent";

            //  메인 대시보드 화면 동기화 (현재 장착된 3개의 슬롯을 읽어와 대시보드를 통째로 갱신)
            const dashboardBadgeList = document.querySelector('.badge-list');
            if (dashboardBadgeList) {
                let dashHtml = "";
                document.querySelectorAll('.badge-slot').forEach(slot => {
                    const img = slot.querySelector('img');
                    if(img) {
                        const id = img.getAttribute('data-id');
                        const url = img.getAttribute('src');
                        // 우측 리스트에서 이름을 찾아옵니다
                        const sourceItem = document.querySelector(`.badge-item-selectable[data-id="${id}"]`);
                        const name = sourceItem ? sourceItem.getAttribute('data-name') : '이름 없음';
                        
                        dashHtml += `
                            <div class="badge-item dash-badge-item">
                                <div class="badge-circle" style="border: 2px solid #ddd; overflow:hidden;">
                                    <img src="${url}" alt="${name}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='/static/img/main_logo.png'">
                                </div>
                                <span>${name}</span>
                            </div>
                        `;
                    }
                });
                dashboardBadgeList.innerHTML = dashHtml;
            }
            // 1번 슬롯 변경 시, DB 업데이트 없이 프로필 칭호 즉시 교체
            if (slotNum === "1") {
                const tierDesc = document.querySelector('.tier-desc');
                if (tierDesc) tierDesc.innerText = newName;
            }
        });
    });
}