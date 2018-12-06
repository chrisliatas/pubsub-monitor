// custom application js

$( document ).ready(() => {
  console.log("[main.js] loaded");
});
// init Infinite Scroll
var $container = $(".js-infinite-layout").infiniteScroll({
    path: ".pagination__next",
    append: ".user-item",
    //button: ".view-more-button",
    //scrollThreshold: false,
    status: ".page-load-status",
    hideNav: ".js-infinite-nav",
});
// flask-moment fix to work with Infinite Scroll
$container.on( 'append.infiniteScroll', function( event, response, path, items ) {
  $(".flask-moment").removeClass("flask-moment").show();
});
var poll = true;
function start_polling() {
    $.get("/polling_pubsub", function (data, status) {
        resp_o_log(data, status);
        info_message((data.status === "success") ?
            "Started background task: polling Pull-subscription" : "A polling task is currently in progress!");
    });
}
function stop_polling() {
    $.post("/polling_pubsub", function (data, status) {
        resp_o_log(data, status);
        info_message((data.status === "terminated") ?
            "Terminating background task: polling Pull-subscription" : "There was an error in background tasks!");
    });
}
function resp_o_log(data, status) {
    console.log("Status: " + status);
    console.log("Data: status: " + data.status + ", task_id: " + data.task_id);
}
function info_message(message) {
    $("#clnt-alert").text(message).fadeIn(1000);
    setTimeout(function() {
        $("#clnt-alert").fadeOut(1000);
    }, 7000);
}
function set_task_progress(description, progress, showalert) {
    const task = $("#current-task");
    if (showalert && task.is(":hidden")) {
        $("#current-task span:first").text(description + ": ");
        $("#task-progress strong").text(progress + "...");
        task.fadeIn(1000);
    }
    if (!showalert && task.is(":visible")) {
        $("#task-progress strong").text(progress + "!");
        setTimeout(function() {
            task.fadeOut(1000);
        }, 5000);
    }
}
function change_pwd(npwd) {
    let posting = $.post("/change_password", { newpwd: npwd });
    posting.done(function (data, status) {
        alert("Password: " + data.status);
    });
}
$("#changepwd").submit(function (e) {
    e.preventDefault();
    const newpass = $('#newpass').val();
    const cnfrmpass = $('#cnfrmpass').val();
    (newpass !== cnfrmpass) ? alert("Passwords do not match!") : change_pwd(newpass);
    $(this).trigger("reset");
});
$("#pollnav").click(function (e) {
    e.preventDefault();
    $(this).text(($(this).text() === "Start polling") ? "Stop polling" : "Start polling");
    poll ? start_polling() : stop_polling();
    poll = !poll;
});
$(function() {
    let since = 0;
    setInterval(function() {
        $.ajax("/notifications?since=" + since).done(
            function(notifications) {
                for (let i = 0; i < notifications.length; i++) {
                    if (notifications[i].name === "task_progress") {
                        console.log("notif.data.progress: " + notifications[i].data.progress);
                        set_task_progress(notifications[i].data.description,
                            notifications[i].data.progress, (notifications[i].data.progress !== "Finished"));
                    }
                    since = notifications[i].timestamp;
                }
            }
        );
        $.getJSON("/useritems").done(function (jsondata) {
            //console.log("New items:" + jsondata.items + " Status:" + jsondata.status);
            const table = $('#useritems');
            $.each(jsondata.items, function (i, item) {
                table.prepend(item);
            });
        });
    }, 5000);
});