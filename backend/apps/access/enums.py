from django.db import models


class ResourceKind(models.TextChoices):
    ACCOUNT = "account", "Account"
    AUDIT = "audit", "Audit"
    OFFERING = "offering", "Offering"
    CONTEST = "contest", "Contest"
    MARK = "mark", "Mark"
    ACCESS_GROUP = "access_group", "Access group"


class Capability(models.TextChoices):
    MARKS_LOCK = "marks.lock", "Lock marks"
    MARKS_UNLOCK = "marks.unlock", "Unlock marks"
    BATCH_REPORTS = "batch.view_reports", "Read delegated batch report projection"
    GROUP_MANAGE = "access_groups.manage", "Manage delegated access group"
    RESTRICTED_VIEW = "restricted.view", "Read scoped restricted evidence"


CAPABILITY_SCOPES = {
    Capability.MARKS_LOCK: ResourceKind.OFFERING,
    Capability.MARKS_UNLOCK: ResourceKind.OFFERING,
    Capability.BATCH_REPORTS: ResourceKind.OFFERING,
    Capability.GROUP_MANAGE: ResourceKind.ACCESS_GROUP,
    Capability.RESTRICTED_VIEW: ResourceKind.CONTEST,
}
