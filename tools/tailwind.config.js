// Rebuild the bundled CSS after changing classes in templates/ or static/app.js:
//   cd tools && npm i tailwindcss@3.4.17 && ./build-css.sh
module.exports = {
  darkMode: 'class',
  content: ['../app/templates/*.html', '../app/static/*.js'],
};
