from rest_framework.permissions import BasePermission

from .models import User


class IsUserAdmin(BasePermission):
    message = "You are not permitted to access this resource."

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.role == User.RoleChoices.ADMIN
        )
