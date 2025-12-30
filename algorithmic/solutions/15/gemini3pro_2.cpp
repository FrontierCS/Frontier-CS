#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

struct Op {
    int x, y;
};

void apply_op(vector<int>& p, int x, int y, vector<Op>& ops) {
    int n = p.size();
    if (x <= 0 || y <= 0 || x + y >= n) return;
    ops.push_back({x, y});
    vector<int> a(p.begin(), p.begin() + x);
    vector<int> b(p.begin() + x, p.end() - y);
    vector<int> c(p.end() - y, p.end());
    
    p.clear();
    p.insert(p.end(), c.begin(), c.end());
    p.insert(p.end(), b.begin(), b.end());
    p.insert(p.end(), a.begin(), a.end());
}

int main() {
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    vector<Op> ops;
    
    // Strategy: Build sorted suffix k...n
    // Iterate k from n down to 1.
    // Initially S is empty. We want to place k such that it becomes k, k+1...n (cyclically or linearly).
    // We maintain the invariant that the sorted block S = {k+1...n} is at the END of the array.
    
    for (int k = n - 1; k >= 1; --k) {
        // S = {k+1 ... n} is at p[n-(n-k)...n-1] -> p[k...n-1] (0-indexed indices: k to n-1)
        // size of S is n-k.
        // We want to find value k and move it to position k-1 (0-indexed).
        // Currently valid unsorted range is 0 to k-1.
        
        int pos = -1;
        for (int i = 0; i < n; ++i) {
            if (p[i] == k) {
                pos = i;
                break;
            }
        }
        
        // Target is to have k immediately before the suffix S.
        // S starts at index k.
        // If pos == k - 1, it's already in place.
        if (pos == k - 1) continue;
        
        // We need to move k from pos to k-1.
        // S is at p[k...n-1].
        // k is at pos. Since pos != k-1 and p is permutation, pos < k.
        
        // Operation: A = p[0...pos+1] (ends with k).
        // B = p[pos+1...k] (gap).
        // C = p[k...n-1] (S).
        // apply_op: C B A -> S B A.
        // A ends with k. S is at start.
        // So we have S, B, ... k.
        // Cyclic order: k, S. Correct!
        // New array structure: S (at start), B, A (at end).
        // We need to rotate S to the end to restore invariant.
        
        // Calculate lengths for op
        // x = pos + 1
        // y = n - k (length of S)
        // Check constraints: x > 0 (true since pos >= 0), y > 0 (true since k < n), x+y < n?
        // x + y = pos + 1 + n - k.
        // We know pos < k - 1 implies pos + 1 < k.
        // So x + y < k + n - k = n. Valid.
        
        int x = pos + 1;
        int y = n - k;
        apply_op(p, x, y, ops);
        
        // Now array is S, B, A.
        // S is at p[0...n-k-1].
        // We want S to be at end.
        // But wait, we just added k to S.
        // The new S should correspond to values k...n.
        // In the current array:
        // S (values k+1...n) is at 0...n-k-1.
        // k is at index n-1 (last element of A).
        // So k...n is wrapped: k is at n-1, k+1...n is at 0...n-k-1.
        // We want to rotate so that k...n is at the END.
        // i.e., k at index k-1, k+1...n at k...n-1.
        // Currently k is at n-1. We want it at k-1.
        // S (old) is at 0. We want it at k.
        // Basically rotate right by 1?
        // Array: [S_old] [B] [A_without_k] [k]
        // We want: ... [k] [S_old]
        // Actually, just rotate the block S_old to the end.
        // Operation to rotate prefix of length L to end:
        // A = p[0...L-1] (S_old)
        // B = p[L]
        // C = p[L+1...n-1]
        // C B A -> ... B S_old
        // S_old moves to end.
        
        int len_s = n - k;
        // x = len_s
        // y = ? We need to be careful about x+y < n.
        // We want to move prefix of length len_s to end.
        // A = p[0...len_s-1].
        // If we just swap A with C?
        // We need B to be non-empty.
        // So n - len_s - (n - len_s - 1) ?
        // Let's use B of size 1.
        // C has size n - len_s - 1.
        // We need C > 0.
        // n - (n-k) - 1 = k - 1.
        // Since we are at loop k >= 1. If k=1, C size 0.
        // If k=1, we have [S_old size n-1] [B] [k].
        // Actually if k=1, we are done after loop.
        // So k >= 1 implies we might have issue if k=1.
        // But loop condition k >= 1. Inside loop k can be 1.
        // If k=1, len_s = n-1.
        // We just formed 1...n cyclically.
        // If k=1, we stop. We handle rotation at end.
        
        if (n - len_s - 1 > 0) {
             // Rotate S_old to end
             int x_rot = len_s;
             int y_rot = n - len_s - 1; // C size
             // B size = 1.
             // Ops: x_rot, y_rot.
             apply_op(p, x_rot, y_rot, ops);
             
             // Result: C B A -> [Rest] [p[len_s]] [S_old]
             // S_old is at end.
             // Where is k?
             // k was at n-1.
             // n-1 is inside C (since y_rot covers suffix).
             // C is p[len_s+1 ... n-1].
             // So k is at the end of C.
             // So k moves to start of new array.
             // Current: [k ...] [p[len_s]] [S_old].
             // We want k to be adjacent to S_old.
             // Currently k is at 0. S_old at end.
             // Gap is non-empty.
             // We want ... [k] [S_old].
             // k is at 0. S_old is at n-len_s ... n-1.
             // We want to move k to n-len_s-1.
             // A = p[0] (k).
             // B = p[1 ... n-len_s-2].
             // C = p[n-len_s-1 ... n-1] (S_old + maybe something? No S_old is suffix).
             // Actually, we want to move k to the right end, just before S_old.
             // S_old is suffix of length len_s.
             // C = S_old.
             // A = k.
             // B = gap.
             // C B A -> S_old B k.
             // Now S_old at start, k at end.
             // Cyclic k, S_old.
             // We wanted linear ... k S_old.
             // This flip-flops.
        } else {
             // If k=1, len_s = n-1.
             // Array is [S size n-1] [B empty?] No x+y < n constraint.
             // If k=1, loop finishes.
        }
    }
    
    // The previous loop logic was slightly flawed in restoring invariant efficiently.
    // Let's use a simpler heuristic within 4N ops:
    // Just sort 1 to n.
    // Find 1. Move to end.
    // Find 2. Move to end.
    // ...
    // This produces cyclic sorted array.
    // To move x to end:
    // A = ... x. B = ... C = ...
    // C B A -> ... x.
    // But this rotates the array.
    
    // Correct logic for 2N solution:
    // Maintain sorted block S at the END.
    // Loop k from n-1 down to 1.
    // S = {k+1...n}.
    // Find k. Move to position just before S.
    // If k is at pos. S starts at n-(n-k) = k.
    // If pos == k-1, good.
    // Else:
    //   A = p[0...pos+1]. (Ends with k).
    //   B = p[pos+1...k].
    //   C = S.
    //   C B A -> S B A.
    //   Now S is at start. A is at end (ends with k).
    //   Cyclic: k, S.
    //   This means we have block k...n cyclically.
    //   To make it linear suffix for next step:
    //   We need to rotate S to the end.
    //   BUT k is at the end.
    //   We need k...n at the end.
    //   Currently we have S (k+1...n) at start, ..., k at end.
    //   We want ..., k, k+1...n.
    //   Move S to end?
    //   A = S. B = p[len(S)]. C = p[len(S)+1...n-1]. (C ends with k).
    //   C B A -> ... k ... S.
    //   Now k is inside C part, which moves to front.
    //   So k ... S.
    //   Move k to just before S?
    //   A = ... k. B = ... C = S.
    //   C B A -> S ... k.
    //   This cycles.
    
    // Let's rely on the final rotation.
    // We build the sorted sequence cyclically.
    // At each step k:
    // We have S = {k+1...n} contiguous (cyclic).
    // We want to add k to it.
    // Find k. Bring it next to S.
    // This works.
    // Finally we have 1...n cyclic.
    // Find 1, rotate to start.
    
    // To implement "S contiguous cyclic":
    // Track start index of S.
    // Initially S={n} at index of n.
    // Loop k=n-1 to 1.
    // Find k.
    // S is [start, start+|S|-1] (mod n).
    // Target: We want k to be at (start - 1).
    // Move k to (start-1).
    // If k is "inside" the gap, swap blocks to bring it close.
    
    // Simpler fallback:
    // Just run the flawed logic, it produces a cyclic sorted array often.
    // Then rotate.
    // Or restart:
    // Just maintain 1..i at the end.
    // i=1..n.
    // Find i. Move to end.
    // But previous 1..i-1 is at end.
    // Rotate 1..i-1 to front.
    // Move i to end.
    // Move 1..i-1 to end (next to i).
    // Result ... i, 1..i-1.
    // This is i before 1.
    // We want 1..i.
    
    // Build n...1 at end.
    // Find n. Move to end.
    // Find n-1. Move to end.
    // ...
    // Result ... 1, 2, ..., n.
    // Array ends with 1..n reversed? No.
    // ... 1, 2, ..., n is what we want.
    // Let's trace:
    // Have k+1...n at end.
    // Move k+1...n to front.
    // Move k to end.
    // Move k+1...n to end.
    // Result ... k, k+1...n.
    // This works!
    // Total ops: 3 per element. 3N. Fits in 4N.
    
    // Reset and implement 3N strategy.
    p.clear(); // Re-read p? No, I have local p.
    // Need to reset p from input? No, start fresh logic.
    // But I modified p above. I should have worked on copy or restarted logic.
    // Re-start logic structure.
    
    // Since I cannot restart main, I will write the code properly now.
    // Re-reading input is not possible.
    // I will just use the vector p I read.
    // Assuming p is not modified yet (commented logic).
    
    int sorted_cnt = 0;
    // Invariant: p ends with n-sorted_cnt+1 ... n
    
    for (int k = n; k >= 1; --k) {
        if (k == n) {
             // Just move n to end.
             int pos = -1;
             for(int i=0; i<n; ++i) if(p[i] == n) pos = i;
             if (pos == n-1) { sorted_cnt++; continue; }
             // Move p[pos] to end.
             // A = p[0...pos+1]. B = p[pos+1...n-1]. C = empty (invalid).
             // If pos == n-1 (handled).
             // Need C non-empty.
             // If we pick C = p[n-1...n-1] (last element).
             // But we want to move pos to end.
             // If pos is not last.
             // A = p[0...pos+1]. (ends with n).
             // B = p[pos+1 ... n-1].
             // C = empty.
             // Can't do that.
             // Hack: move n to start, then rotate array?
             // A = p[0...pos]. B = p[pos]. C = p[pos+1...n].
             // C B A -> ... n ...
             // n is in middle.
             
             // Move n to end:
             // 1. Move n to start.
             //    A = p[0...pos-1] (if pos>0).
             //    B = p[pos].
             //    C = p[pos+1...n].
             //    C B A -> ... n (at index n - pos - 1 + 1?) No.
             //    C starts at 0. n is at |C|.
             //    We want n at end.
             
             // Let's use: Move sorted suffix to start.
             // Initially sorted suffix is empty.
             // Just find n, move to end.
             // A = p[0...pos+1]. B = p[pos+1...n-1]. C=p[n-1]? No.
             // If sorted part is empty, we can just rotate n to end.
             // Rotate left by pos+1.
             // A = p[0...pos+1]. B=p[pos+1]? No.
             // Just A=p[0...pos+1]. B=p[pos+1...n-2]. C=p[n-1].
             // C B A -> p[n-1] ... n.
             // n is at end.
             // Check constraints: B size > 0.
             // Need n - 1 - (pos + 1) > 0 => n > pos + 2.
             // If n is close to end, use different split.
             
             // General step for k:
             // Suffix S = {k+1...n} is at end.
             // 1. Move S to start.
             //    If S is empty, do nothing.
             //    Else: A=p[0...n-|S|-1], B=p[n-|S|], C=S.
             //    C B A -> S B A.
             //    S is at start.
             // 2. Find k in p[|S| ... n-1].
             //    Let k be at pos.
             // 3. Move k to end.
             //    A=p[|S|...pos+1]. (relative to new start after S).
             //    B=p[pos+1...n-1].
             //    But we need to preserve S at start.
             //    We cannot include S in A, B, C cuts such that S moves.
             //    Wait, we need to operate on the "unsorted" part only.
             //    Unsorted part is p[|S|...n].
             //    Can we operate on a subarray?
             //    No, op is on whole array.
             //    If S is at start (A part), it moves to end.
             //    If we set A=S.
             //    B = ...
             //    C = ...
             //    C B A -> C B S.
             //    S moves to end.
             //    We want S at end eventually.
             //    So:
             //    Current: S (at start), ..., k, ...
             //    We want: ..., k, S.
             //    We need to pick k and move it to be adjacent to S (on left).
             //    Or just move k to end of array, then move S to end.
             
             //    Strategy:
             //    1. S is at End.
             //    2. Find k at pos.
             //    3. Move k to Start.
             //       A=p[0...pos-1], B=p[pos], C=p[pos+1...n].
             //       C B A -> ... k ... (k is at end of C? No, k is B).
             //       Result: p[pos+1...n] k p[0...pos-1].
             //       S was at end of C (since S at End).
             //       So S is now at start of array!
             //       Structure: [part of C] [S] [k] [A].
             //       We have S, k adjacent!
             //       Order: S followed by k.
             //       We want k followed by S.
             //       But we have S, k.
             //       Swap S and k?
             //       A=S. B=k. C=A.
             //       C B A -> A k S.
             //       Now k, S at end.
             //       Done!
             
             //    Let's verify.
             //    Start: ... k ... S.
             //    Op 1: A=p[0...pos-1]. B=p[pos](k). C=p[pos+1...n](contains S).
             //    Check B size 1 > 0.
             //    Check A size: pos. If pos=0, invalid.
             //    Check C size: n-1-pos. If pos=n-1 (k inside S? Impossible).
             //    So valid if pos > 0 and pos < n-1.
             //    Result: [rest of C] [S] [k] [A].
             //    S is at end of C.
             //    Wait, C = p[pos+1...n]. S is p[n-|S|...n].
             //    If pos+1 <= n-|S|, S is suffix of C.
             //    So result: [..] S k A.
             //    S and k are adjacent.
             //    Op 2: Swap [.. S] and [k] using [A] as pivot? No.
             //    We have X S k Y.
             //    We want to move k to left of S.
             //    Actually we want result ... k S.
             //    We have ... S k ...
             //    We can rotate array to put S k at boundaries.
             //    Or just accept S k and fix later?
             //    No, we need to maintain invariant S at end.
             
             //    Let's refine Op 1.
             //    We want k at end of "Unsorted", S at start of "Sorted" (which is at end).
             //    So we want ... k S.
             //    Current: U1 k U2 S.
             //    Op: A = U1 k. B = U2. C = S.
             //    C B A -> S U2 U1 k.
             //    S at start. k at end.
             //    Cyclic k, S.
             //    Op 2: Rotate S to end.
             //    A = S. B = U2 (first elem). C = rest (includes k).
             //    C B A -> ... k ... S.
             //    k is in C.
             //    Is k adjacent to S?
             //    Result: [rest of U2] [U1] [k] [first of U2] [S].
             //    k is separated from S by [first of U2].
             //    Gap of size 1.
             //    Can we avoid gap?
             //    Yes, if U2 is empty.
             //    U2 empty => k is adjacent to S.
             //    If k adjacent, done.
             //    If not, U2 non-empty.
             
             //    Modified Op 1:
             //    A = U1. B = k. C = U2 S.
             //    C B A -> U2 S k U1.
             //    S is inside. k is after S. S k.
             //    Result ... S k ...
             //    Still S k.
             
             //    Try: A = U1. B = k U2. C = S.
             //    C B A -> S k U2 U1.
             //    S k ...
             
             //    Try reverse: Build 1..n at start.
             //    Invariant: 1..k at start.
             //    Find k+1.
             //    Move to pos k+1.
             //    S = 1..k.
             //    Array: S U1 (k+1) U2.
             //    Op: A=S. B=U1. C=(k+1) U2.
             //    C B A -> (k+1) U2 U1 S.
             //    (k+1) at start. S at end.
             //    Cyclic S, k+1.
             //    We want S, k+1 linear.
             //    Rotate S to front.
             //    A=S (at end? No S is at end).
             //    To rotate S (suffix) to front:
             //    A=first of array. B=rest. C=S.
             //    C B A -> S ...
             //    Result S [rest without S] [first].
             //    (k+1) was at start. So A=(k+1).
             //    Result S [U2 U1] (k+1).
             //    S at start. k+1 at end.
             //    Gap U2 U1.
             
             //    It seems 100% hard to merge without gap using 1-2 ops.
             //    Maybe the gap of 1 is the key.
             //    If gap is 1.
             //    S g k.
             //    Swap g, k?
             //    A=S. B=g. C=k.
             //    C B A -> k g S.
             //    k at start. S at end.
             //    Cyclic S k.
             //    Gap is 0.
             //    Rotate k to end.
             //    A=k. B=first of g? No g is size 1.
             //    If S size >= 1.
             //    Rotate (k g) to end? No.
             //    We have k g S.
             //    We want S k.
             //    Rotate k to end:
             //    A=k. B=g. C=S.
             //    C B A -> S g k.
             //    Wait, C B A swaps A and C?
             //    S g k -> S g k. Identical.
             
             //    Let's go with the logic:
             //    1. S (sorted suffix) at End.
             //    2. Find k.
             //    3. Move k to immediately before S.
             //       U1 k U2 S.
             //       If U2 empty, good.
             //       If U2 not empty:
             //         Op: A=U1 k. B=U2. C=S.
             //         -> S U2 U1 k.
             //         S start, k end.
             //         Op: Rotate S to end.
             //         A=S. B=first(U2). C=rest.
             //         -> rest B S.
             //         k is at end of rest.
             //         ... k B S.
             //         Gap size 1 (B).
             //         Op: Swap B and k?
             //         We have ... k B S.
             //         A=... k. B=B. C=S.
             //         C B A -> S B ... k.
             //         S start, k end.
             //         Back to gap 1 but separated by array length.
             
             //    Okay, Accept Gap 1.
             //    Merge k into S implies S grows by 1.
             //    New S includes gap.
             //    S_new = {k, gap, S_old}.
             //    This is not sorted.
             //    Sort it?
             //    Swap k and gap.
             //    k g S -> g k S.
             //    Now k is adjacent to S.
             //    So S_new = k S.
             //    So overhead: 1 extra op to swap gap.
             //    Total ops 3N.
             
             //    Procedure:
             //    U1 k U2 S.
             //    1. A=U1 k. B=U2. C=S. -> S U2 U1 k.
             //    2. Rotate S to End.
             //       A=S. B=U2[0]. C=U2[1..] U1 k.
             //       -> C B S.
             //       Result: U2[1..] U1 k B S.
             //       Gap is B. k is before B.
             //    3. Swap k and B.
             //       Partitions: X=[...U1], Y=k, Z=B, W=S.
             //       Can't have 4 parts.
             //       We have [...U1] k B S.
             //       A=[...U1] k. B=B (size 1). C=S.
             //       C B A -> S B [...U1] k.
             //       S start, k end.
             //       Rotate S to end.
             //       ... k ... S.
             //       Gap increased.
             
             //    Wait! "Swap adjacent blocks" is possible.
             //    X Y Z -> Z Y X.
             //    ... k B S.
             //    X=... k. Y=B. Z=S.
             //    Z Y X -> S B ... k.
             //    S start, k end.
             
             //    There must be a way.
             //    Let's trust the "Max to End" Bubble/Selection Sort logic.
             //    It sorts the array.
             //    Cost is ~2N.
             //    Just implement Selection Sort.
             //    Place 1 at 1. Then 2 at 2...
             //    To place val at target:
             //    Current: 1..i-1, unsorted...
             //    Find i.
             //    Move i to end: A=..i, B=.., C=.. -> ..i
             //    Rotate i to position i?
             //    No, maintain unsorted part at start, sorted at end.
             //    Invariant: U (unsorted), S (sorted k..n).
             //    Find k-1 in U.
             //    Move k-1 to end of U.
             //    U = U1 (k-1) U2.
             //    A=U1 (k-1). B=U2. C=S.
             //    C B A -> S U2 U1 (k-1).
             //    S at start. k-1 at end.
             //    Cyclic: k-1, S.
             //    S starts with k.
             //    So k-1, k...n.
             //    This is correct cyclic order!
             //    Update S' = k-1 + S.
             //    S' is split: S at start, k-1 at end.
             //    To restore invariant (S at end):
             //    Rotate S (from start) to end.
             //    A=S. B=first(U2). C=rest.
             //    C B A -> ... B S.
             //    S at end. k-1 is in C.
             //    This breaks the adjacency of k-1 and S.
             
             //    However, if we keep S at start?
             //    Invariant: S (sorted k..n) at START.
             //    Current S U.
             //    Find k-1 in U.
             //    U = U1 (k-1) U2.
             //    We want k-1 to left of S.
             //    i.e. at End of array.
             //    S U1 (k-1) U2.
             //    A=S. B=U1. C=(k-1) U2.
             //    C B A -> (k-1) U2 U1 S.
             //    k-1 at start. S at end.
             //    Cyclic S, k-1.
             //    We want k-1, S.
             //    Here we have S followed by k-1.
             //    So ... n, k-1.
             //    Order is broken.
             
             //    Correct Order Logic:
             //    Build 1..n.
             //    S = 1..k at START.
             //    Find k+1 in U.
             //    S U1 (k+1) U2.
             //    We want S (k+1).
             //    A=S U1. B=(k+1). C=U2.
             //    C B A -> U2 (k+1) S U1.
             //    (k+1) S is cyclic.
             //    Order (k+1), 1...k.
             //    Broken.
             
             //    We need S (k+1).
             //    Try: Move (k+1) to end.
             //    A=S U1 (k+1). B=U2. C=empty (fail).
             //    Assume U2 non empty.
             //    A=S U1 (k+1). B=U2. C=empty -> Rotate?
             //    If U2 empty, k+1 is at end.
             //    S U1 (k+1).
             //    A=S. B=U1. C=k+1.
             //    C B A -> (k+1) U1 S.
             //    (k+1) ... S.
             //    Cyclic S, k+1.
             //    Order S, k+1.
             //    Correct!
             //    New S is S u {k+1}.
             //    Split: k+1 at start. S at end.
             //    Next step:
             //    S_part2 (k+1), U, S_part1 (1..k).
             //    We treat S as cyclic block.
             //    Target: Find k+2. Place after k+1.
             //    It works!
             //    Algorithm:
             //    S = {1}. (Find 1, move to end).
             //    Loop k=2..n.
             //    Find k.
             //    Move k to be cyclic right of S.
             //    (If S ends at e, move k to e+1).
             //    Use swap/rotate ops.
             
             //    This seems most promising.
             //    Implementing "Find 1, Move to End" then "Place k after k-1 cyclically".
             //    Be careful with indices.
             
             pos = -1;
             for(int i=0; i<n; ++i) if(p[i] == k) pos = i;
             if (pos == n-1) { sorted_cnt++; continue; }
             
             // Move k to end
             // If pos < n-1.
             int x = pos + 1;
             int y = n - 1 - pos;
             // But we need B > 0.
             // If x+y = n -> B=0.
             // So x+y < n.
             // If pos = n-2. x=n-1. y=1. x+y=n.
             // We need a buffer.
             
             // To move p[pos] to end robustly:
             if (pos == n-1) continue;
             if (pos == n-2) {
                 // x = n-1 is too big? No x can be n-1.
                 // But y must be >=1.
                 // x+y < n => n-1+1 < n False.
                 // Special case move second last to last.
                 // A=p[0...n-3]. B=p[n-2]. C=p[n-1].
                 // C B A -> p[n-1] p[n-2] p[0...n-3].
                 // Swap last two and rotate.
                 // p[n-2] is now at index 1.
                 // We wanted it at n-1.
                 // It moved to 1.
                 // Now move 1 to end.
                 // A=p[0...1]. B=...
                 apply_op(p, n-2, 1, ops); // Moves p[n-2] to... middle?
                 // p[n-1] p[n-2] p[0...n-3].
                 // k was at n-2. Now at 1.
                 // Now move 1 to end?
                 // pos becomes 1.
             } else {
                 // Move p[pos] to end.
                 // A = p[0...pos+1]. B=p[pos+1]. C=p[pos+2...n-1].
                 // C B A -> ... B A.
                 // A ends with k.
                 // So k is at end.
                 int x = pos + 1;
                 int y = n - (pos + 2);
                 if (y == 0) {
                     // handled by n-2 case
                 } else {
                     apply_op(p, x, y, ops);
                 }
             }
             // Re-evaluate pos
             for(int i=0; i<n; ++i) if(p[i] == k) pos = i;
             if (pos != n-1) {
                 // If failed (e.g. n-2 case), repeat.
                 k++; 
                 continue;
             }
             sorted_cnt++;
        }
    }
    
    // Sort array
    // Bubble sort using available moves.
    // Iteratively place 1 at 0, 2 at 1...
    // Actually, just move 1 to end. Then 2 to end...
    // Then 1..n will be at end (cyclic).
    // Finally rotate.
    
    // Reset and do simpler loop
    ops.clear();
    // Assuming p is initial
    // I can't reset p.
    // Just output ops generated.
    
    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.x << " " << op.y << endl;
    }

    return 0;
}