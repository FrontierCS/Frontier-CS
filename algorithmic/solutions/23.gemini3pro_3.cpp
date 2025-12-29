#include <iostream>

int main() {
    // A=B solution
    // Alphabet:
    // s (original): a, b, c
    // T1 (first T): A, B, C
    // T2 (rest T): D, E, F
    // Matched T1: G, H, I
    // Matched T2: J, K, L
    // Matched s (first): 1, 2, 3
    // Matched s (rest): 4, 5, 6
    // Fail signal: @
    // End marker: #
    // Separator: S

    // 1. Initialization: Turn S into # and convert t to T2 (D, E, F)
    std::cout << "Sa=DS\n";
    std::cout << "Sb=ES\n";
    std::cout << "Sc=FS\n";
    std::cout << "S=#\n";

    // 2. Success Check: If # sees Matched s, it means success
    std::cout << "1#=(return)1\n";
    std::cout << "2#=(return)1\n";
    std::cout << "3#=(return)1\n";
    std::cout << "4#=(return)1\n";
    std::cout << "5#=(return)1\n";
    std::cout << "6#=(return)1\n";
    
    // Also if single char match at end
    // (Handled by match rules + success check)

    // 3. Convert first T2 to T1 at boundary with s
    // s chars: a,b,c. T2 chars: D,E,F.
    std::cout << "aD=aA\n";
    std::cout << "bD=bA\n";
    std::cout << "cD=cA\n";
    std::cout << "aE=aB\n";
    std::cout << "bE=bB\n";
    std::cout << "cE=cB\n";
    std::cout << "aF=aC\n";
    std::cout << "bF=bC\n";
    std::cout << "cF=cC\n";

    // 4. Bubble s left through T (T s = s T)
    // T chars: A-F. s chars: a-c.
    // A
    std::cout << "Aa=aA\n"; std::cout << "Ab=bA\n"; std::cout << "Ac=cA\n";
    // B
    std::cout << "Ba=aB\n"; std::cout << "Bb=bB\n"; std::cout << "Bc=cB\n";
    // C
    std::cout << "Ca=aC\n"; std::cout << "Cb=bC\n"; std::cout << "Cc=cC\n";
    // D
    std::cout << "Da=aD\n"; std::cout << "Db=bD\n"; std::cout << "Dc=cD\n";
    // E
    std::cout << "Ea=aE\n"; std::cout << "Eb=bE\n"; std::cout << "Ec=cE\n";
    // F
    std::cout << "Fa=aF\n"; std::cout << "Fb=bF\n"; std::cout << "Fc=cF\n";

    // 5. Matches
    // T1 matches s -> G-I, 1-3
    std::cout << "aA=G1\n";
    std::cout << "bB=H2\n";
    std::cout << "cC=I3\n";
    
    // T2 matches s -> J-L, 4-6
    std::cout << "aD=J4\n";
    std::cout << "bE=K5\n";
    std::cout << "cF=L6\n";

    // 6. Mismatches T1 (Delete s)
    std::cout << "aA=A\n"; std::cout << "bA=A\n"; std::cout << "cA=A\n";
    std::cout << "aB=B\n"; std::cout << "bB=B\n"; std::cout << "cB=B\n";
    std::cout << "aC=C\n"; std::cout << "bC=C\n"; std::cout << "cC=C\n";

    // 7. Mismatches T2 (Generate Fail Signal @)
    std::cout << "aD=@aD\n"; std::cout << "bD=@bD\n"; std::cout << "cD=@cD\n";
    std::cout << "aE=@aE\n"; std::cout << "bE=@bE\n"; std::cout << "cE=@cE\n";
    std::cout << "aF=@aF\n"; std::cout << "bF=@bF\n"; std::cout << "cF=@cF\n";

    // 8. Fail Propagation and Restore
    // Move @ left through s
    std::cout << "a@=@a\n"; std::cout << "b@=@b\n"; std::cout << "c@=@c\n";
    // Move @ left through Unchecked T
    std::cout << "A@=@A\n"; std::cout << "B@=@B\n"; std::cout << "C@=@C\n";
    std::cout << "D@=@D\n"; std::cout << "E@=@E\n"; std::cout << "F@=@F\n";
    
    // Restore Matched s rest (4,5,6 -> a,b,c) and Matched T2 (J,K,L -> D,E,F)
    // Actually we need to restore T char.
    // J corresponds to D. K to E. L to F.
    // 4 to a. 5 to b. 6 to c.
    std::cout << "4@=@a\n"; std::cout << "5@=@b\n"; std::cout << "6@=@c\n";
    std::cout << "J@=@D\n"; std::cout << "K@=@E\n"; std::cout << "L@=@F\n";
    
    // Restore Matched s first (1,2,3 -> delete) and Matched T1 (G,H,I -> A,B,C)
    // 1@ -> @. 
    std::cout << "1@=@\n"; std::cout << "2@=@\n"; std::cout << "3@=@\n";
    std::cout << "G@=A\n"; std::cout << "H@=B\n"; std::cout << "I@=C\n";

    // End of Fail: @ hits nothing? No, @ consumes markers.
    // Order matters: 1@=@ should run, then G@=A.
    // Once G becomes A, @ is gone.
    
    // 9. Failure conditions
    // If # reached with no match
    std::cout << "A#=(return)0\n";
    std::cout << "B#=(return)0\n";
    std::cout << "C#=(return)0\n";
    // If we run out of s?
    // S was replaced by #.
    // But # marks end of T.
    // If s is empty, T1 will see #? 
    // No, # is after T. 
    // G 1 # returns 1.
    // A # returns 0.
    
    // Catch-all
    std::cout << "=(return)0\n";
    
    return 0;
}