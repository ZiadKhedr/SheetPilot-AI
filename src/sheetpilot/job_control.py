from .store import Problem


class StopJob(Problem):
    """Cooperative interruption at a boundary before/after an actual safe step."""
    def __init__(self,state,message):
        super().__init__(message,409)
        self.state=state
