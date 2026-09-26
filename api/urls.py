from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(prefix="users", viewset=views.UserViewSet, basename="user")
router.register(prefix="parties", viewset=views.PartyViewSet, basename="party")
router.register(prefix="elections", viewset=views.ElectionViewSet, basename="election")
router.register(
    prefix="candidates", viewset=views.CandidateViewSet, basename="candidate"
)
router.register(prefix="positions", viewset=views.PositionViewSet, basename="position")
router.register(prefix="lgas", viewset=views.LGAViewSet, basename="lga")
router.register(prefix="states", viewset=views.StateViewSet, basename="state")
router.register(prefix="wards", viewset=views.WardViewSet, basename="ward")
router.register(
    prefix="polling-units", viewset=views.PollingUnitViewSet, basename="polling-unit"
)
router.register(prefix="vote", viewset=views.VoteViewSet, basename="vote")
router.register(prefix="voters", viewset=views.VoterViewSet, basename="voter")

# ADMIN URLS

router.register(
    prefix="admin/users", viewset=views.AdminUserViewSet, basename="admin-user"
)
router.register(
    prefix="admin/voters", viewset=views.AdminVoterViewSet, basename="admin-voter"
)
router.register(
    prefix="admin/elections",
    viewset=views.AdminElectionViewSet,
    basename="admin-election",
)

router.register(
    prefix="admin/parties",
    viewset=views.AdminPartiesViewSet,
    basename="admin-party",
)

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("platform-stats/", views.PlatformStatsView.as_view(), name="platform-stats"),
    path("pvc-verification/", views.VerifyPVCView.as_view(), name="pvc-verification"),
    path("get-candidates/", views.CandidateView.as_view(), name="view-candidates"),
    path("", include(router.urls)),
]
