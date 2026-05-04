document.addEventListener("DOMContentLoaded", function(){

    const socket = io();

    let selectedUser = null;
    let selectedMessages = new Set();
    let selectionMode = false;

    const box = document.getElementById("chat-box");
    const form = document.getElementById("chat-form");
    const msgInput = document.getElementById("message");
    const search = document.getElementById("searchUser");

    function roomName(a,b){
        return [a,b].sort().join("_");
    }

    /* ---------------- OPEN CHAT ---------------- */
    window.openChat = function(username){

        selectedUser = username;

        document.getElementById("chat-header").innerText = username;
        form.style.display = "flex";

        // remove unread badge instantly
        document.querySelectorAll(".user-item").forEach(item => {
            const name = item.querySelector(".user-name").innerText;
            if (name === username) {
                let badge = item.querySelector(".badge");
                if (badge) badge.remove();
            }
        });

        socket.emit("join", {
            room: roomName(CURRENT_USER, selectedUser)
        });

        loadMessages();
    };

    /* ---------------- SEND ---------------- */
    form.addEventListener("submit", function(e){
        e.preventDefault();

        if(!selectedUser) return;

        const msg = msgInput.value.trim();
        if(!msg) return;

        socket.emit("send_message", {
            sender: CURRENT_USER,
            receiver: selectedUser,
            message: msg
        });

        msgInput.value = "";
    });

    /* ---------------- SOCKET ---------------- */
    socket.on("new_message", function(){
        if(selectedUser) loadMessages();
        refreshUnread();
    });

    /* ---------------- LOAD MESSAGES ---------------- */
    async function loadMessages(){

        if(!selectedUser) return;

        const res = await fetch("/messages/" + selectedUser);
        const data = await res.json();

        box.innerHTML = "";

        data.forEach(item => {

            const div = document.createElement("div");
            const isSender = item.sender === CURRENT_USER;

            div.className = isSender ? "msg sent" : "msg received";

            let ticks = isSender ? (item.seen ? "✔✔" : "✔") : "";

            let forwardedLabel = item.forwarded
                ? "<div class='forwarded-label'>Forwarded</div>"
                : "";

            let verifyBadge = `
                <span class="${item.verified ? 'ok' : 'bad'}">
                ${item.verified ? '✓ Verified' : '⚠ Unverified'}
                </span>
            `;

            div.dataset.id = item.id;

            div.onclick = function(){

                if(!selectionMode){
                    selectionMode = true;
                    showForwardBar();
                }

                if(selectedMessages.has(item.id)){
                    selectedMessages.delete(item.id);
                    div.classList.remove("selected");
                } else {
                    selectedMessages.add(item.id);
                    div.classList.add("selected");
                }

                updateSelectionCount();
            };

            div.innerHTML = `
                ${forwardedLabel}
                <div class="msg-text">${item.message}</div>
                <small>
                    ${item.time}
                    ${isSender ? `<span class="ticks">${ticks}</span>` : ""}
                    ${verifyBadge}
                </small>
            `;

            box.appendChild(div);
        });

        box.scrollTop = box.scrollHeight;

        await refreshUnread();
    }

    /* ---------------- FORWARD ---------------- */
    window.openForwardUI = function(){

        if(selectedMessages.size === 0){
            alert("No messages selected");
            return;
        }

        let users = prompt("Enter usernames (comma separated, max 6)");
        if(!users) return;

        let list = users.split(",").map(u => u.trim()).slice(0,6);

        selectedMessages.forEach(id => {

            let msg = document.querySelector(`[data-id="${id}"] .msg-text`).innerText;

            fetch("/forward", {
                method: "POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({
                    receivers: list,
                    message: msg
                })
            });

        });

        cancelSelection();
    };

    /* ---------------- UI HELPERS ---------------- */
    function showForwardBar(){
        document.getElementById("forward-bar").style.display = "flex";
        updateSelectionCount();
    }

    function updateSelectionCount(){
        document.getElementById("selected-count").innerText =
            selectedMessages.size + " selected";
    }

    window.cancelSelection = function(){
        selectedMessages.clear();
        selectionMode = false;

        document.querySelectorAll(".msg").forEach(el=>{
            el.classList.remove("selected");
        });

        document.getElementById("forward-bar").style.display = "none";
    };

    /* ---------------- UNREAD REFRESH ---------------- */
    async function refreshUnread() {
        const res = await fetch("/unread");
        const data = await res.json();

        document.querySelectorAll(".user-item").forEach(item => {
            const username = item.querySelector(".user-name").innerText;

            let badge = item.querySelector(".badge");

            if (data[username] > 0) {
                if (!badge) {
                    badge = document.createElement("span");
                    badge.className = "badge";
                    item.appendChild(badge);
                }
                badge.innerText = data[username];
            } else {
                if (badge) badge.remove();
            }
        });
    }

    /* ---------------- SEARCH (STABLE VERSION) ---------------- */
    if(search){
        search.addEventListener("input", function(){

            const val = search.value.toLowerCase();

            document.querySelectorAll(".user-item").forEach(item => {
                const name = item.querySelector(".user-name").innerText.toLowerCase();

                if(name.includes(val)){
                    item.style.display = "flex";
                } else {
                    item.style.display = "none";
                }
            });

        });
    }

});