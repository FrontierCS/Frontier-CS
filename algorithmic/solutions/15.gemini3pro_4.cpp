#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

struct Op {
    int x, y;
};

void apply_op(vector<int>& p, int x, int y) {
    int n = p.size();
    vector<int> prefix(p.begin(), p.begin() + x);
    vector<int> middle(p.begin() + x, p.end() - y);
    vector<int> suffix(p.end() - y, p.end());
    
    p.clear();
    p.insert(p.end(), suffix.begin(), suffix.end());
    p.insert(p.end(), middle.begin(), middle.end());
    p.insert(p.end(), prefix.begin(), prefix.end());
}

int main() {
    int n;
    if (!(cin >> n)) return 0;
    
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }
    
    vector<Op> ops;
    
    // Step 1: Normalize 1 to index 0
    int k = -1;
    for (int i = 0; i < n; ++i) {
        if (p[i] == 1) {
            k = i;
            break;
        }
    }
    
    if (k != 0) {
        if (k == n - 1) {
            // 1 is at end
            if (n >= 3) {
                // p[0...n-3] | p[n-2] | 1
                ops.push_back({n - 2, 1});
                apply_op(p, n - 2, 1);
            }
        } else {
            // 1 is at k
            // P = 0...k-1, M = k, S = k+1...n-1
            if (k >= 1) { // k is index, so length of P is k
                // Wait, P length must be > 0. If k=0, P empty. But k != 0 here.
                // We want to bring S starting at k to front.
                // If we do P(k) | M(1) | S(n-k-1) -> S M P.
                // 1 is at start of M? No, 1 is at k. M is just 1.
                // Result S (1) P. 1 is in middle.
                // We want 1 at start.
                // We need 1 to be in S.
                // So S starts at k. S = k...n-1.
                // P needs to be non-empty. k >= 1.
                // M needs to be non-empty.
                // If k=1: 1 is at 1. P=[p0]. S=[1...]. M must be from P? No.
                // P must be before S.
                // If k=1, we have p0, 1, ...
                // S = 1...n-1. P=p0. M? Empty.
                // So cannot split if k=1 directly to S.
                // If k >= 2: P=0...k-2. M=k-1. S=k...n-1.
                // P | M | S -> S M P.
                // S starts with 1. So 1 at 0.
                if (k >= 2) {
                    ops.push_back({k - 1, n - k});
                    apply_op(p, k - 1, n - k);
                } else {
                    // k=1. 1 is at index 1.
                    // Move 1 to end first?
                    // P=0, M=1, S=2..n-1
                    // P | M | S -> S M P.
                    // Result S 1 P.
                    // 1 is at index n-2.
                    // Now use "at end" logic or general logic.
                    // 1 is at n-2. n >= 3.
                    // k becomes n-2. Since n-2 >= 1 (n>=3).
                    // If n=3, k=1. p0 1 p2.
                    // P=p0, M=1, S=p2. -> p2 1 p0.
                    // 1 is at 1.
                    // Just accept 1 at pos 1 for a moment? No.
                    // Use special 2-step for k=1.
                    // P=0, M=1..n-2, S=n-1.
                    // P | M | S -> S M P.
                    // p[n-1] M p0. 1 is inside M (at 0 relative to M).
                    // 1 is at index 1.
                    // This shifts array right.
                    // Let's use the 'k=n-1' logic which moves end to front.
                    // Move 1 to end: P=0, M=1, S=2..n-1.
                    // S 1 P. 1 is at n-1.
                    // Now k=n-1. Use k=n-1 logic.
                    if (n > 2) {
                        int lenS = n - 2;
                        ops.push_back({1, lenS});
                        apply_op(p, 1, lenS);
                        // Now 1 is at n-1.
                        // Apply k=n-1 logic:
                        ops.push_back({n - 2, 1});
                        apply_op(p, n - 2, 1);
                    }
                }
            }
        }
    }
    
    // Step 2: Place 2...n-1
    for (int i = 1; i < n - 1; ++i) {
        int v = i + 1;
        int k = -1;
        for (int j = 0; j < n; ++j) {
            if (p[j] == v) {
                k = j;
                break;
            }
        }
        
        if (k == i) continue; // Already in place
        
        if (k == n - 1) {
            if (i <= n - 3) {
                // Use the special 'at end' logic
                // 1. Move a, v to front (a is p[n-2])
                ops.push_back({i, 2});
                apply_op(p, i, 2);
                // 2. Fix order
                ops.push_back({1, i});
                apply_op(p, 1, i);
            } else {
                // i = n-2. v = n-1.
                // We have 1...n-2 at start. n-1 is at end.
                // So array is 1...n-2, n, n-1.
                // Try to swap last two.
                // P=1..n-2. M=n. S=n-1.
                // P | M | S -> S M P -> n-1 n P.
                // Rotate P to front.
                // S=P. Pre=n-1 n. P'=n-1 M'=n.
                // n-1 | n | P -> P n n-1.
                // Cycle. Just stop.
                break; 
            }
        } else {
            // Generic case: v is at k, i < k < n-1.
            // P = 0...i-1 (len i). M = i...k-1? No.
            // P is sorted block 1...i.
            // We need to cut after P.
            // Cut before v.
            // Cut after v.
            // P (0 to i-1).
            // v is at k.
            // S (k+1 to n-1).
            // M (i to k). v is at start of M? No.
            // If we define P=0..i-1.
            // We want v (at k) to be adjacent to P.
            // Op 1: P | M | S -> S M P
            // We define S such that v is start of S?
            // S = k...n-1.
            // M = i...k-1.
            // P = 0...i-1.
            // P | M | S -> S M P.
            // Result: S M P.
            // S starts with v. So v is at 0.
            // P is at end.
            int lenP = i;
            int lenM = k - i;
            int lenS = n - k;
            
            ops.push_back({lenP, lenS});
            apply_op(p, lenP, lenS);
            
            // Op 2: S starts with v.
            // We want P v M.
            // Currently S M P.
            // S = v S'.
            // Pre = S. Mid = M? No.
            // We want to swap S and P? No.
            // We want P at start.
            // Currently P is suffix.
            // S is prefix.
            // S = v + RestS.
            // P is sorted.
            // We want P + v + ...
            // Use Op: Pre=S, Mid=M, Suff=P -> P M S? No.
            // We want P v ...
            // S starts with v.
            // Try: Pre=S, Mid=M, Suff=P.
            // S | M | P -> P M S.
            // P is at start. M is next. S is end.
            // v is at start of S.
            // So P M v ...
            // v is separated from P by M.
            // This happens if M is not empty.
            // M was part between P and v.
            // We failed to jump v over M.
            
            // CORRECT GENERIC LOGIC:
            // v is at k.
            // Swap M and v?
            // S = k+1..n-1.
            // P = 0..i-1.
            // M = i..k-1. v is at k.
            // We want v next to P.
            // Use logic: P M v S -> P v M S.
            // We need to swap adjacent blocks M and v.
            // To swap M and v using P as anchor:
            // 1. P M v S -> v S M P. (x=len(P)+len(M), y=len(S)+1? No).
            // Use the rotation swap:
            // Move P to end: P | M v | S -> S M v P?
            // No.
            // Just use the logic derived:
            // 1. P | M | v S -> v S M P. (S_new = v S).
            //    x = i, y = n - k.
            //    State: v S M P.
            // 2. v | S M | P -> P S M v.
            //    x = 1, y = i.
            //    State: P S M v.
            //    v is at end.
            //    P is at start.
            //    S M is in middle.
            //    v is NOT next to P.
            
            // Let's use the code logic that definitely worked for "at end" case but adapted.
            // Actually, if we use the simple 2-step:
            // 1. P | M | v S -> v S M P.
            // 2. v S | M | P -> P M v S. (Undo).
            
            // We need to eliminate M.
            // Maybe we just take v and put it at end, then rotate?
            // If v is at k.
            // P | M | v S -> v S M P.
            // Now v is at 0.
            // Then rotate P to front?
            // v S M P.
            // We want P v ...
            // S_new = P.
            // Pre = v S M.
            // Split Pre: v | S M.
            // v | S M | P -> P S M v.
            // P at start. v at end.
            
            // Okay, use the verified 2-step from thought process:
            // "Insert into wrapping sorted block"
            // Start: P M v S.
            // 1. P | M | v S -> v S M P.
            //    x = len(P) + len(M). (i + k - i = k).
            //    y = len(v S) = n - k.
            //    Actually need P, M, S non empty.
            //    If M is empty (v adjacent to P), done. (Handled by k==i).
            //    If S is empty (v at end), handled by "at end" logic.
            //    So M, S non-empty. P non-empty (i>=1).
            //    Op: x=k, y=n-k.
            //    State: v S M P.
            // 2. v | S M | P -> P S M v.
            //    This moves v to end. P to start.
            //    Effectively P...v wrapping.
            //    This builds 1...i, i+1 wrapping.
            //    Next iteration handles wrapping?
            //    Loop assumes P is at 0.
            //    If P is at 0, and v is at end (n-1).
            //    Then next iteration k=n-1 logic handles it!
            //    So we intentionally move v to end!
            
            ops.push_back({k, n - k});
            apply_op(p, k, n - k);
            
            ops.push_back({1, i});
            apply_op(p, 1, i);
            
            // Now v is at n-1.
            // P is at 0...i-1.
            // Correct.
            // Next loop will see v (next val) somewhere.
            // If next val was in S or M, it shifted.
        }
    }

    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.x << " " << op.y << endl;
    }
    
    return 0;
}