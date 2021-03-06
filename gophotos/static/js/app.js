// Generated by CoffeeScript 1.12.5
(function() {
  angular.module('app', ['ngRoute', 'ngSanitize']).config([
    '$routeProvider', '$locationProvider', function($routeProvider, $locationProvider) {
      $locationProvider.html5Mode(true);
      return $routeProvider.when('/', {
        templateUrl: '/static/ui/home.html',
        controller: 'HomeController'
      }).when('/shared/:sid', {
        templateUrl: '/static/ui/shared.html',
        controller: 'SharedController'
      }).otherwise({
        templateUrl: '/static/ui/404.html'
      });
    }
  ]).controller('RootController', [
    '$scope', '$sce', '$http', '$interval', 'util', function($scope, $sce, $http, $interval, util) {
      $scope.app = {
        name: 'GoPhotos',
        title: 'GoPhotos',
        copyright: $sce.trustAsHtml('Created by <a href="https://github.com/tjumyk" target="_blank">Kelvin Miao</a>')
      };
      return $scope.format_date = util.formatDate;
    }
  ]).controller('HomeController', [
    '$scope', '$sce', '$http', '$location', 'util', function($scope, $sce, $http, $location, util) {
      $http.get('/api/albums').then(function(response) {
        $scope.albums = response.data;
        return $http.get('/api/shared-albums').then(function(response) {
          var album, j, len, ref, results, share;
          $scope.shared_albums = {};
          ref = response.data;
          results = [];
          for (j = 0, len = ref.length; j < len; j++) {
            share = ref[j];
            results.push((function() {
              var k, len1, ref1, results1;
              ref1 = $scope.albums;
              results1 = [];
              for (k = 0, len1 = ref1.length; k < len1; k++) {
                album = ref1[k];
                if (album.id === share.aid) {
                  album._shared = share;
                  break;
                } else {
                  results1.push(void 0);
                }
              }
              return results1;
            })());
          }
          return results;
        }, function(response) {
          return alert(util.formatResponseError(response));
        });
      }, function(response) {
        return alert(util.formatResponseError(response));
      });
      $scope.share_album = function(album) {
        album._sharing = true;
        return $http.get('/api/share-album/' + album.id).then(function(response) {
          album._sharing = false;
          return $location.url(response.data.url);
        }, function(response) {
          album._sharing = false;
          return alert(util.formatResponseError(response));
        });
      };
      return $scope.stop_share_album = function(album) {
        if (!album._shared) {
          return;
        }
        album._stopping_share = true;
        return $http["delete"]('/api/shared-albums/' + album._shared.sid).then(function(response) {
          album._stopping_share = false;
          return delete album._shared;
        }, function(response) {
          album._stopping_share = false;
          return alert(util.formatResponseError(response));
        });
      };
    }
  ]).controller('SharedController', [
    '$scope', '$sce', '$http', '$routeParams', '$timeout', 'util', function($scope, $sce, $http, $routeParams, $timeout, util) {
      var lazyload, pswp_params;
      lazyload = new LazyLoad();
      pswp_params = {
        element: $('.pswp')[0],
        ui: PhotoSwipeUI_Default,
        items: [],
        options: {
          history: false,
          getThumbBoundsFn: function(i) {
            var pageYScroll, rect, ret, thumbnail;
            thumbnail = $(".thumbnail.image:eq(" + i + ")")[0];
            pageYScroll = window.pageYOffset || document.documentElement.scrollTop;
            rect = thumbnail.getBoundingClientRect();
            ret = {
              x: rect.left,
              y: rect.top + pageYScroll,
              w: rect.width
            };
            return ret;
          }
        }
      };
      $http.get('/api/shared-albums/' + $routeParams['sid']).then(function(response) {
        var items, j, len, p, ref;
        $scope.data = response.data;
        $timeout(function() {
          return lazyload.update();
        });
        items = [];
        ref = $scope.data.photos;
        for (j = 0, len = ref.length; j < len; j++) {
          p = ref[j];
          p = angular.copy(p);
          items.push({
            src: p.content.url,
            w: p.width,
            h: p.height
          });
        }
        return pswp_params.items = items;
      }, function(response) {
        return alert(util.formatResponseError(response));
      });
      return $scope.show_photo = function(index) {
        var pswp;
        pswp_params.options.index = index;
        pswp = new PhotoSwipe(pswp_params.element, pswp_params.ui, pswp_params.items, pswp_params.options);
        return pswp.init();
      };
    }
  ]);

}).call(this);

//# sourceMappingURL=app.js.map
