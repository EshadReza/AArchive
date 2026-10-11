# Central role and scope policy interface

Implemented in S007 against SRS Sections 9, 10, 18 and 48, D02/D04. Session
transport is implemented in [S008](authentication.md); domain policies arrive with
their modules and full component visibility is S019.

## Authorization entry points

`apps.access.policy` provides:

- `allows(actor, action, resource=None)` for services and workers.
- `require_permission(...)`, raising Django `PermissionDenied` on denial.
- `scope_queryset(actor, action, queryset, *, kind)` for filtering before
  pagination/counts/serialization, preserving existing queryset filters.
- `ResourceRef(ResourceKind, UUID_or_positive_integer)`: typed identity, without
  caller-supplied ownership, role, or visibility claims.
- `ResourcePolicy(model, selectors)` and `register_policy(kind, policy)`: trusted
  startup hooks mapping actions to functions returning database `Q` predicates.
  Duplicate registration is rejected; selector maps are copied and immutable.

Each authorization call refetches account eligibility and platform roles from
the database. Only saved platform Users qualify. Source-role dictionaries,
headers, Django staff/superuser attributes and cached role assignments grant
nothing. Unknown actions, missing policies, wrong model/kind combinations and
missing objects deny even Administrators. Anonymous calls currently deny; S019
adds explicit public-component policies and parent gates.

Current global gates: `users.manage`, `roles.manage`, `system.manage`, `audit.view`
(Administrator only), and `contest.create` (Administrator/Teacher). Global gates
do not authorize arbitrary objects. Every object check uses its registered model
selector and filters by identity, using the same predicate as list filtering.
There is no Administrator fallback around the adapter's integrity/privacy checks.

Adapters own current assignments, enrollment, publication, parent gates and
field/projection restrictions. They must use authoritative server data. The only
production adapter now registered is the Administrator audit read policy. Tests
register synthetic mark/offering adapters over fixture rows to verify the hooks;
these are not deployed academic models.

### REST and worker integration

`PolicyPermission` uses a view's fixed `policy_action` for global gates. Object
views must scope their querysets too; a DRF list permission does not filter rows.
For actions without a global gate, use scoped querysets and object checks rather
than inventing a role shortcut. Audit list/detail now use the central gate/filter.

```python
# In a future mark view, after its module registers the real policy:
def get_queryset(self):
    return scope_queryset(
        self.request.user, "marks.view", super().get_queryset(),
        kind=ResourceKind.MARK,
    )
```

Until registration, this example denies. Workers must reload the initiating User,
check the exact resource/projection at execution, and reauthorize downloads.
Never cache Principals, prefiltered querysets or permission booleans between jobs
or requests. These helpers do not replace business transactions and locks.

## Scoped grants

`ScopedGrant` stores UUID identity, protected subject, capability, typed scope UUID,
active flag and timestamps. Database constraints enforce the allowed pairs below
and uniqueness of `(subject, capability, scope_kind, scope_id)`.

| Capability | Scope | Additional adapter requirement |
|---|---|---|
| `marks.lock`, `marks.unlock` | Offering | Current offering assignment plus grant |
| `batch.view_reports` | Offering | Only that report projection; no individual marks |
| `access_groups.manage` | Access Group | Only the delegated group |
| `restricted.view` | Contest | Explicit resource/field scope and governance audit |

`granted_scope_ids(principal, capability, kind)` supplies candidate IDs to the
selector, using its fresh Principal. It requires Teacher and is not a final
permission decision: intersect assignments/privacy as appropriate. A second role
can confer legitimate staff rights; Student alone cannot use these capabilities.

Administrator-only actions and arbitrary capability names cannot be delegated.
The existing `/api/audit` remains Administrator-only. The SRS's optional delegated
own-action audit view has no grant key/route here; adding it later requires a
separate scoped policy without widening the existing global API.

Scope IDs have no polymorphic FK to future tables. Activation requires a registered
resource model and an existing UUID row. Authorization queries that actual resource.
Future modules must keep IDs stable, prevent reuse and revoke grants on retirement.
Revocation remains possible after the target disappears. Real offering/contest/group
grants cannot yet be activated because their models/adapters are not implemented.

## Audited privilege commands

Use `apps.access.services`, not direct role/grant model serializers:

```python
set_roles(actor=administrator, subject_id=user_id,
          roles=["STUDENT", "TEACHER"], reason="administrative_change")
set_grant(actor=administrator, subject_id=teacher_id,
          capability="marks.lock", scope=ResourceRef(ResourceKind.OFFERING, offering_id),
          active=True, reason="administrative_change")
```

These are internal service interfaces, not new HTTP endpoints. Each opens an
atomic transaction, locks the seeded `PrivilegeLock(pk=1)`, rechecks Administrator
authority, validates explicit fields, applies the change and writes its audit
record. Audit failures roll back the mutation; exact repeats are no-ops. Supported
nonempty reasons: `administrative_change`, `user_request`, `security_response`.
ANONYMIZED subjects reject changes. No source roles or credentials are accepted.

Roles must contain one to three distinct fixed values. Removing the last eligible
Administrator is rejected, including concurrent attempts. Removing Teacher also
deactivates and audits every active delegated grant in the same transaction;
restoring Teacher does not restore those grants. Regranting uses the retained row;
revocation sets `active=False`, preserving history. Activation requires Teacher.

The singleton serializes low-volume privilege edits to prevent authorization and
last-Administrator races. S010 lifecycle/recovery commands call
`lock_privilege_changes()` inside their transaction **before** locking Users or
resources, then enforce account invariants and revoke sessions as required.
See [lifecycle contract](recovery-lifecycle.md). Raw ORM writes remain trusted migration
and implementation tools and can bypass these service rules; never expose them to
importers or generic mass-assignment endpoints.

### First Administrator

An operator with trusted CLI/database access may run:

```sh
uv run --locked --env-file .env python backend/manage.py bootstrap_administrator \
  --email verified-operator@example.edu
```

The account must already exist, be verified/approved and be in an eligible state.
This command does not create accounts, set passwords, verify ownership or activate
pending accounts. It refuses if any Administrator assignment exists, even a
suspended one. It is not an account recovery shortcut or a web endpoint. The same
lock/transaction is used, with an `accounts.roles.changed` event attributed to the
controlled `bootstrap` system actor. S007 created no real account.

## Schema and later integrations

Apply migrations with the README command. `access.0001_initial` creates the grant
and lock tables; `0002_seed_privilege_lock` depends on audit and seeds the singleton
idempotently. Reversing only the seed intentionally retains the row; reapplication
does not duplicate it. Missing locks fail closed. Full reversal drops grant data;
use forward corrective migrations and backups once real grants exist.

`accounts.roles.changed` stores previous/new roles. `access.grant.changed` stores
subject UUID, capability, scope kind/UUID and GRANTED/REVOKED status, targeting the
grant UUID. UUID fields use canonical validators; unknown audit fields are still
excluded. No source identity or credential fields were added.

S011 exposes Administrator account/role commands through the
[account-management API](account-management.md), with expected-role conflict checks.
It reuses these services and the privilege lock; profile/invitation changes also
share that lock. No browser/source role claim bypasses current authorization.

S012 academic administration uses current `system.manage` for reads and writes.
Structure mutation and future assignment-context validation share the privilege lock;
see [academic structure](academic-structure.md). Teacher read projections for future
offering selection must be scoped explicitly rather than opening management APIs.

Integration owners: S008 sessions (implemented); S010 lifecycle locking (implemented); S011 accounts (implemented); S014/S016 assignments;
S018 groups; S019/S020 visibility; S041 provisioning; S053/S061 grading/privacy;
S070-S078 reports/exports; S085 endpoint inventory. Each must test its real adapter
and projection before enabling an action. See [S007 evidence](sprints/S007.md).
