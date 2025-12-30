#include <iostream>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int Tid;
    std::cin >> Tid;

    // This solution implements a naive string search algorithm.
    // The A=B program works in phases.
    //
    // Phase 1: Setup (lowest priority rules)
    // The string s is converted to uppercase (A, B, C) to distinguish it from t.
    // This is done by rules like `aS=AS`, which are only active at the start
    // because after conversion, no lowercase letters are before S.
    //
    // Phase 2: Main Loop (higher priority rules)
    // The program repeatedly tries to match the prefix of the (remaining) uppercase string S'
    // with the target string t.
    //
    // Sub-phase 2a: Match
    // Rules like `ASa=S` check for a character match. If so, both matched characters
    // are consumed. This continues for the next characters.
    //
    // Sub-phase 2b: Advance on Mismatch
    // If no character-match rule applies, it implies a mismatch for the current starting position.
    // The program then "advances", which means discarding the first character of S'.
    // This is implemented by a state transition: `AS=X`, `BS=X`, `CS=X` start the process.
    // `X` then bubbles through the rest of S' (`XA=AX`, etc.) and restores the separator S (`XS=S`).
    // This effectively removes one character from the front of S', and the main loop restarts.
    //
    // Phase 3: Termination
    // - If t is consumed entirely (`S` is all that's left between S' and t), a match is found.
    //   `S=(return)1` handles this success case.
    // - If S' is consumed entirely before a match is found (`S` is at the beginning of the string),
    //   it means t is not a substring. `Sa=(return)0`, `Sb=(return)0`, `Sc=(return)0` handle this.

    // --- Termination: Success ---
    // If t is successfully matched and consumed, the string becomes a remnant of S'
    // followed by S, or just S. In this case, S becomes the leftmost match.
    std::cout << "S=(return)1\n";

    // --- Termination: Failure ---
    // If S' is exhausted, S will be at the beginning of the string, followed by
    // the remaining part of t. This signifies failure.
    std::cout << "Sa=(return)0\n";
    std::cout << "Sb=(return)0\n";
    std::cout << "Sc=(return)0\n";

    // --- Main Loop: Match one character ---
    // These rules have the highest priority among active search rules due to length.
    // They match and consume one character from S' and one from t.
    std::cout << "ASa=S\n";
    std::cout << "BSb=S\n";
    std::cout << "CSc=S\n";

    // --- Main Loop: Advance S' (on mismatch) ---
    // If no match rule applies, one of these will, starting the "advance" process.
    std::cout << "AS=X\n";
    std::cout << "BS=X\n";
    std::cout << "CS=X\n";

    // Helper rules to move the temporary marker X past the rest of S'.
    std::cout << "XA=AX\n";
    std::cout << "XB=BX\n";
    std::cout << "XC=CX\n";
    
    // Restore the separator S, completing the "advance" step.
    std::cout << "XS=S\n";

    // --- Setup Phase ---
    // These rules have the lowest priority and run only at the beginning.
    // They convert s (lowercase) to S' (uppercase).
    std::cout << "aS=AS\n";
    std::cout << "bS=BS\n";
    std::cout << "cS=CS\n";

    return 0;
}