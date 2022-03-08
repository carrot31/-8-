let isActive = false;

const showMenu = (toggleId, navbarId) => {
    const toggle = document.getElementById(toggleId),
        navbar = document.getElementById(navbarId);

    console.log(toggle, navbar)

    if( toggle && navbar ) {
        toggle.addEventListener('click', () => {
            navbar.classList.toggle('expander');
            isActive = !isActive
            console.log(isActive)
        })
    }
}

showMenu('nav-toggle', 'navbar', 'body-pd')


const linkColor = document.querySelectorAll('.nav_link')
function colorLink() {
    if(isActive) {
        linkColor.forEach(l => l.classList.remove('active'))
        this.classList.add('active')
    } else {
        linkColor.forEach(l => l.classList.remove('active'))
    }

}
linkColor.forEach(l=> l.addEventListener('click', colorLink))


const linkCollapse = document.getElementsByClassName('collapse_link')

let i;

for(i=0; i<linkCollapse.length; i++) {
    linkCollapse[i].addEventListener('click', function(){
        const collapseMenu = this.nextElementSibling
        collapseMenu.classList.toggle('showCollapse')

        const rotate = collapseMenu.previousElementSibling
        rotate.classList.toggle('rotate')
    });
}
