from rest_framework.permissions import BasePermission
from accounts.models import User
from voting.models import Voter

class IsApprovedVoter(BasePermission):
    message = "You are not an approved voter."

    def has_permission(self, request, view):
        return request.user.voter.voter_status == Voter.Status.APPROVED
    
class IsUserCandidate(BasePermission):
    message = "You are not a candidate for this election"
    def has_permission(self, request, view):
        return request.user.role == User.RoleChoices.CANDIDATE