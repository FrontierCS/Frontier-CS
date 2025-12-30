#include <iostream>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    // Phase 1: Setup.
    // The input string is sSt.
    // First, change S to Q and create a backup of t, separated by #.
    // The backup t will use alphabet {X, Y, Z}.
    std::cout << "S=Q#" << std::endl;
    std::cout << "#a=a#X" << std::endl;
    std::cout << "#b=b#Y" << std::endl;
    std::cout << "#c=c#Z" << std::endl;
    // After these, string is `s Q t # t_XYZ`.
    // Now, introduce a marker `P` at the very beginning of s.
    std::cout << "a=Da" << std::endl;
    std::cout << "b=Db" << std::endl;
    std::cout << "c=Dc" << std::endl;
    std::cout << "D=P" << std::endl;
    // Now string is `P s Q t # t_XYZ`. P is the sliding window pointer.

    // Phase 2: Main loop.
    // At each position of P, try to match.
    // Start match: P becomes M.
    std::cout << "P=M" << std::endl;
    // Matching rules:
    std::cout << "MaQa=M" << std::endl;
    std::cout << "MbQb=M" << std::endl;
    std::cout << "McQc=M" << std::endl;
    
    // Success: M has consumed all of t.
    std::cout << "MQ#=(return)1" << std::endl;
    
    // Mismatch rules:
    std::cout << "MaQb=F" << std::endl;
    std::cout << "MaQc=F" << std::endl;
    std::cout << "MbQa=F" << std::endl;
    std::cout << "MbQc=F" << std::endl;
    std::cout << "McQa=F" << std::endl;
    std::cout << "McQb=F" << std::endl;
    
    // Mismatch recovery:
    // F will clean up the partially consumed t and s, then restore t and advance P.
    // `s_done M s_rem_match F s_rem_rest Q t_rem # t_XYZ`
    std::cout << "aF=Fa" << std::endl;
    std::cout << "bF=Fb" << std::endl;
    std::cout << "cF=Fc" << std::endl;
    std::cout << "MF=FM" << std::endl; // Move F past the original M position.
    
    // Once F is at the beginning of where s_rem was:
    // `s_done F M s_rem ...` -> advance `P`'s logical position.
    // `FM=P`. This effectively removes one char from s and restarts search.
    std::cout << "FM=P" << std::endl;
    
    // Reset `t`. When `P` is set, `t` needs to be restored.
    std::cout << "PaQ=PaR" << std::endl;
    std::cout << "PbQ=PbR" << std::endl;
    std::cout << "PcQ=PcR" << std::endl;
    std::cout << "P#=P_R" << std::endl; // Also for case when t is empty
    
    // R (restore) state.
    std::cout << "Ra=R" << std::endl;
    std::cout << "Rb=R" << std::endl;
    std::cout << "Rc=R" << std::endl;
    std::cout << "R#=T" << std::endl;
    
    // T copies from backup.
    std::cout << "TX=aT" << std::endl;
    std::cout << "TY=bT" << std::endl;
    std::cout << "TZ=cT" << std::endl;
    
    // When T is done, it becomes Q again.
    // Need to handle end of backup string.
    std::cout << "aT=aQ" << std::endl;
    std::cout << "bT=bQ" << std::endl;
    std::cout << "cT=cQ" << std::endl;
    std::cout << "T=Q" << std::endl;
    
    // Termination: P has scanned the entire string s.
    std::cout << "PQ=(return)0" << std::endl;
    return 0;
}