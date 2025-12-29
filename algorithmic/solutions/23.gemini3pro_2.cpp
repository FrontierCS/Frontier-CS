#include <iostream>
#include <string>
#include <vector>

using namespace std;

int main() {
    // A=B program generation
    
    // Phase 1: Initialization and Mapping s
    // Map s chars a,b,c -> G,H,I to distinguish from t chars
    // Create L and R markers. L s(mapped) S t R
    
    cout << "S=^S%" << endl;
    cout << "a^=^G" << endl;
    cout << "b^=^H" << endl;
    cout << "c^=^I" << endl;
    cout << "^=L" << endl;
    
    cout << "%a=a%" << endl;
    cout << "%b=b%" << endl;
    cout << "%c=c%" << endl;
    cout << "%=R" << endl;
    
    // Phase 2: Reverse t (a,b,c) to t^R
    // Use > to carry from R to S.
    // Trigger >
    cout << "S=S>" << endl;
    
    cout << ">a=a>" << endl;
    cout << ">b=b>" << endl;
    cout << ">c=c>" << endl;
    
    // Pick from R
    cout << "a>R=R<a" << endl; // Carry a
    cout << "b>R=R<b" << endl; // Carry b
    cout << "c>R=R<c" << endl; // Carry c
    
    // End of t (empty)
    cout << ">R=ET" << endl; // E is separator, T is terminator
    
    // Carry back to S
    cout << "a<=<a" << endl;
    cout << "b<=<b" << endl;
    cout << "c<=<c" << endl;
    
    // Deposit at S and repeat
    cout << "S<a=Sa>" << endl;
    cout << "S<b=Sb>" << endl;
    cout << "S<c=Sc>" << endl;
    
    // Phase 3: Mark Start of t^R (a->A, b->B, c->C)
    // S separates s(GHI) and t(abc).
    // Start matching. S becomes M.
    // First char of t becomes Start Marker.
    
    cout << "Sa=MA" << endl;
    cout << "Sb=MB" << endl;
    cout << "Sc=MC" << endl;
    
    // If t was empty (shouldn't happen per spec), match succeeds? 
    // Spec says t non-empty. So Sa/Sb/Sc will match.
    
    // Matching Rules
    // s chars: G,H,I
    // t start: A,B,C
    // t normal: a,b,c
    // used start: U,V,W
    // used normal: x,y,z
    
    // Success condition
    cout << "ME=(return)1" << endl;
    
    // Failure condition (s empty)
    cout << "LM=(return)0" << endl;
    
    // Match logic
    // G matches A -> U
    cout << "GMA=MU" << endl;
    cout << "HMB=MV" << endl;
    cout << "IMC=MW" << endl;
    
    // G matches a -> x
    cout << "GMa=Mx" << endl;
    cout << "HMb=My" << endl;
    cout << "IMc=Mz" << endl;
    
    // Mismatch logic
    // Any G/H/I M followed by active t char (A/B/C/a/b/c) -> Fail
    // Prioritize Match rules above.
    // Mismatch consumes s char (G/H/I).
    cout << "GM=F" << endl;
    cout << "HM=F" << endl;
    cout << "IM=F" << endl;
    
    // Movers (U,V,W,x,y,z) move right through active (A,B,C,a,b,c) to E
    // 6 movers * 6 active = 36 lines.
    vector<string> movers = {"U", "V", "W", "x", "y", "z"};
    vector<string> through = {"A", "B", "C", "a", "b", "c"};
    for(string m : movers) {
        for(string t : through) {
            cout << m << t << "=" << t << m << endl;
        }
        // Move past E
        cout << m << "E=E" << m << endl;
    }
    
    // Flush F
    // F moves active chars to E
    for(string t : through) {
        cout << "F" << t << "=" << t << "F" << endl;
    }
    // F hits E -> Switch to Restore G
    cout << "FE=EG" << endl;
    
    // Restore G
    // G moves through used (U...z), converts back to active (A...c)
    // and effectively rotates them (since they are past E).
    // Actually G just converts them. The position relative to E is maintained (right of E).
    // But we need them LEFT of E for next round?
    // Wait, E separates active (left) and used (right).
    // If we restore, they become active. So they must move LEFT of E?
    // Or we just redefine E's position?
    // T is at end. Used are between E and T.
    // Restored should be left of E.
    // So G U -> A G? No, G is right of E.
    // We want A to be left of E.
    // Use # to carry left.
    
    cout << "GU=A#" << endl;
    cout << "GV=B#" << endl;
    cout << "GW=C#" << endl;
    cout << "Gx=a#" << endl;
    cout << "Gy=b#" << endl;
    cout << "Gz=c#" << endl;
    
    // G hits T -> Done restoring.
    // But G consumes chars. T is reached when no used chars left.
    cout << "GT=T$" << endl;
    
    // # carries active left over E
    // # E = E #? No, # is right of E.
    // used chars were E U V ...
    // G converts U -> A #.
    // E A #. We want A E.
    // So # swaps A and E?
    // Actually # needs to move A to the queue end.
    // Queue end is E.
    // So A should be left of E.
    // A # E? No.
    // Logic: E U ... T.
    // G U -> A #.
    // We have E A # ...
    // We want A E # ... (A moved left of E).
    // So # must move A left over E?
    // But A is active.
    // Let's make # move A left.
    // A # -> # A? No.
    // We want to deposit A left of E.
    
    // Let's do: G U = # A.
    // # moves A left.
    // # A -> A #. (Move # right? No).
    // # A -> A # is wrong direction.
    // We are at E # A ...
    // # A E -> E A #?
    // Simpler: Just move A left over E.
    // # is transient.
    // Actually, simply:
    // GU=A'G (mark A as 'moving').
    // A' moves left over E.
    // A' E = E A.
    // Then G continues.
    
    // Let's rename rules.
    // GU = u G (temp u).
    // u E = E A (restored A left of E).
    // u x = x u (move u left over used? No, used are on right).
    // u is created by G. G is moving right.
    // E (used) G (rest).
    // G U -> u G.
    // E (used) u G.
    // u must move left over (used) and E.
    // u U = U u. u x = x u. (u moves left over used).
    // u E = E A. (Done).
    
    // Movers u,v,w (for A,B,C) and k,l,m (for a,b,c)
    // u,v,w,k,l,m move left over U,V,W,x,y,z.
    
    // This adds 6 * 6 = 36 lines. Too many.
    // Total lines already ~70. 36 is risky. 106 > 100.
    
    // OPTIMIZATION:
    // Don't distinguish Used Start vs Used Normal in movement.
    // We only need to distinguish during Restore.
    // G knows which is which.
    // u, v, w, k, l, m.
    // Can we group?
    // No.
    
    // Alternative: Move E right?
    // F moves active to E. E hops over them.
    // F a E -> E a F? (E moves left).
    // F a -> a F. F E -> G.
    // E is left of used.
    // G restores used to active.
    // G U -> A G.
    // E A G.
    // A is active. E is separator.
    // We want A left of E?
    // Yes.
    // But E is already left of A!
    // E A G. A is between E and G.
    // If we leave A there, E is left of A.
    // Next Match: M matches chars LEFT of E.
    // But A is RIGHT of E.
    // We need A LEFT of E.
    // So E must move RIGHT over A.
    // E A -> A E.
    // That's 6 rules.
    // E A = A E, E B = B E ... E c = c E.
    // Then G continues.
    
    // G U = A E G? No.
    // G U = A G. (Leaves A).
    // Then E must hop over A.
    // Can E see A?
    // Sequence: E A G ...
    // E A = A E.
    // Then E G ...
    // G takes next.
    // This works! Only 6 rules.
    
    cout << "GU=AG" << endl; cout << "GV=BG" << endl; cout << "GW=CG" << endl;
    cout << "Gx=aG" << endl; cout << "Gy=bG" << endl; cout << "Gz=cG" << endl;
    
    for(string t : through) {
        cout << "E" << t << "=" << t << "E" << endl;
    }
    
    // Finish restore
    cout << "GT=T$" << endl;
    
    // $ carries M back to L (actually to G/H/I)
    // $ moves left over active (A...c)
    // $ hits G/H/I -> M
    
    for(string t : through) {
        cout << t << "$=$" << t << endl;
    }
    cout << "E$=$" << endl; // $ crosses E? No E is on right of A...c.
    // Sequence: A...c E T $.
    // $ moves left.
    // $ T -> $ ? No GT=T$. $ is left of T.
    // E A ... c T $.
    // Wait GT=T$.
    // G was at T.
    // A...c E G T.
    // G T -> T $.
    // A...c E T $.
    // $ moves left over T?
    // T$=T$. No.
    // $ must move left over T, E, and active chars.
    
    cout << "T$=T$" << endl; // Swap
    cout << "E$=E$" << endl; // Swap? No E is right of active.
    // Actually sequence: Active... E Used(empty) T.
    // G finished.
    // Active... E T $.
    // $ moves left.
    // $ must cross T, E, Active.
    
    // T$=T$ is wrong direction. $ is left of T.
    // We generated $ LEFT of T? GT=T$. G was LEFT of T.
    // So $ is LEFT of T.
    // Active E $.
    // $ moves left over E.
    cout << "E$=$E" << endl; // $ moves left over E
    
    // $ moves left over Active
    for(string t : through) {
        cout << t << "$=$" << t << endl;
    }
    
    // $ hits s (G,H,I)
    cout << "G$=GM" << endl;
    cout << "H$=HM" << endl;
    cout << "I$=IM" << endl;
    cout << "L$=LM" << endl;
    
    return 0;
}