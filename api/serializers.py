from dataclasses import field
from datetime import date, datetime
from os import read
from typing import Any

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import AuthUser, TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token

from accounts.models import ActivityLog, Profile
from elections.models import Election, Position, StatusChoices
from parties.models import (
    Candidate,
    Party,
)
from voting.models import LGA, PollingUnit, State, Vote, Voter, Ward

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: AuthUser) -> Token:
        token = super().get_token(user=user)

        token["role"] = user.role

        return token


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:

        data = super().validate(attrs=attrs)

        if self.user.role != User.RoleChoices.ADMIN:
            raise serializers.ValidationError(
                "You are not authorized to access this resource."
            )

        return data

    @classmethod
    def get_token(cls, user: AuthUser) -> Token:
        token = super().get_token(user=user)

        token["role"] = user.role

        return token


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = "__all__"


class LgaSerializer(serializers.ModelSerializer):
    state = StateSerializer(read_only=True)

    class Meta:
        model = LGA
        fields = "__all__"


class WardSerializer(serializers.ModelSerializer):
    lga = LgaSerializer(read_only=True)

    class Meta:
        model = Ward
        fields = "__all__"


class PollingUnitSerializer(serializers.ModelSerializer):
    ward = WardSerializer(read_only=True)

    class Meta:
        model = PollingUnit
        fields = "__all__"


class VoterSerializer(serializers.ModelSerializer):
    polling_unit = PollingUnitSerializer(read_only=True)

    class Meta:
        model = Voter
        fields = [
            "vin",
            "polling_unit",
            "voter_status",
            "registration_date",
            "passport",
        ]
        extra_kwargs = {
            "vin": {"read_only": True},
        }


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "date_of_birth",
            "gender",
            "state_of_origin",
            "telephone_number",
            "profile_image",
            "address",
        ]
        extra_kwargs = {"user": {"read_only": True}}


class UserSerializer(serializers.ModelSerializer):
    voter = VoterSerializer(read_only=True)
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "middle_name",
            "email",
            "username",
            "role",
            "voter",
            "profile",
            "last_login",
            "date_joined",
        ]
        extra_kwargs = {
            "role": {"read_only": True},
        }

    def update(self, instance, validated_data):
        instance.email = validated_data.get("email", instance.email)

        instance.save()

        profile = instance.profile
        profile.telephone_number = validated_data.get(
            "telephone_number", profile.telephone_number
        )
        profile.address = validated_data.get("address", profile.address)
        profile.profile_image = validated_data.get(
            "profile_image", profile.profile_image
        )

        profile.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    telephone_number = serializers.CharField(required=True)
    gender = serializers.CharField(required=True)
    date_of_birth = serializers.DateField(required=True)
    state_of_origin = serializers.CharField(required=True)

    def validate_date_of_birth(self, value):
        today = date.today()
        age = today.year - value.year
        birthDate = value.day

        monthDiff = today.month - value.month

        if monthDiff < 0 or (monthDiff == 0 and today.day < birthDate):
            age -= 1

        if age < 18:
            raise serializers.ValidationError(
                "You must be at least 18 years old to register"
            )

        return value

    class Meta:
        model = User
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "password",
            "confirm_password",
            "telephone_number",
            "gender",
            "date_of_birth",
            "state_of_origin",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already in use."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop(
            "password"
        )  # .pop removes the field from showing in our response.

        gender = validated_data.pop("gender")
        telephone_number = validated_data.pop("telephone_number")
        date_of_birth = validated_data.pop("date_of_birth")
        state_of_origin = validated_data.pop("state_of_origin")

        username = validated_data["email"].split("@")[0]

        user = User.objects.create_user(
            password=password,
            username=username,
            **validated_data,  # this is the extra fields. This contains all the data for the rest fields.
        )

        user.profile.gender = gender
        user.profile.telephone_number = telephone_number
        user.profile.date_of_birth = date_of_birth
        user.profile.state_of_origin = state_of_origin

        user.profile.save()
        return Response(
            {"message": "Registration Successful"}, status=status.HTTP_201_CREATED
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")
        attrs["user"] = user
        return attrs


class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = ["id", "name", "party_initials", "logo", "description", "party_slogan"]

    def validate(self, attrs):

        name = attrs["name"]
        party_initials = attrs["party_initials"]
        logo = attrs["logo"]
        description = attrs["description"]
        party_slogan = attrs["party_slogan"]

        if len(party_initials) > 6:
            raise serializers.ValidationError(
                "Party Initials must not be more than 6 characters"
            )

        return attrs

    def validate_logo(self, value):

        maximum_size = 2 * 1024 * 1024

        valid_extensions = ["image/jpeg", "image/png", "image/svg", "image/jpg"]

        if value.size > maximum_size:
            raise serializers.ValidationError("Logo file size cannot exceed 2MB")

        if value.content_type not in valid_extensions:
            raise serializers.ValidationError("Invalid logo file type")

        return value


class CandidateUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "full_name", "email"]


class CandidateMinimalSerializer(serializers.ModelSerializer):
    user = CandidateUserSerializer(read_only=True)
    party = PartySerializer(read_only=True)

    class Meta:
        model = Candidate
        fields = ["id", "user", "party", "candidate_image"]


# Position Serializer (Nesting the candidates running for this position)
class PositionNestedSerializer(serializers.ModelSerializer):
    candidates = CandidateMinimalSerializer(many=True, read_only=True)
    name_display = serializers.CharField(source="get_name_display", read_only=True)

    class Meta:
        model = Position
        fields = ["id", "name", "name_display", "description", "candidates"]


class ElectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = "__all__"

    def validate(self, attrs):
        title = attrs.get("title")
        election_type = attrs.get("election_type")
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        description = attrs.get("description")
        status = attrs.get("status")

        queryset = Election.objects.filter(title=title, election_type=election_type)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Duplicate election type is not permitted"
            )

        if start_date >= end_date:
            raise serializers.ValidationError("End date must be later than start date")
        return attrs


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = "__all__"

    def validate(self, attrs):
        election = attrs.get("election")
        party = attrs.get("party")
        position = attrs.get("position")

        queryset = Candidate.objects.filter(election=election, party=party)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "This candidate already exists for this party in this election."
            )

        if Candidate.objects.filter(user=attrs.get("user"), election=election).exists():
            raise serializers.ValidationError(
                "This user already exists in this election"
            )

        if Candidate.objects.filter(user=attrs.get("user"), position=position).exists():
            raise serializers.ValidationError(
                "Candidate can only vie for one position at a time"
            )
        return attrs

    def create(self, validated_data):
        user = validated_data.get("user")

        # we create the candidate first
        candidate = Candidate.objects.create(**validated_data)

        # Then we update the user role
        user.role = User.RoleChoices.CANDIDATE
        user.save(update_fields=["role"])

        return candidate


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "name", "election", "description"]

    def validate(self, attrs):
        name = attrs.get("name")
        election = attrs.get("election")

        queryset = Position.objects.filter(name=name, election=election)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("Duplicate entry not permitted!")

        return attrs


class ElectionPositionSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True, read_only=True)

    class Meta:
        model = Position
        fields = ["id", "name", "description", "candidates"]


class ElectionCandidateSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="user.get_full_name", read_only=True)
    party = PartySerializer(read_only=True)
    position = PositionSerializer(read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "candidate_name",
            "candidate_image",
            "party",
            "position",
        ]


class VoterStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = ["voter_status"]

    def validate_voter_status(self, value):
        if value not in ["not_applied"]:
            raise serializers.ValidationError("Invalid status update.")
        return value


class VoteSerializer(serializers.ModelSerializer):
    election_title = serializers.CharField(source="election.title", read_only=True)

    candidate_name = serializers.CharField(
        source="candidate.user.get_user_fullname", read_only=True
    )

    position_name = serializers.CharField(
        source="position.get_name_display", read_only=True
    )

    vin = serializers.CharField(read_only=True)

    class Meta:
        model = Vote
        fields = [
            "election",
            "position",
            "candidate",
            "election_title",
            "candidate_name",
            "position_name",
            "vin",
        ]

    def validate(self, attrs):
        voter = self.context["request"].user
        election = attrs.get("election")
        candidate = attrs.get("candidate")
        position = attrs.get("position")
        vin = attrs.get("vin")

        if election.status != StatusChoices.ACTIVE:
            raise serializers.ValidationError({"error": "This Election is not active."})

        try:
            voter_profile = voter.voter
        except Voter.DoesNotExist:
            raise serializers.ValidationError(
                {"error": "You are not registered as a voter."}
            )

        if voter.voter.voter_status != Voter.Status.APPROVED:
            raise serializers.ValidationError(
                {"error": "Your voter registration has not been approved"}
            )

        now = timezone.now()
        if not (election.start_date <= now <= election.end_date):
            raise serializers.ValidationError(
                {"error": "This election is not within its voting period."}
            )

        if candidate.election != election:
            raise serializers.ValidationError(
                {"error": "This candidate is not part of this election."}
            )

        if candidate.position != position:
            raise serializers.ValidationError(
                {"error": "This candidate is not vying for this position."}
            )

        if Vote.objects.filter(
            voter=voter, election=election, position=position
        ).exists():
            raise serializers.ValidationError(
                {"error": "You have already voted for this position in this election."}
            )

        return attrs

    def create(self, validated_data):
        voter = self.context["request"].user
        return Vote.objects.create(voter=voter, **validated_data)


class RegisterVoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = "__all__"
        read_only_fields = ["user"]

    def validate(self, attrs):

        state = attrs.get("state")
        lga = attrs.get("lga")
        ward = attrs.get("ward")
        polling_unit = attrs.get("polling_unit")
        address = attrs.get("address")
        passport = attrs.get("passport")

        user = self.context["request"].user
        date_of_birth = user.profile.date_of_birth
        voter = Voter.objects.filter(user=user).order_by("-registration_date").first()

        if voter:
            if voter.voter_status == Voter.Status.PENDING:
                raise serializers.ValidationError("Your application is still pending.")

            if voter.voter_status == Voter.Status.APPROVED:
                raise serializers.ValidationError("You are already a registered voter.")

        today = date.today()
        print(attrs)
        print(attrs.get("date_of_birth"))

        age = (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )

        if age < 18:
            raise serializers.ValidationError(
                {"date_of_birth": "You must be up to 18 years old to apply"}
            )

        return attrs

        # def create(self, validated_data):
        #     pass


class GetElectionSerializer(serializers.ModelSerializer):
    positions = PositionNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Election
        fields = ["id", "title", "description", "election_type", "status", "positions"]


class VerifyVoterSerializer(serializers.Serializer):
    election = serializers.PrimaryKeyRelatedField(queryset=Election.objects.all())
    vin = serializers.CharField(max_length=20)


class ElectionBallotCandidateSerializer(serializers.ModelSerializer):
    position = ElectionPositionSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "user",
            "candidate_image",
            "party",
            "position",
        ]


class VotingHistorySerializer(serializers.ModelSerializer):
    votes_cast = serializers.SerializerMethodField()
    voted_at = serializers.SerializerMethodField()

    class Meta:
        model = Election
        fields = [
            "id",
            "title",
            "election_type",
            "status",
            "votes_cast",
            "voted_at",
        ]

    def get_votes_cast(self, obj):
        user = self.context["request"].user

        return Vote.objects.filter(voter=user, election=obj).count()

    def get_voted_at(self, obj):
        user = self.context["request"].user

        vote = (
            Vote.objects.filter(voter=user, election=obj).order_by("voted_at").first()
        )

        return vote.voted_at if vote else None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)

    class Meta:
        model = Profile
        fields = ["telephone_number", "address", "profile_image", "email"]

    def update(self, instance, validated_data):
        email = validated_data.pop("email", None)

        if email:
            instance.user.email = email
            instance.user.save()

        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError(
                {"password": "Current Password is incorrect"}
            )

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )

        if user.check_password(attrs["new_password"]):
            raise serializers.ValidationError(
                {
                    "new_password": "Your new password cannot be the same as your current password."
                }
            )

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"new_password": list(error.messages)})

        return attrs

    def save(self, **kwargs):

        user = self.context["request"].user

        user.set_password(self.validated_data["new_password"])
        user.save()

        return user


class AdminVoterSerializer(serializers.ModelSerializer):
    polling_unit = PollingUnitSerializer(read_only=True)

    class Meta:
        model = Voter
        fields = [
            "vin",
            "polling_unit",
            "voter_status",
            "registration_date",
            "passport",
        ]
        extra_kwargs = {
            "vin": {"read_only": True},
        }


class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "date_of_birth",
            "gender",
            "state_of_origin",
            "telephone_number",
            "profile_image",
            "address",
        ]
        extra_kwargs = {"user": {"read_only": True}}


class AdminUserSerializer(serializers.ModelSerializer):
    profile = AdminProfileSerializer(read_only=True)
    voter = AdminVoterSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "profile",
            "voter",
        ]


class AdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "password"]

    # WE USE DJANGO'S BUILT-IN PASSWORD VALIDATORS
    def validate_password(self, value):
        validate_password(value, self.instance)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password, role=User.RoleChoices.ADMIN, **validated_data
        )

        return user


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "user",
            "action",
            "description",
            "ip_address",
            "user_agent",
            "status",
            "created_at",
        ]


class ViewUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "role",
            "date_joined",
            "is_active",
        ]
        extra_kwargs = {"role": {"read_only": True}}


class UserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "username",
            "email",
            "is_active",
            "date_joined",
            "role",
        ]


class ViewVoterSerializer(serializers.ModelSerializer):
    polling_unit = PollingUnitSerializer(read_only=True)
    user = UserAccountSerializer(read_only=True)

    class Meta:
        model = Voter
        fields = [
            "id",
            "vin",
            "passport",
            "voter_status",
            "registration_date",
            "polling_unit",
            "user",
        ]
        extra_kwargs = {"vin": {"read_only": True}}


class ApproveDeclineVoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = ["voter_status"]


class AdminCandidateSerializer(serializers.ModelSerializer):
    user = ViewUserSerializer(read_only=True)
    party = PartySerializer(read_only=True)
    election = ElectionSerializer(read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "user",
            "party",
            "election",
            "candidate_image",
            "position",
            "is_active",
        ]


class PvcVerificationSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["vin", "details"])

    vin = serializers.CharField(required=False)

    state = serializers.IntegerField(required=False)
    lga = serializers.IntegerField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    def validate(self, attrs: Any) -> Any:
        method = attrs["method"]

        if method == "vin":
            if not attrs.get("vin"):
                raise serializers.ValidationError({"vin": "VIN is required."})
        elif method == "details":
            required_fields = [
                "state",
                "lga",
                "first_name",
                "last_name",
            ]

            missing = [field for field in required_fields if not attrs.get(field)]

            if missing:
                raise serializers.ValidationError(
                    {
                        field: f"{field.replace('_', ' ').title()} is required."
                        for field in missing
                    }
                )

        return attrs
