/************************************************************
 * 전역 상태(State)
 * ----------------------------------------------------------
 * 화면에서 공통으로 사용하는 값들을 한 곳에 모아둔다.
 * 나중에 기능이 늘어나면 여기 상태를 추가하면 된다.
 ************************************************************/
const state = {
    sortBy: "visits",                  // 현재 정렬 기준
    items: [],                        // 현재 화면에 보여주는 음식점 목록
    allItems: [],                     // 전체 음식점 목록 (검색과 무관한 원본 데이터)
    pickedCategory: null,             // 룰렛으로 뽑힌 카테고리
    rouletteAnimating: false,         // 룰렛이 돌고 있는지 여부
    lastRecommendedRestaurantId: null // 직전에 추천된 음식점 id
};

/************************************************************
 * DOM 요소 모음
 * ----------------------------------------------------------
 * document.getElementById(...) 를 여기서 한 번만 수행해두면
 * 아래 코드에서 재사용하기 편하다.
 ************************************************************/
const regionSelect = document.getElementById("regionSelect");
const categorySelect = document.getElementById("categorySelect");
const keywordInput = document.getElementById("keywordInput");
const searchBtn = document.getElementById("searchBtn");

const restaurantList = document.getElementById("restaurantList");
const mapMarkers = document.getElementById("mapMarkers");
const sortChips = document.querySelectorAll(".sort-chip");

const rouletteBtn = document.getElementById("rouletteBtn");
const rouletteRetryBtn = document.getElementById("rouletteRetryBtn");
const rouletteConfirmBtn = document.getElementById("rouletteConfirmBtn");
const rouletteCloseBtn = document.getElementById("rouletteCloseBtn");
const rouletteResult = document.getElementById("rouletteResult");
const rouletteQuestion = document.getElementById("rouletteQuestion");
const rouletteDesc = document.getElementById("rouletteDesc");
const rouletteSlotTrack = document.getElementById("rouletteSlotTrack");

const mapNotice = document.getElementById("mapNotice");
const mapNoticeToggle = document.getElementById("mapNoticeToggle");

const menuBtn = document.getElementById("menuBtn");
const sideDrawer = document.getElementById("sideDrawer");
const sideDrawerBackdrop = document.getElementById("sideDrawerBackdrop");
const sideDrawerCloseBtn = document.getElementById("sideDrawerCloseBtn");

/************************************************************
 * 상수(Constant)
 * ----------------------------------------------------------
 * 코드 안에 숫자를 직접 여러 번 쓰면 나중에 수정하기 어렵다.
 * 의미 있는 숫자는 상수로 빼두는 것이 좋다.
 ************************************************************/
const ROULETTE_ITEM_HEIGHT = 42;
const ROULETTE_MIN_ROUNDS = 5;
const SIDE_DRAWER_CLOSE_DELAY = 280;
const CARD_HIGHLIGHT_DURATION = 1500;
const DEFAULT_IMAGE_URL = "https://placehold.co/300x300?text=No+Image";

/************************************************************
 * 유틸 함수(작은 도구 함수들)
 ************************************************************/

/**
 * HTML 특수문자를 이스케이프 처리한다.
 * 문자열을 그대로 innerHTML에 넣으면 XSS 같은 문제가 생길 수 있어서
 * 안전하게 바꿔주는 함수다.
 */
function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

/**
 * 숫자처럼 보이는 값을 안전하게 Number로 바꾼다.
 */
function toNumber(value, fallback = 0) {
    const numberValue = Number(value);
    return Number.isNaN(numberValue) ? fallback : numberValue;
}

/**
 * 평점을 항상 소수점 1자리 문자열로 맞춘다.
 */
function formatRating(value) {
    return toNumber(value).toFixed(1);
}

/**
 * 음식점 id로 현재 데이터 또는 전체 데이터에서 음식점을 찾는다.
 */
function findRestaurantById(restaurantId) {
    return (
        state.items.find((item) => Number(item.restaurant_id) === Number(restaurantId)) ||
        state.allItems.find((item) => Number(item.restaurant_id) === Number(restaurantId))
    );
}

/**
 * 로딩 박스를 보여준다.
 */
function showLoading() {
    restaurantList.innerHTML = `<div class="loading-box">음식점 데이터를 불러오는 중...</div>`;
    mapMarkers.innerHTML = "";
}

/**
 * 에러 박스를 보여준다.
 */
function showError() {
    restaurantList.innerHTML = `
        <div class="empty-box">
            데이터를 불러오지 못했습니다.<br />
            DB 연결 및 테이블/컬럼명을 확인해 주세요.
        </div>
    `;
    mapMarkers.innerHTML = "";
}

/**
 * 빈 결과 메시지를 보여준다.
 */
function showEmptyList() {
    restaurantList.innerHTML = `
        <div class="empty-box">
            조건에 맞는 음식점이 없습니다.
        </div>
    `;
}

/************************************************************
 * 쿼리 문자열 생성
 ************************************************************/

/**
 * 현재 검색 조건을 이용해 API 쿼리 문자열을 만든다.
 */
function buildFilteredQuery() {
    const params = new URLSearchParams({
        region: regionSelect?.value ?? "",
        category_id: categorySelect?.value ?? "",
        keyword: keywordInput?.value.trim() ?? "",
        sort_by: state.sortBy
    });

    return params.toString();
}

/**
 * 전체 음식점 목록을 가져올 때 사용할 쿼리 문자열을 만든다.
 * 검색 조건 없이 전체 데이터를 가져온다.
 */
function buildAllItemsQuery() {
    const params = new URLSearchParams({
        region: "",
        category_id: "",
        keyword: "",
        sort_by: state.sortBy
    });

    return params.toString();
}

/************************************************************
 * 데이터 가져오기
 ************************************************************/

/**
 * 서버에서 데이터를 가져온다.
 * filtered: 현재 검색 조건에 맞는 목록
 * all: 검색과 무관한 전체 목록
 *
 * 두 목록을 동시에 가져오는 이유:
 * - 화면 리스트는 검색 결과를 보여주기 위해
 * - 룰렛은 전체 카테고리와 전체 음식점 기준으로 추천하기 위해
 */
async function fetchRestaurants() {
    showLoading();

    const filteredUrl = `${window.__INITIAL_STATE__.apiUrl}?${buildFilteredQuery()}`;
    const allUrl = `${window.__INITIAL_STATE__.apiUrl}?${buildAllItemsQuery()}`;

    try {
        const [filteredResponse, allResponse] = await Promise.all([
            fetch(filteredUrl),
            fetch(allUrl)
        ]);

        if (!filteredResponse.ok || !allResponse.ok) {
            throw new Error("API 요청 실패");
        }

        const [filteredData, allData] = await Promise.all([
            filteredResponse.json(),
            allResponse.json()
        ]);

        state.items = Array.isArray(filteredData) ? filteredData : [];
        state.allItems = Array.isArray(allData) ? allData : [];

        renderRestaurantList(state.items);
        renderMapMarkers(state.items);
    } catch (error) {
        console.error(error);
        showError();
    }
}

/************************************************************
 * 추천 모드 전환
 ************************************************************/

/**
 * 어떤 탭에 있든 "추천" 탭으로 강제로 전환한다.
 * 룰렛은 항상 추천 기준 전체 목록을 보이게 하기 위해 사용한다.
 */
function switchToRecommendMode() {
    state.sortBy = "visits";

    sortChips.forEach((chip) => {
        chip.classList.toggle("active", chip.dataset.sort === "visits");
    });

    state.items = [...state.allItems];
    renderRestaurantList(state.items);
    renderMapMarkers(state.items);
}

/************************************************************
 * 음식점 카드 렌더링
 ************************************************************/

/**
 * 음식점 카드 한 개의 HTML 문자열을 만든다.
 */
function createRestaurantCardHtml(item, index) {
    const title = escapeHtml(item.name || "이름 없음");
    const category = escapeHtml(item.category_name || "카테고리 미지정");
    const region = escapeHtml(item.region_sigungu || item.region_sido || "");
    const description = escapeHtml(item.description || "");
    const address = escapeHtml(item.road_address || item.address || "주소 정보 없음");
    const imageUrl = escapeHtml(item.image_url || DEFAULT_IMAGE_URL);

    const avgRating = formatRating(item.avg_rating);
    const visitCount = toNumber(item.visit_count);
    const reviewCount = toNumber(item.review_count);

    return `
        <article class="restaurant-card" data-id="${item.restaurant_id}">
            <div class="rank-badge">${index + 1}</div>

            <img
                class="card-thumb"
                src="${imageUrl}"
                alt="${title}"
                onerror="this.onerror=null; this.src='${DEFAULT_IMAGE_URL}';"
            />

            <div class="card-body">
                <div class="card-title-row">
                    <h3 class="card-title">${title}</h3>
                    <div class="card-score">★ ${avgRating}</div>
                </div>

                <div class="card-meta">
                    ${category}${region ? ` | ${region}` : ""}
                    ${description ? `<br>${description}` : ""}
                </div>

                <div class="card-address">${address}</div>

                <div class="card-stats">
                    <span class="stat-pill">방문 ${visitCount}</span>
                    <span class="stat-pill">리뷰 ${reviewCount}</span>
                    <span class="stat-pill">평점 ${avgRating}</span>
                </div>
            </div>
        </article>
    `;
}

/**
 * 음식점 목록 전체를 렌더링한다.
 */
function renderRestaurantList(items) {
    if (!items.length) {
        showEmptyList();
        return;
    }

    restaurantList.innerHTML = items
        .map((item, index) => createRestaurantCardHtml(item, index))
        .join("");

    bindRestaurantCardEvents();
}

/**
 * 카드 클릭 이벤트를 연결한다.
 * 카드 클릭 시 해당 음식점 마커를 강조한다.
 */
function bindRestaurantCardEvents() {
    document.querySelectorAll(".restaurant-card").forEach((card) => {
        card.addEventListener("click", () => {
            const restaurantId = Number(card.dataset.id);
            const item = findRestaurantById(restaurantId);

            if (item) {
                highlightMarker(item.restaurant_id);
            }
        });
    });
}

/************************************************************
 * 룰렛 결과 표시
 ************************************************************/

/**
 * 최종 추천된 음식점 정보를 룰렛 박스에 표시한다.
 */
function renderRecommendedResult(item) {
    const category = item.category_name || "카테고리 미지정";
    const region = item.region_sigungu || item.region_sido || "지역 정보 없음";
    const rating = formatRating(item.avg_rating);
    const visits = toNumber(item.visit_count);

    rouletteSlotTrack.innerHTML = `
        <div class="roulette-slot__item">${escapeHtml(item.name || "이름 없음")}</div>
    `;
    rouletteSlotTrack.style.transition = "none";
    rouletteSlotTrack.style.transform = "translateY(0)";

    rouletteQuestion.textContent = `${category} · ${region} · ★ ${rating} · 방문 ${visits}`;
    rouletteDesc.textContent = "이 음식점을 오늘의 추천으로 골라봤어요.";
}

/************************************************************
 * 카드 포커스 / 하이라이트
 ************************************************************/

/**
 * 특정 음식점 카드를 화면 중앙으로 스크롤하고 잠깐 강조한다.
 */
function focusRestaurantCard(restaurantId) {
    const targetCard = document.querySelector(`.restaurant-card[data-id="${restaurantId}"]`);
    if (!targetCard) return;

    targetCard.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });

    targetCard.style.boxShadow =
        "0 0 0 3px rgba(143, 170, 122, 0.25), 0 10px 30px rgba(0, 0, 0, 0.06)";

    setTimeout(() => {
        targetCard.style.boxShadow = "";
    }, CARD_HIGHLIGHT_DURATION);
}

/**
 * 전체 음식점 목록을 보여주고, 특정 음식점에 포커스를 준다.
 */
function showAllRestaurantsAndFocus(item) {
    switchToRecommendMode();
    highlightMarker(item.restaurant_id);

    requestAnimationFrame(() => {
        focusRestaurantCard(item.restaurant_id);
    });
}

/************************************************************
 * 룰렛 관련 함수
 ************************************************************/

/**
 * 현재 룰렛 버튼/확인/다시뽑기 버튼 상태를 한 번에 바꾼다.
 */
function setRouletteButtonsDisabled(disabled) {
    if (rouletteConfirmBtn) rouletteConfirmBtn.disabled = disabled;
    if (rouletteRetryBtn) rouletteRetryBtn.disabled = disabled;
    if (rouletteBtn) rouletteBtn.disabled = disabled;
}

/**
 * 룰렛 박스를 초기 상태로 되돌린다.
 */
function resetRouletteBox() {
    rouletteSlotTrack.innerHTML = `<div class="roulette-slot__item">한식</div>`;
    rouletteSlotTrack.style.transition = "none";
    rouletteSlotTrack.style.transform = "translateY(0)";

    rouletteQuestion.textContent = "이 카테고리 음식점을 추천해드릴까요?";
    rouletteDesc.textContent = "주사위를 다시 눌러도 다른 카테고리를 추천받을 수 있어요.";
}

/**
 * 전체 음식점 목록에서 중복 없는 카테고리 배열을 만든다.
 */
function getAllCategories() {
    return [...new Set(
        state.allItems
            .map((item) => item.category_name)
            .filter(Boolean)
    )];
}

/**
 * 룰렛 애니메이션에 사용할 카테고리 시퀀스를 만든다.
 * 예:
 * [한식, 일식, 중식, ...] 를 여러 번 반복하고,
 * 마지막에는 실제 당첨 카테고리에서 멈추도록 구성한다.
 */
function buildRouletteSpinSequence(categories, finalIndex) {
    const spinSequence = [];

    for (let round = 0; round < ROULETTE_MIN_ROUNDS; round += 1) {
        spinSequence.push(...categories);
    }

    for (let i = 0; i <= finalIndex; i += 1) {
        spinSequence.push(categories[i]);
    }

    return spinSequence;
}

/**
 * 룰렛 박스를 닫는다.
 */
function closeRouletteBox() {
    rouletteResult.hidden = true;
    state.pickedCategory = null;
    state.rouletteAnimating = false;

    resetRouletteBox();
    setRouletteButtonsDisabled(false);
}

/**
 * 룰렛으로 뽑힌 카테고리에서 음식점을 랜덤 추천한다.
 *
 * 규칙:
 * - 같은 카테고리 식당이 여러 개 있으면 직전 추천 식당은 제외
 * - 같은 카테고리 식당이 1개뿐이면 그대로 추천
 */
function recommendRestaurantFromPickedCategory() {
    if (state.rouletteAnimating) return;

    if (!state.pickedCategory) {
        alert("먼저 카테고리를 뽑아주세요.");
        return;
    }

    const sameCategoryItems = state.allItems.filter(
        (item) => item.category_name === state.pickedCategory
    );

    if (!sameCategoryItems.length) {
        alert("해당 카테고리의 음식점이 없습니다.");
        return;
    }

    let candidateItems = sameCategoryItems;

    if (sameCategoryItems.length > 1 && state.lastRecommendedRestaurantId !== null) {
        const filteredItems = sameCategoryItems.filter(
            (item) => Number(item.restaurant_id) !== Number(state.lastRecommendedRestaurantId)
        );

        if (filteredItems.length) {
            candidateItems = filteredItems;
        }
    }

    const randomIndex = Math.floor(Math.random() * candidateItems.length);
    const pickedRestaurant = candidateItems[randomIndex];

    state.lastRecommendedRestaurantId = pickedRestaurant.restaurant_id;

    renderRecommendedResult(pickedRestaurant);
    showAllRestaurantsAndFocus(pickedRestaurant);
}

/**
 * 룰렛을 돌려서 카테고리를 하나 뽑는다.
 */
function pickRandomCategory() {
    if (!state.allItems.length) {
        alert("추천할 음식점 데이터가 없습니다.");
        return;
    }

    if (state.rouletteAnimating) return;

    // 룰렛 시작 시 무조건 추천 모드로 전환
    switchToRecommendMode();

    const categories = getAllCategories();

    if (!categories.length) {
        alert("카테고리 정보가 없습니다.");
        return;
    }

    state.rouletteAnimating = true;
    state.pickedCategory = null;
    rouletteResult.hidden = false;

    rouletteQuestion.textContent = "카테고리를 고르는 중..";
    rouletteDesc.textContent = "뭐 먹을지 찾는 중..";
    setRouletteButtonsDisabled(true);

    const finalIndex = Math.floor(Math.random() * categories.length);
    const finalCategory = categories[finalIndex];
    const spinSequence = buildRouletteSpinSequence(categories, finalIndex);

    rouletteSlotTrack.innerHTML = spinSequence
        .map((category) => `<div class="roulette-slot__item">${escapeHtml(category)}</div>`)
        .join("");

    // 애니메이션 시작 전 초기 위치 세팅
    rouletteSlotTrack.style.transition = "none";
    rouletteSlotTrack.style.transform = "translateY(0)";

    // 강제 리플로우: 브라우저가 현재 상태를 먼저 반영하도록 함
    void rouletteSlotTrack.offsetHeight;

    let step = 0;
    const lastStep = spinSequence.length - 1;

    function moveNext() {
        step += 1;
        rouletteSlotTrack.style.transform = `translateY(-${step * ROULETTE_ITEM_HEIGHT}px)`;

        if (step < lastStep) {
            const progress = step / lastStep;
            const delay = 40 + Math.pow(progress, 2.2) * 100;

            setTimeout(() => {
                rouletteSlotTrack.style.transition = "transform 0.09s linear";
                moveNext();
            }, delay);
        } else {
            state.pickedCategory = finalCategory;
            state.rouletteAnimating = false;

            rouletteQuestion.textContent = "이 카테고리 음식점을 추천해드릴까요?";
            rouletteDesc.textContent = "확인을 누르면 해당 카테고리의 음식점 중 한 곳을 추천해드려요.";
            setRouletteButtonsDisabled(false);
        }
    }

    requestAnimationFrame(() => {
        rouletteSlotTrack.style.transition = "transform 0.09s linear";
        setTimeout(moveNext, 80);
    });
}

/************************************************************
 * 지도 마커 렌더링
 ************************************************************/

/**
 * 지도가 아직 실제 API와 연결되지 않았기 때문에
 * 임시 위치 배열을 사용해 마커를 배치한다.
 */
function getFallbackMarkerPositions() {
    return [
        { x: 28, y: 22 },
        { x: 43, y: 27 },
        { x: 35, y: 39 },
        { x: 26, y: 35 },
        { x: 40, y: 49 },
        { x: 32, y: 57 },
        { x: 53, y: 32 },
        { x: 58, y: 67 },
        { x: 70, y: 48 },
        { x: 63, y: 22 }
    ];
}

/**
 * 지도에 마커를 그린다.
 * 현재는 상위 10개만 표시한다.
 */
function renderMapMarkers(items) {
    if (!items.length) {
        mapMarkers.innerHTML = "";
        return;
    }

    const fallbackPositions = getFallbackMarkerPositions();

    mapMarkers.innerHTML = items
        .slice(0, 10)
        .map((item, index) => {
            const pos = fallbackPositions[index % fallbackPositions.length];

            return `
                <div
                    class="map-marker"
                    data-id="${item.restaurant_id}"
                    style="left:${pos.x}%; top:${pos.y}%;"
                    title="${escapeHtml(item.name || "이름 없음")}"
                >
                    <span>${index + 1}</span>
                </div>
            `;
        })
        .join("");

    bindMapMarkerEvents();
}

/**
 * 마커 클릭 이벤트를 연결한다.
 */
function bindMapMarkerEvents() {
    document.querySelectorAll(".map-marker").forEach((marker) => {
        marker.addEventListener("click", () => {
            const restaurantId = Number(marker.dataset.id);
            const item = findRestaurantById(restaurantId);

            if (item) {
                alert(
                    `${item.name}\n방문 ${toNumber(item.visit_count)} · 리뷰 ${toNumber(item.review_count)} · 평점 ${formatRating(item.avg_rating)}`
                );
            }
        });
    });
}

/**
 * 특정 음식점 마커를 강조한다.
 */
function highlightMarker(restaurantId) {
    document.querySelectorAll(".map-marker").forEach((marker) => {
        marker.style.filter = "";
        marker.style.transform = "rotate(-45deg)";
    });

    const targetMarker = document.querySelector(`.map-marker[data-id="${restaurantId}"]`);

    if (targetMarker) {
        targetMarker.style.filter = "brightness(0.9) saturate(1.2)";
        targetMarker.style.transform = "rotate(-45deg) scale(1.12)";
    }
}

/************************************************************
 * 우측 드로어(햄버거 메뉴)
 ************************************************************/

/**
 * 우측 드로어를 연다.
 */
function openSideDrawer() {
    if (!sideDrawer || !sideDrawerBackdrop) return;

    sideDrawer.hidden = false;
    sideDrawerBackdrop.hidden = false;

    requestAnimationFrame(() => {
        sideDrawer.classList.add("is-open");
        sideDrawerBackdrop.classList.add("is-open");
        sideDrawer.setAttribute("aria-hidden", "false");
        document.body.classList.add("drawer-open");
    });
}

/**
 * 우측 드로어를 닫는다.
 */
function closeSideDrawer() {
    if (!sideDrawer || !sideDrawerBackdrop) return;

    sideDrawer.classList.remove("is-open");
    sideDrawerBackdrop.classList.remove("is-open");
    sideDrawer.setAttribute("aria-hidden", "true");
    document.body.classList.remove("drawer-open");

    setTimeout(() => {
        sideDrawer.hidden = true;
        sideDrawerBackdrop.hidden = true;
    }, SIDE_DRAWER_CLOSE_DELAY);
}

/************************************************************
 * 이벤트 연결
 ************************************************************/

/**
 * 정렬 칩 이벤트 연결
 */
function bindSortChipEvents() {
    sortChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            sortChips.forEach((targetChip) => targetChip.classList.remove("active"));
            chip.classList.add("active");

            state.sortBy = chip.dataset.sort;
            fetchRestaurants();
        });
    });
}

/**
 * 검색 관련 이벤트 연결
 */
function bindSearchEvents() {
    if (searchBtn) {
        searchBtn.addEventListener("click", fetchRestaurants);
    }

    if (keywordInput) {
        keywordInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                fetchRestaurants();
            }
        });
    }

    if (regionSelect) {
        regionSelect.addEventListener("change", fetchRestaurants);
    }

    if (categorySelect) {
        categorySelect.addEventListener("change", fetchRestaurants);
    }
}

/**
 * 룰렛 관련 이벤트 연결
 */
function bindRouletteEvents() {
    if (rouletteBtn) {
        rouletteBtn.addEventListener("click", pickRandomCategory);
    }

    if (rouletteRetryBtn) {
        rouletteRetryBtn.addEventListener("click", pickRandomCategory);
    }

    if (rouletteConfirmBtn) {
        rouletteConfirmBtn.addEventListener("click", recommendRestaurantFromPickedCategory);
    }

    if (rouletteCloseBtn) {
        rouletteCloseBtn.addEventListener("click", closeRouletteBox);
    }
}

/**
 * 공지사항 토글 이벤트 연결
 */
function bindMapNoticeEvents() {
    if (!mapNotice || !mapNoticeToggle) return;

    mapNoticeToggle.addEventListener("click", () => {
        const isCollapsed = mapNotice.classList.toggle("collapsed");

        if (isCollapsed) {
            mapNoticeToggle.setAttribute("aria-label", "공지사항 펼치기");
            mapNoticeToggle.setAttribute("aria-expanded", "false");
        } else {
            mapNoticeToggle.setAttribute("aria-label", "공지사항 접기");
            mapNoticeToggle.setAttribute("aria-expanded", "true");
        }
    });
}

/**
 * 사이드 드로어 이벤트 연결
 */
function bindSideDrawerEvents() {
    if (menuBtn) {
        menuBtn.addEventListener("click", openSideDrawer);
    }

    if (sideDrawerCloseBtn) {
        sideDrawerCloseBtn.addEventListener("click", closeSideDrawer);
    }

    if (sideDrawerBackdrop) {
        sideDrawerBackdrop.addEventListener("click", closeSideDrawer);
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSideDrawer();
        }
    });
}

/************************************************************
 * 초기 실행
 ************************************************************/

/**
 * 페이지가 처음 열릴 때 실행되는 함수
 * - 이벤트 연결
 * - 첫 데이터 로드
 */
function init() {
    bindSortChipEvents();
    bindSearchEvents();
    bindRouletteEvents();
    bindMapNoticeEvents();
    bindSideDrawerEvents();
    fetchRestaurants();
}

init();

const profileToggle = document.getElementById("profileToggle");
const profileDropdown = document.getElementById("profileDropdown");

if (profileToggle && profileDropdown) {
    profileToggle.addEventListener("click", function (e) {
        e.stopPropagation();
        profileDropdown.classList.toggle("show");
    });

    document.addEventListener("click", function (e) {
        if (!profileToggle.contains(e.target) && !profileDropdown.contains(e.target)) {
            profileDropdown.classList.remove("show");
        }
    });
}