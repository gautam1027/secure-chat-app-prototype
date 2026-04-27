const socket = io();

let selectedUser = null;

const box = document.getElementById("chat-box");
const form = document.getElementById("chat-form");
const msgInput = document.getElementById("message");

function roomName(a,b){
    return [a,b].sort().join("_");
}

/* GLOBAL FUNCTION FOR HTML onclick */
window.openChat = function(username){

    selectedUser = username;

    document.getElementById("chat-header").innerText = username;

    socket.emit("join", {
        room: roomName(CURRENT_USER, selectedUser)
    });

    loadMessages();
};

form.addEventListener("submit", function(e){
    e.preventDefault();

    if(!selectedUser) return;

    const msg = msgInput.value.trim();
    if(msg === "") return;

    socket.emit("send_message", {
        sender: CURRENT_USER,
        receiver: selectedUser,
        message: msg
    });

    msgInput.value = "";
});

socket.on("new_message", function(){
    loadMessages();
});

async function loadMessages(){

    if(!selectedUser) return;

    const res = await fetch("/messages/" + selectedUser);
    const data = await res.json();

    box.innerHTML = "";

    data.forEach(item => {

        let div = document.createElement("div");

        div.className =
            item.sender === CURRENT_USER
            ? "msg sent"
            : "msg received";

        div.innerHTML = `
            <div>${item.message}</div>
            <small>${item.time}</small>
        `;

        box.appendChild(div);
    });

    box.scrollTop = box.scrollHeight;
}