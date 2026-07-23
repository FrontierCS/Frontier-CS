/-
Trusted checker for formal_conjectures submissions.

Run via `lake env lean --run CheckDriver.lean <module components> / <theorem
components> [/ <mode>]` from the formal-conjectures package root, with the
compiled submission (module `FCSolution`) on LEAN_PATH.

This file only ever loads compiled .oleans via `importModules` — it never
elaborates submission *syntax*, so submission-defined macros/elaborators can
never influence the check. It verifies:
  1. the submission declares a constant `solution`,
  2. `solution` depends only on the standard axioms, and
  3. `solution`'s type matches the target, depending on <mode>:
     - "prove" (default): definitionally equal to the target conjecture's
       statement (the statement constant exists in the target module even
       when its proof is `sorry`);
     - "prove_or_disprove": the target is a fill-in-the-answer statement
       whose `answer(sorry)` elaborated to a `True` placeholder, so its
       compiled type must be literally `True ↔ Q`; the submission is accepted
       iff `solution`'s type is definitionally equal to `Q` or to `¬Q`.

Fail-closed: any shape the checker cannot positively verify (unexpected mode,
target not of the form `True ↔ Q`, type matching neither side) is an error,
which the evaluator scores 0.0.

Prints FC_CHECK_OK and exits 0 iff the submission is accepted.
-/
import Lean

open Lean

def allowedAxioms : List Name := [`propext, `Classical.choice, `Quot.sound]

def mkNameFromComponents (cs : List String) : Name :=
  cs.foldl .str .anonymous

def fail (msg : String) : IO UInt32 := do
  IO.eprintln s!"[driver] {msg}"
  return 1

def check (targetName : Name) (mode : String) : CoreM (Except String Unit) := do
  let env ← getEnv
  let some target := env.find? targetName
    | return .error s!"target theorem {targetName} not found"
  let some sol := env.find? `solution
    | return .error "submission must declare a top-level `theorem solution : <statement>`"
  if target.type.hasSorry then
    return .error s!"target statement {targetName} contains sorry; problem is not checkable"

  -- Axiom audit: catches sorryAx, native_decide (ofReduceBool), custom axioms.
  let axioms ← collectAxioms `solution
  for ax in axioms do
    unless allowedAxioms.contains ax do
      return .error s!"solution depends on forbidden axiom: {ax}"

  unless target.levelParams.length == sol.levelParams.length do
    return .error "universe parameter count differs from the conjecture statement"
  let solType := sol.type.instantiateLevelParams sol.levelParams
    (target.levelParams.map Level.param)

  match mode with
  | "prove" =>
    -- `solution`'s type must be defeq to the conjecture's statement.
    let ok ← Meta.MetaM.run' (Meta.isDefEq target.type solType)
    unless ok do
      return .error
        s!"the type of `solution` does not match the statement of {targetName}"
    return .ok ()
  | "prove_or_disprove" =>
    -- Target must have the exact placeholder shape `True ↔ Q` (no reduction:
    -- anything else fails closed). Accept a proof of `Q` or of `¬Q`.
    unless target.type.isAppOfArity `Iff 2 do
      return .error s!"target {targetName} is not a top-level iff; not checkable"
    let lhs := target.type.appFn!.appArg!
    let q := target.type.appArg!
    unless lhs.isConstOf `True do
      return .error s!"target {targetName} placeholder is not `True`; not checkable"
    if ← Meta.MetaM.run' (Meta.isDefEq q solType) then
      return .ok ()
    if ← Meta.MetaM.run' (Meta.isDefEq (mkApp (mkConst `Not) q) solType) then
      return .ok ()
    return .error
      s!"the type of `solution` proves neither the question of {targetName} nor its negation"
  | _ => return .error s!"unknown check mode: {mode}"

def main (args : List String) : IO UInt32 := do
  let (modComponents, rest) := args.span (· != "/")
  let (thmComponents, rest2) := (rest.drop 1).span (· != "/")
  let mode := (rest2.drop 1).headD "prove"
  if modComponents.isEmpty || thmComponents.isEmpty then
    return ← fail "usage: CheckDriver <module components> / <theorem components> [/ <mode>]"
  let targetMod := mkNameFromComponents modComponents
  let targetName := mkNameFromComponents thmComponents

  initSearchPath (← findSysroot)
  let env ← importModules #[{ module := targetMod }, { module := `FCSolution }] {}

  let coreCtx : Core.Context := { fileName := "", fileMap := default }
  let (result, _) ← (check targetName mode).toIO coreCtx { env := env }
  match result with
  | .error msg => return ← fail msg
  | .ok () =>
    IO.println "FC_CHECK_OK"
    return 0
