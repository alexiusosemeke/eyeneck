from turtle import position

from django.db.models import Count

from ..models import Vote


def calculate_election_results(election):
    results = (
        Vote.objects.filter(election=election)
        .values(
            "position", "candidate"
        )  # we group by position and candidate for more transparency
        .annotate(
            vote_count=Count("id")
        )  # then count the votes based on the groups above
        .order_by("-vote_count")  # and order the votes by the vote count above
    )

    results_per_position = []

    for result in results:
        position_id = result["position"]

        if position_id not in results_per_position:
            results_per_position[position_id] = []

        results_per_position[position_id].append(result)
    # then we get all the votes belonging to this election

    winner = max(candidates, key=lambda candidate: candidate["vote_count"])
