/-
Validation sweep for prove-or-disprove problems (run via shape_check.sh).

Reads a file of lines "<module components> / <theorem components>" and checks,
in the prebuilt eval environment, that every target's compiled type has the
exact placeholder shape `True ↔ Q` required by CheckDriver.lean's
"prove_or_disprove" mode. Any target failing this would be a permanently-zero
problem (the driver fails closed) and must be excluded by the generator —
typically because the statement references section `variable`s, which prepend
∀ binders to the compiled type.

Prints one "BAD <reason>: <name>" line per failure and a final
"checked <n>, bad <m>" summary; exits non-zero iff any target is bad.
-/
import Lean
open Lean

def mkNameFromComponents (cs : List String) : Name :=
  cs.foldl .str .anonymous

def main (args : List String) : IO UInt32 := do
  initSearchPath (← findSysroot)
  let lines ← IO.FS.lines ⟨args.head!⟩
  let entries := lines.filterMap fun l =>
    if l.isEmpty then none
    else
      match l.splitOn " / " with
      | [m, t] => some (mkNameFromComponents (m.splitOn " "),
                        mkNameFromComponents (t.splitOn " "))
      | _ => none
  let mods := entries.map (fun e => ({ module := e.1 } : Import))
  let env ← importModules mods {}
  let mut bad := 0
  let mut total := 0
  for (_, name) in entries do
    total := total + 1
    match env.find? name with
    | none => IO.println s!"BAD missing: {name}"; bad := bad + 1
    | some ci =>
      if ci.type.hasSorry then
        IO.println s!"BAD hasSorry: {name}"; bad := bad + 1
      else if !ci.type.isAppOfArity `Iff 2 then
        IO.println s!"BAD not-iff: {name}"; bad := bad + 1
      else if !(ci.type.appFn!.appArg!.isConstOf `True) then
        IO.println s!"BAD lhs-not-True: {name}"; bad := bad + 1
  IO.println s!"checked {total}, bad {bad}"
  return if bad == 0 then 0 else 1
