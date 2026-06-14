var ismobile = navigator.userAgent.match(/(iPhone)|(iPod)|(android)|(webOS)|(BlackBerry)/i);
var scroll_x = $(window).width() / 2;
var floor_x = 0;
var mario_x = 0;
var direction = false;
var music_play = false;
var interval_left = false;
var interval_right = false;


if (ismobile) scroll_x -= 170;
else scroll_x -= 240;

$('#scroll').css('left', scroll_x + 'px');

$('.tweet').click(function () {
    window.open('https://twitter.com/intent/tweet?text=' + document.title + '&tw_p=tweetbutton&url=' + document.location.href);
    return false;
});

function moveTo(pos) {

    diff = ismobile ? 10 : 15;

    if (pos == 'left') {

        if (!direction) {
            direction = 'left';
            $('#mario').css('-webkit-transform', 'scaleX(-1)');
        }
        floor_x += diff;
        scroll_x += diff;
        mario_x -= 65;
        if (mario_x == -195) mario_x = 0;

    } else if (pos == 'right') {

        if (!direction) {
            direction = 'right';
            $('#mario').css('-webkit-transform', 'scaleX(1)');
        }
        floor_x -= diff;
        scroll_x -= diff;
        mario_x -= 65;
        if (mario_x == -195) mario_x = 0;

    } else {
        direction = false;
    }


    // reach end
    if (scroll_x < (parseInt($('#scroll').css('width')) * -1)) {
        scroll_x = $(window).width();


        // reach start
    } else if (scroll_x > $(window).width()) {
        scroll_x = parseInt($('#scroll').css('width')) * -1;
    }

    $('#scroll').css('left', scroll_x + 'px');
    $('#floor').css('background-position-x', floor_x + 'px');
    $('#mario').css('background-position-x', mario_x + 'px');
}


function playMusic() {
    if (!music_play) {
        document.getElementById("bg_music").play();
        music_play = true;
    }
}

function moveLeft() {
    playMusic();

    direction = false;
    if (!interval_left) {
        interval_left = setInterval(function () {
            moveTo('left');
        }, 100);
    }
}

function moveRight() {
    playMusic();

    direction = false;
    if (!interval_right) {
        interval_right = setInterval(function () {
            moveTo('right');
        }, 100);
    }
}

function stopMove() {
    clearInterval(interval_left);
    clearInterval(interval_right);
    interval_left = false;
    interval_right = false;
}




$(function () {

    $("body, #scroll").click(function () {
        playMusic();
    });

    $("body").keydown(function (e) {
        if (e.keyCode == 37) {
            moveLeft();
        } else if (e.keyCode == 39) {
            moveRight();
        }
    });

    $("body").keyup(function (e) {
        stopMove();
    });

    $('#btn_left').on('mousedown touchstart', function () {
        moveLeft();
    });

    $('#btn_right').on('mousedown touchstart', function () {
        moveRight();
    });

    $('#btn_left, #btn_right').on('mouseup touchend', function (event) {
        stopMove();
    });

});
// --- Akhila custom: set scroll width based on boxes so you can add/remove sections safely
function setScrollWidth(){
    var boxes = $('#scroll .box').length;
    // each box is ~400px (width + left margin); add extra breathing room
    $('#scroll').css('width', (boxes * 420 + 600) + 'px');
}
$(function(){
    setScrollWidth();
    $(window).on('resize', function(){
        // keep Mario centered nicely on resize
        scroll_x = $(window).width() / 2;
        if (ismobile) scroll_x -= 170;
        else scroll_x -= 240;
        $('#scroll').css('left', scroll_x + 'px');
        setScrollWidth();
    });
});

// --- Akhila custom: warp Mario directly to a section, then keep left/right working from there
function jumpTo(index) {
    playMusic();
    stopMove();

    var $box = $('#scroll .box').eq(index);
    if (!$box.length) return;

    // Where the box currently sits inside #scroll (relative to scroll's own left edge)
    var boxOffset = $box.position().left;

    // We want that box to land roughly under Mario (screen center).
    // scroll_x is the #scroll element's "left". Mario is fixed near center.
    var marioCenter = $(window).width() / 2 - 30; // matches #mario margin-left:-30px
    scroll_x = marioCenter - boxOffset;

    // Keep within the same wrap bounds the movement logic uses
    $('#scroll').css('left', scroll_x + 'px');

    // Reset facing so the next key/arrow press behaves predictably
    direction = false;

    // Mark active nav link
    $('.nav_link').removeClass('active');
    $('.nav_link[data-index="' + index + '"]').addClass('active');
}

$(function(){
    $('.nav_link[data-index]').on('click', function(){
        var idx = parseInt($(this).attr('data-index'), 10);
        jumpTo(idx);
    });
});
