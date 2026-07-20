/-
Trusted checker for formal_conjectures submissions.

Run via `lake env lean --run CheckDriver.lean <module components> / <theorem
components>` from the formal-conjectures package root, with the compiled
submission (module `FCSolution`) on LEAN_PATH.

This file only ever loads compiled .oleans via `importModules` — it never
elaborates submission *syntax*, so submission-defined macros/elaborators can
never influence the check. It verifies:
  1. the submission declares a constant `solution`,
  2. `solution` depends only on the standard axioms, and
  3. `solution`'s type is definitionally equal to the target conjecture's
     statement (the statement constant exists in the target module even when
     its proof is `sorry`).

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

def check (targetName : Name) : CoreM (Except String Unit) := do
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

  -- Statement check: `solution`'s type must be defeq to the conjecture's.
  unless target.levelParams.length == sol.levelParams.length do
    return .error "universe parameter count differs from the conjecture statement"
  let solType := sol.type.instantiateLevelParams sol.levelParams
    (target.levelParams.map Level.param)
  let ok ← Meta.MetaM.run' (Meta.isDefEq target.type solType)
  unless ok do
    return .error
      s!"the type of `solution` does not match the statement of {targetName}"
  return .ok ()

def main (args : List String) : IO UInt32 := do
  let (modComponents, rest) := args.span (· != "/")
  let thmComponents := rest.drop 1
  if modComponents.isEmpty || thmComponents.isEmpty then
    return ← fail "usage: CheckDriver <module components> / <theorem components>"
  let targetMod := mkNameFromComponents modComponents
  let targetName := mkNameFromComponents thmComponents

  initSearchPath (← findSysroot)
  let env ← importModules #[{ module := targetMod }, { module := `FCSolution }] {}

  let coreCtx : Core.Context := { fileName := "", fileMap := default }
  let (result, _) ← (check targetName).toIO coreCtx { env := env }
  match result with
  | .error msg => return ← fail msg
  | .ok () =>
    IO.println "FC_CHECK_OK"
    return 0
