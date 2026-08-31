(function () {
  var targets = document.querySelectorAll('[data-reveal]');
  if (!targets.length || !('IntersectionObserver' in window)) return;

  document.body.classList.add('js-reveal');

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );

  targets.forEach(function (el) {
    observer.observe(el);
  });
})();
