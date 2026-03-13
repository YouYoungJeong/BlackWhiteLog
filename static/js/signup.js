function execDaumPostcode() {
    new kakao.Postcode({
        oncomplete: function (data) {
            let roadAddr = data.roadAddress;
            let extraRoadAddr = "";

            if (data.bname !== "" && /[동|로|가]$/g.test(data.bname)) {
                extraRoadAddr += data.bname;
            }

            if (data.buildingName !== "" && data.apartment === "Y") {
                extraRoadAddr += (extraRoadAddr !== "" ? ", " + data.buildingName : data.buildingName);
            }

            if (extraRoadAddr !== "") {
                extraRoadAddr = " (" + extraRoadAddr + ")";
            }

            document.getElementById("postcode").value = data.zonecode;
            document.getElementById("roadAddress").value = roadAddr || "";
            document.getElementById("jibunAddress").value = data.jibunAddress || "";
            document.getElementById("extraAddress").value = extraRoadAddr;
            document.getElementById("detailAddress").focus();
        }
    }).open();
}

const emailInput = document.getElementById("email");

const emailMessage = document.getElementById("emailMessage");

const emailChecked = document.getElementById("email_checked");

const checkedEmailValue = document.getElementById("checked_email_value");

function resetEmailCheck() {
    emailChecked.value = "false";
    checkedEmailValue.value = "";
    emailMessage.textContent = "";
    emailMessage.className = "check-message";
}

emailInput.addEventListener("input", resetEmailCheck);


document.getElementById("checkEmailBtn").addEventListener("click", async function () {
    const value = emailInput.value.trim();

    if (!value) {
        alert("이메일을 입력해주세요.");
        emailInput.focus();
        return;
    }

    try {
        const response = await fetch(`/api/check-duplicate?type=email&value=${encodeURIComponent(value)}`);
        const data = await response.json();

        emailMessage.textContent = data.message;
        emailMessage.className = data.available ? "check-message success" : "check-message error";

        if (data.available) {
            emailChecked.value = "true";
            checkedEmailValue.value = value;
        } else {
            emailChecked.value = "false";
            checkedEmailValue.value = "";
            emailInput.focus();
        }
    } catch (error) {
        alert("이메일 중복 확인 중 오류가 발생했습니다.");
    }
});

document.getElementById("signupForm").addEventListener("submit", function (e) {

    const currentEmail = emailInput.value.trim();

    if (emailChecked.value !== "true" || checkedEmailValue.value !== currentEmail) {
        e.preventDefault();
        alert("이메일 중복 확인을 해주세요.");
        emailInput.focus();
        return;
    }
});