angular.module 'app', ['ngRoute', 'ngSanitize']
.config ['$routeProvider', '$locationProvider', ($routeProvider, $locationProvider)->
  $locationProvider.html5Mode(true)
  $routeProvider
    .when '/',
      templateUrl: '/static/ui/home.html'
      controller: 'HomeController'
    .when '/shared/:sid',
      templateUrl: '/static/ui/shared.html'
      controller: 'SharedController'
    .otherwise
      templateUrl: '/static/ui/404.html'
]

.controller 'RootController', ['$scope', '$sce', '$http', '$interval', 'util', ($scope, $sce, $http, $interval, util)->
  $scope.app =
    name: 'GoPhotos'
    title: 'GoPhotos'
    copyright: $sce.trustAsHtml('Created by <a href="https://github.com/tjumyk" target="_blank">Kelvin Miao</a>')

  $scope.format_date = util.formatDate
]

.controller 'HomeController', ['$scope', '$sce', '$http', '$location', 'util', ($scope, $sce, $http, $location, util)->
  $http.get('/api/albums').then (response)->
    $scope.albums = response.data
    $http.get('/api/shared-albums').then (response)->
      $scope.shared_albums = {}
      for share in response.data
        for album in $scope.albums
          if album.id == share.aid
            album._shared = share
            break
    , (response)->
      alert(util.formatResponseError(response))
  , (response)->
    alert(util.formatResponseError(response))

  $scope.share_album = (album)->
    album._sharing = true
    $http.get('/api/share-album/' + album.id).then (response)->
      album._sharing = false
      $location.url(response.data.url)
    , (response)->
      album._sharing = false
      alert(util.formatResponseError(response))

  $scope.stop_share_album = (album)->
    return if !album._shared
    album._stopping_share = true
    $http.delete('/api/shared-albums/' + album._shared.sid).then (response)->
      album._stopping_share = false
      delete album._shared
    , (response)->
      album._stopping_share = false
      alert(util.formatResponseError(response))
]

.controller 'SharedController', ['$scope', '$sce', '$http', '$routeParams', '$timeout', 'util', ($scope, $sce, $http, $routeParams, $timeout, util)->
  lazyload = new LazyLoad()
  pswp_params =
    element: $('.pswp')[0]
    ui: PhotoSwipeUI_Default
    items: []
    options:
      history: false
      getThumbBoundsFn: (i)->
        thumbnail = $(".thumbnail.image:eq(#{i})")[0]
        pageYScroll = window.pageYOffset || document.documentElement.scrollTop
        rect = thumbnail.getBoundingClientRect()
        ret =
          x: rect.left
          y: rect.top + pageYScroll
          w: rect.width
        return ret

  $http.get('/api/shared-albums/' + $routeParams['sid']).then (response)->
    $scope.data = response.data
    $timeout ->
      lazyload.update()
    items = []
    for p in $scope.data.photos
      p = angular.copy(p)
      items.push
        src: p.content.url
        w: p.width
        h: p.height
    pswp_params.items = items
  , (response)->
    alert(util.formatResponseError(response))

  $scope.show_photo = (index)->
    pswp_params.options.index = index
    pswp = new PhotoSwipe(pswp_params.element, pswp_params.ui, pswp_params.items, pswp_params.options)
    pswp.init()


]
