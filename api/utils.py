from accounts.models import ActivityLog


# SINCE I AM ALREADY USING A ROLE BASED SYSTEM, THERE'D BE NO NEED TO CREATE A SEPARATE ACTIVITY TRACKER FOR ADMINS
def log_activity(user, action, status, request=None, description=""):
    ip_address = None
    user_agent = ""
    
    if request:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            # HTTP_X_FORWARDED_FOR can be a comma-separated list of IPs. 
            # The first one is the original client.
            ip_address = x_forwarded.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        
    ActivityLog.objects.create(
        user=user,
        action=action,
        status=status,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )