/************************************************************
 * 음식점 상세 패널 및 탭 로직 ####
 ************************************************************/
const detailPanel = document.getElementById("restaurantDetailPanel");
const closeDetailBtn = document.getElementById("closeDetailBtn");
const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanes = document.querySelectorAll(".tab-pane");

// 패널 닫기 이벤트
if (closeDetailBtn) {
    closeDetailBtn.addEventListener("click", () => {
        detailPanel.classList.add("hidden");
    });
}
// 지도 영역 클릭 시 패널 닫기
const mapArea = document.querySelector(".map-panel");
if (mapArea) {
    mapArea.addEventListener("click", (event) => {
        // 상세 패널 자체를 클릭했을 때는 안 닫히도록 예외 처리
        if (event.target.closest('#restaurantDetailPanel')) return;

        // 패널이 열려있을 때만 닫기
        if (!detailPanel.classList.contains("hidden")) {
            detailPanel.classList.add("hidden");
        }
    });
}

// 탭 전환 이벤트
tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        // 모든 탭 버튼과 내용 초기화
        tabButtons.forEach(b => b.classList.remove("active"));
        tabPanes.forEach(p => p.classList.add("hidden"));

        // 클릭된 탭 활성화
        btn.classList.add("active");
        const targetTabId = "tab-" + btn.getAttribute("data-tab");
        document.getElementById(targetTabId).classList.remove("hidden");
    });
});

// 패널 열기 및 AJAX 정보 호출 함수 
async function openDetailPanel(restaurantId) {
    const detailPanel = document.getElementById("restaurantDetailPanel");
    detailPanel.classList.remove("hidden");
    
    // '정보' 탭을 강제로 클릭하여 활성화
    document.querySelector('.tab-btn[data-tab="info"]').click();

    const infoTab = document.getElementById("tab-info");
    infoTab.innerHTML = "<p>가게 정보를 불러오는 중...</p>";

    try {
        // Step 2: 서버에서 식당 상세 정보 가져오기
        const response = await fetch(`/api/restaurants/${restaurantId}`);
        if (!response.ok) throw new Error("정보를 불러오지 못했습니다.");
        const data = await response.json();

        // 1. 패널 상단 헤더 업데이트
        document.getElementById("detailRestaurantName").textContent = data.name;
        document.getElementById("detailMainImage").src = data.image_url;

        // 2. 정보 탭 내용 렌더링
        const isOpen = data.status === 'OPEN';
        infoTab.innerHTML = `
            <div style="line-height: 1.6;">
                <p><strong>📝 설명:</strong> ${data.description || '설명이 없습니다.'}</p>
                <p><strong>📞 전화:</strong> ${data.phone || '정보 없음'}</p>
                <p><strong>📍 주소:</strong> ${data.road_address || '정보 없음'}</p>
                <p><strong>⏰ 시간:</strong> ${data.business_hours || '정보 없음'}</p>
                <p><strong>운영:</strong> 
                    <span style="color: ${isOpen ? 'green' : 'red'}; font-weight: bold;">
                        ${isOpen ? '🟢 오픈중' : '🔴 영업종료'}
                    </span>
                </p>
            </div>
        `;

        // 3. [추가] 메뉴 탭 데이터 렌더링
        const menuTab = document.getElementById("tab-menu");
        menuTab.innerHTML = "<p>메뉴 정보를 불러오는 중...</p>";
        
        try {
            const menuRes = await fetch(`/api/restaurants/${restaurantId}/menus`);
            if (!menuRes.ok) throw new Error("메뉴 API 호출 실패");
            const menus = await menuRes.json();

            if (menus.length === 0) {
                menuTab.innerHTML = "<p style='color: var(--subtext);'>등록된 메뉴가 없습니다.</p>";
            } else {
                let menuHtml = '<ul style="list-style: none; padding: 0; margin: 0;">';
                menus.forEach(m => {
                    // 가격에 천 단위 콤마(,) 찍기
                    const priceFormatted = m.price.toLocaleString() + '원';
                    menuHtml += `
                        <li style="display: flex; justify-content: space-between; padding: 16px 0; border-bottom: 1px solid var(--line);">
                            <span style="font-weight: bold; color: var(--text);">${m.menu_name}</span>
                            <span style="color: var(--point-dark); font-weight: bold;">${priceFormatted}</span>
                        </li>
                    `;
                });
                menuHtml += '</ul>';
                menuTab.innerHTML = menuHtml;
            }
        } catch (menuError) {
            menuTab.innerHTML = `<p style="color:red;">메뉴를 불러오지 못했습니다.</p>`;
            console.error("Menu Fetch Error:", menuError);
        }
    } catch (error) {
        infoTab.innerHTML = `<p style="color:red;">오류 발생: ${error.message}</p>`;
        console.error("Detail Fetch Error:", error);
    }
}

document.addEventListener("click", (event) => {
    // 1. 클릭된 요소가 '.restaurant-card' 이거나 그 내부의 요소인지 확인합니다.
    const clickedCard = event.target.closest(".restaurant-card");
    
    // 2. 만약 식당 카드가 맞다면?
    if (clickedCard) {
        // html의 data-id 속성에서 식당 번호를 빼옵니다.
        const restaurantId = clickedCard.getAttribute("data-id");
        
        if (restaurantId) {
            openDetailPanel(restaurantId); // 패널 열기 함수 실행!
        }
    }
});

/************************************************************
 * 음식점 상세 패널 및 탭 로직 ####
 ************************************************************/