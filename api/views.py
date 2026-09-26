from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import ActivityLog
from accounts.permissions import IsUserAdmin
from api.utils import log_activity
from elections.models import (
    Election,
    ElectionChoices,
    Position,
    PositionChoices,
    StatusChoices,
)
from parties.models import (
    Candidate,
    Party,
)
from voting.models import (
    LGA,
    PollingUnit,
    State,
    Vote,
    Voter,
    Ward,
)
from voting.permissions import IsApprovedVoter

from .serializers import (
    ActivitySerializer,
    AdminCandidateSerializer,
    AdminCreateSerializer,
    AdminTokenObtainPairSerializer,
    AdminUserSerializer,
    AdminVoterSerializer,
    CandidateMinimalSerializer,
    CandidateSerializer,
    ChangePasswordSerializer,
    ElectionCandidateSerializer,
    ElectionPositionSerializer,
    ElectionSerializer,
    GetElectionSerializer,
    LgaSerializer,
    LoginSerializer,
    PartySerializer,
    PollingUnitSerializer,
    PositionSerializer,
    ProfileUpdateSerializer,
    PvcVerificationSerializer,
    RegisterSerializer,
    RegisterVoterSerializer,
    StateSerializer,
    UserSerializer,
    VerifyVoterSerializer,
    ViewUserSerializer,
    ViewVoterSerializer,
    VoterSerializer,
    VoteSerializer,
    VotingHistorySerializer,
    WardSerializer,
)

# Create your views here.
User = get_user_model()


class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PlatformStatsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        userStats = User.objects.count()
        polling_units = PollingUnit.objects.count()
        voters = Voter.objects.count()
        wards = Ward.objects.count()

        result_data = {
            "user_stats": userStats,
            "polling_units": polling_units,
            "voters": voters,
            "wards": wards,
        }
        return Response(result_data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication],
        parser_classes=[MultiPartParser, FormParser],
    )
    @transaction.atomic
    def register_voter(self, request):
        serializer = RegisterVoterSerializer(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        voter = serializer.save(user=request.user)
        voter.voter_status = Voter.Status.PENDING
        voter.save(update_fields=["voter_status"])
        log_activity(
            user=request.user,
            action=ActivityLog.Action.REGISTER_VOTER,
            status=ActivityLog.Status.SUCESS,
            description="Voter Registration Application",
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsApprovedVoter],
        authentication_classes=[JWTAuthentication],
    )
    @transaction.atomic
    def vote(self, request):
        serializer = VoteSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        log_activity(
            user=request.user,
            action=ActivityLog.Action.VOTE,
            status=ActivityLog.Status.SUCESS,
            description="Voting Exercise Completed",
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["PUT", "PATCH"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    @transaction.atomic
    def update_user(self, request):
        serializer = ProfileUpdateSerializer(
            request.user.profile, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            log_activity(
                user=request.user,
                action=ActivityLog.Action.UPDATE_PROFILE,
                status=ActivityLog.Status.SUCESS,
                description="Profile Update Completed",
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["PATCH"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def change_password(self, request):

        serializer = ChangePasswordSerializer(
            request.user, data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_activity(
            user=request.user,
            action=ActivityLog.Action.CHANGE_PASSWORD,
            status=ActivityLog.Status.SUCESS,
            description="Password Change Successful",
        )

        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "Registration successful"}, status=status.HTTP_201_CREATED
        )


# class RegisterVoter(generics.CreateAPIView):
#     serializer_class = RegisterVoterSerializer
#     queryset = Voter.objects.all()
#     permission_classes = [IsAuthenticated]

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user, voter_status=Voter.Status.PENDING)


class LoginView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


class PartyViewSet(viewsets.ModelViewSet):
    queryset = Party.objects.all()
    serializer_class = PartySerializer
    permission_classes = [AllowAny]

    def get_permissions(self):

        if self.action == "create":
            return [permissions.IsAuthenticated(), IsUserAdmin()]
        return super().get_permissions()

    def get_authenticators(self) -> list[BaseAuthentication]:

        if self.request and self.request.method == "POST":
            return [JWTAuthentication()]
        return super().get_authenticators()


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    # permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()

        election_id = self.request.query_params.get("election")
        position_id = self.request.query_params.get("position")

        if election_id:
            queryset = queryset.filter(election=election_id)

        if position_id:
            queryset = queryset.filter(position=position_id)

        return queryset

    def get_serializer_class(self):

        # we'll store the url parameters as variables for a more cleaner checking

        election = self.request.query_params.get("election")
        position = self.request.query_params.get("position")

        if self.action == "list" and election and position:
            return ElectionCandidateSerializer

        if self.action == "list" and election:
            return ElectionCandidateSerializer

        return CandidateSerializer


class ElectionViewSet(viewsets.ModelViewSet):
    queryset = Election.objects.all()
    serializer_class = ElectionSerializer
    # permission_classes = [IsAuthenticatedOrReadOnly]
    # authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get("status")

        if status is not None:
            queryset = queryset.filter(status=status)

        return queryset

    @action(
        detail=True,
        methods=["get"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def get_candidates(self, request, pk=None):
        election = self.get_object()

        candidates = Candidate.objects.filter(election=election)
        # positions = Position.objects.filter(election=election)
        serializer = ElectionCandidateSerializer(candidates, many=True)

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def ballot(self, request, pk=None):
        election = self.get_object()

        positions = Position.objects.filter(election=election)
        serializer = ElectionPositionSerializer(positions, many=True)

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["GET"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticatedOrReadOnly],
    )
    def summary(self, request, pk=None):
        election = self.get_object()

        total_votes = Vote.objects.filter(election=election).count()

        voters_who_voted = (
            Vote.objects.filter(election=election).values("voter").distinct().count()
        )

        eligible_voters = Voter.objects.filter(
            voter_status=Voter.Status.APPROVED
        ).count()

        total_states = State.objects.count()

        turnout = 0

        if eligible_voters:
            turnout = (voters_who_voted / eligible_voters) * 100

        states_reported = (
            Vote.objects.filter(election=election)
            .values("voter__voter__polling_unit__ward__lga__state")
            .distinct()
            .count()
        )

        polling_units_counted = (
            Vote.objects.filter(election=election)
            .values("voter__voter__polling_unit")
            .distinct()
            .count()
        )

        party_results = (
            Vote.objects.filter(election=election)
            .values(
                "candidate__party__id",
                "candidate__party__name",
                "candidate__party__party_initials",
                "candidate__party__logo",
            )
            .annotate(votes=Count("id"))
            .order_by("-votes")
        )

        percentage = (voters_who_voted / total_votes) * 100

        candidate_results = (
            Vote.objects.filter(election=election)
            .values(
                "candidate",
                "candidate__user__first_name",
                "candidate__user__last_name",
                "candidate__party__party_initials",
                "position__name",
            )
            .annotate(votes=Count("id"))
            .order_by("position", "-votes")
        )

        state_results = (
            Vote.objects.filter(election=election)
            .values(
                "voter__voter__polling_unit__ward__lga__state__name",
                "candidate__party__party_initials",
            )
            .annotate(votes=Count("id"))
        )

        polling_unit_results = (
            Vote.objects.filter(election=election)
            .values(
                "voter__voter__polling_unit__name",
                "candidate__party__party_initials",
            )
            .annotate(votes=Count("id"))
        )

        return Response(
            {
                "turnout": turnout,
                "total_votes": total_votes,
                "states_reported": states_reported,
                "polling_units": polling_units_counted,
                "total_states": total_states,
                "party_results": party_results,
                "percentage": percentage,
                "candidate_results": candidate_results,
                "state_results": state_results,
                "polling_unit_results": polling_unit_results,
            }
        )

    @action(
        methods=["GET"],
        detail=False,
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def history(self, request):

        elections_participated = (
            Election.objects.filter(votes__voter=request.user).distinct().count()
        )

        elections = Election.objects.filter(votes__voter=request.user).distinct()

        serializer = VotingHistorySerializer(
            elections, many=True, context={"request": request}
        )

        return Response(
            {
                "elections": serializer.data,
                "elections_participated": elections_participated,
            }
        )


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer

    def get_queryset(self):

        queryset = super().get_queryset()
        election_id = self.request.query_params.get("election")

        if election_id:
            queryset = queryset.filter(election=election_id)

        return queryset

    @action(
        detail=False,
        methods=["GET"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated, IsUserAdmin],
    )
    def choices(self, request, pk=None):
        choices = [
            {"label": label, "value": value} for label, value in PositionChoices.choices
        ]

        return Response(choices, status=status.HTTP_200_OK)


class PositionView(generics.ListCreateAPIView):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer


class PositionEditView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer


class StateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["name"]
    ordering = ["name"]


class LGAViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LgaSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = LGA.objects.all()

        state_id = self.request.query_params.get("state")

        if state_id:
            queryset = queryset.filter(state_id=state_id)

        return queryset


class WardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WardSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = Ward.objects.all()

        lga_id = self.request.query_params.get("lga")

        if lga_id:
            queryset = queryset.filter(lga_id=lga_id)

        return queryset


class PollingUnitViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PollingUnitSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = PollingUnit.objects.all()

        ward_id = self.request.query_params.get("ward")
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)

        return queryset


class VoteViewSet(viewsets.ModelViewSet):
    serializer_class = VoteSerializer
    queryset = Vote.objects.all()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication],
    )
    def getElectionsData(self, request):
        # we will fetch the elections from the database
        election = (
            Election.objects.filter(status="active")
            .prefetch_related("positions__candidates")
            .first()
        )

        if not election:
            return Response(
                {"message": "There is no active election at the moment."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = GetElectionSerializer(election)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        authentication_classes=[JWTAuthentication],
    )
    def verify(self, request):
        serializer = VerifyVoterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from elections.models import StatusChoices

        election = serializer.validated_data["election"]
        vin = serializer.validated_data["vin"]

        if election.status != StatusChoices.ACTIVE:
            return Response(
                {"detail": "Election is not active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # verify voter
        try:
            voter = Voter.objects.get(vin=vin)
        except Voter.DoesNotExist:
            return Response(
                {"detail": "Invalid VIN."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"verified": True})

    @action(
        detail=False,
        methods=["POST"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def cast(self, request):
        serializer = VoteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def results(self, request):

        election_id = request.query_params.get("election")

        results = (
            Vote.objects.filter(election=election_id)
            .values("position", "candidate")
            .annotate(vote_count=Count("id"))
            .order_by("-vote_count")
        )

        total_votes = Vote.objects.filter(election_id=election_id).count()
        total_candidates = Candidate.objects.filter(election_id=election_id).count()

        results_per_position = {}
        candidates = []
        positions = []

        for result in results:
            position_id = result["position"]
            candidate_id = result["candidate"]
            vote_count = result["vote_count"]

            candidates.append(candidate_id)
            positions.append(position_id)

            a_result = {"candidate": candidate_id, "vote_count": vote_count}

            if position_id not in results_per_position:
                results_per_position[position_id] = []

            results_per_position[position_id].append(a_result)

        candidate_qs = Candidate.objects.filter(id__in=candidates)
        position_qs = Position.objects.filter(id__in=positions)

        candidate_lookup = {candidate.id: candidate for candidate in candidate_qs}
        position_lookup = {position.id: position for position in position_qs}

        final_results = {}

        for position_id, candidate_entries in results_per_position.items():
            position_obj = position_lookup[position_id]
            position_name = position_obj.name  # adjust if your field differs

            resolved_candidates = []
            for entry in candidate_entries:
                candidate_obj = candidate_lookup[entry["candidate"]]
                candidate_name = (
                    candidate_obj.user.get_full_name() or candidate_obj.user.username
                )

                resolved_candidates.append(
                    {
                        "candidate_id": entry["candidate"],
                        "candidate_name": candidate_name,
                        "vote_count": entry["vote_count"],
                    }
                )

            final_results[position_name] = resolved_candidates

        return Response(
            {
                "election_id": election_id,
                "total_votes": total_votes,
                "total_candidates": total_candidates,
                "results": final_results,
            }
        )


class VoterViewSet(viewsets.ModelViewSet):
    serializer_class = VoterSerializer
    queryset = Voter.objects.all()

    @action(
        detail=True,
        methods=["POST"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def approve_voter(self, request, pk=None):
        voter = self.get_object()

        voter.voter_status = Voter.Status.APPROVED

        voter.save()

        return Response({"message": "Approved"})

    @action(
        detail=False,
        methods=["POST"],
        permission_classes=[AllowAny],
    )
    def verify_pvc(self, request):
        serializer = PvcVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data["method"]

        if method == "vin":
            vin = serializer.validated_data["vin"]

            try:
                voter = Voter.objects.get(vin=vin)
            except Voter.DoesNotExist:
                return Response(
                    {"detail": "Voter not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        elif method == "details":
            state = serializer.validated_data["state"]
            lga = serializer.validated_data["lga"]
            first_name = serializer.validated_data["first_name"]
            last_name = serializer.validated_data["last_name"]

            try:
                voter = Voter.objects.get(
                    state=state,
                    lga=lga,
                    first_name__iexact=first_name,
                    last_name__iexact=last_name,
                )
            except Voter.DoesNotExist:
                return Response(
                    {"detail": "No voter found with the provided details."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Voter.MultipleObjectsReturned:
                return Response(
                    {
                        "detail": (
                            "Multiple voters were found with the provided details. "
                            "Please verify using your VIN."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            return Response(
                {"detail": "Invalid verification method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "Voter verified successfully.",
                "voter": VoterSerializer(voter).data,
            },
            status=status.HTTP_200_OK,
        )


class VerifyPVCView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PvcVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data["method"]

        if method == "vin":
            vin = serializer.validated_data["vin"]

            try:
                voter = Voter.objects.get(vin=vin)
            except Voter.DoesNotExist:
                return Response(
                    {"detail": "Voter not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        elif method == "details":
            state = serializer.validated_data["state"]
            lga = serializer.validated_data["lga"]
            first_name = serializer.validated_data["first_name"]
            last_name = serializer.validated_data["last_name"]

            try:
                voter = Voter.objects.get(
                    polling_unit__ward__lga__state=state,
                    polling_unit__ward__lga=lga,
                    user__first_name__iexact=first_name,
                    user__last_name__iexact=last_name,
                )
            except Voter.DoesNotExist:
                return Response(
                    {"detail": "No voter found with the provided details."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Voter.MultipleObjectsReturned:
                return Response(
                    {
                        "detail": (
                            "Multiple voters were found with the provided details. "
                            "Please verify using your VIN."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            return Response(
                {"detail": "Invalid verification method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "Voter verified successfully.",
                "voter": VoterSerializer(voter).data,
            },
            status=status.HTTP_200_OK,
        )


class CandidateView(generics.ListAPIView):
    queryset = Candidate.objects.all()
    serializer_class = ElectionCandidateSerializer
    permission_classes = [AllowAny]


# ADMIN VIEWSETS


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated, IsUserAdmin]

    @action(
        detail=False,
        methods=["GET"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated, IsUserAdmin],
    )
    def me(self, request):
        serializer = AdminUserSerializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["GET"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated, IsUserAdmin],
    )
    def admin_list(self, request, pk=None):

        admin = User.objects.filter(role=User.RoleChoices.ADMIN)
        total_number = User.objects.filter(role=User.RoleChoices.ADMIN).count()

        return Response(
            {"admins": admin, "total_admins": total_number}, status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=["POST"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated, IsUserAdmin],
    )
    def invite_admin(self, request):
        serializer = AdminCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Registration Successful"}, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["GET"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated, IsUserAdmin],
    )
    def stats(self, request, pk=None):

        total_users = User.objects.all().count()
        active_users = User.objects.filter(is_active=True).count()
        registered_voters = Voter.objects.all().count()
        eligible_voters = Voter.objects.filter(
            voter_status=Voter.Status.APPROVED
        ).count()
        total_elections = Election.objects.all().count()
        live_elections = Election.objects.filter(status="active").count()
        total_candidates = Candidate.objects.all().count()
        total_positions = Position.objects.all().count()
        total_states = State.objects.all().count()
        total_lgas = LGA.objects.all().count()
        total_wards = Ward.objects.all().count()
        total_polling_units = PollingUnit.objects.all().count()

        return Response(
            {
                "total_users": total_users,
                "active_users": active_users,
                "registered_voters": registered_voters,
                "eligible_voters": eligible_voters,
                "live_elections": live_elections,
                "total_elections": total_elections,
                "total_candidates": total_candidates,
                "total_positions": total_positions,
                "total_states": total_states,
                "total_lgas": total_lgas,
                "total_wards": total_wards,
                "total_polling_units": total_polling_units,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["GET"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated, IsUserAdmin],
    )
    def recent_activity(self, request):
        recent_activity = ActivityLog.objects.order_by("-created_at")[:5]

        serializer = ActivitySerializer(recent_activity, many=True)

        return Response(
            {"recent_activities": serializer.data}, status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsAuthenticated, IsUserAdmin],
        authentication_classes=[JWTAuthentication],
    )
    def get_users(self, request):
        users = User.objects.filter(is_active=True)

        serializer = ViewUserSerializer(users, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["GET"],
    )
    def voters(self, request):
        voters = Voter.objects.order_by("-voter_status")

        serializer = ViewVoterSerializer(voters, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["DELETE"],
        permission_classes=[IsAuthenticated, IsUserAdmin],
        authentication_classes=[JWTAuthentication],
    )
    def deactivate(self, request, pk=None):
        user = self.get_object()

        if user == request.user:
            return Response(
                {"message": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.role == User.RoleChoices.ADMIN:
            return Response(
                {
                    "message": "You cannot deactivate an admin account. Please contact IT Support."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.is_staff or user.is_superuser:
            return Response(
                {
                    "message": "You cannot deactivate a staff or a superuser account. Please contact IT Support."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response({"message": "User Deactivated"}, status=status.HTTP_200_OK)


class AdminVoterViewSet(viewsets.ModelViewSet):
    queryset = Voter.objects.all()
    serializer_class = AdminVoterSerializer

    @action(
        detail=True,
        methods=["PATCH"],
        permission_classes=[IsAuthenticated, IsUserAdmin],
        authentication_classes=[JWTAuthentication],
    )
    @transaction.atomic
    def approve_voter(self, request, pk=None):

        voter = self.get_object()

        if voter.voter_status == Voter.Status.APPROVED:
            return Response(
                {"message": "Voter already approved"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        voter.voter_status = Voter.Status.APPROVED
        voter.save(update_fields=["voter_status"])

        return Response(
            {"message": "Voter approved successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["PATCH"],
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated, IsUserAdmin],
    )
    @transaction.atomic
    def decline_voter(self, request, pk=None):

        user = self.get_object()

        voter = user.voter

        voter.voter_status = Voter.Status.REJECTED
        voter.save(update_fields=["voter_status"])

        return Response(
            {"message": "Voter Registration Request Rejected successfully."},
            status=status.HTTP_200_OK,
        )


class AdminElectionViewSet(viewsets.ModelViewSet):
    queryset = Election.objects.all()
    serializer_class = ElectionSerializer
    permission_classes = [IsAuthenticated, IsUserAdmin]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args: Any, **kwargs: Any) -> Response:
        return super().list(request, *args, **kwargs)

    def create(self, request, *args: Any, **kwargs: Any) -> Response:
        return super().create(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsAuthenticated, IsUserAdmin],
        authentication_classes=[JWTAuthentication],
    )
    @transaction.atomic
    def types(self, request, pk=None):
        types = [
            {"value": value, "label": label} for value, label in ElectionChoices.choices
        ]

        return Response(types, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsAuthenticated, IsUserAdmin],
        authentication_classes=[JWTAuthentication],
    )
    def status_types(self, request, pk=None):
        status_types = [
            {"value": value, "label": label} for value, label in StatusChoices.choices
        ]

        return Response(status_types, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        permission_classes=[IsAuthenticated, IsUserAdmin],
        authentication_classes=[JWTAuthentication],
    )
    def party(self, request, pk=None):
        election = self.get_object()
        total_parties = Candidate.objects.filter(election=election).distinct().count()
        total_candidates = Candidate.objects.filter(election=election).count()

        parties = Candidate.objects.filter(election=election).distinct()
        serializer = AdminCandidateSerializer(parties, many=True)
        return Response(
            {
                "parties": total_parties,
                "candidates": total_candidates,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class AdminPartiesViewSet(viewsets.ModelViewSet):
    serializer_class = PartySerializer
    queryset = Party.objects.all()
    permission_classes = [IsAuthenticated, IsUserAdmin]
    authentication_classes = [JWTAuthentication]
