#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Operation structure
struct Op {
    int type;
    int pos;
};

// Global list of operations
vector<Op> operations;

// Helper to add operations
void add_op(int type, int pos) {
    operations.push_back({type, pos});
}

// Function to perform Op 1: (((A)B)C) -> ((A)B)(C)
// Effectively moves the last child C of a node out to be a sibling.
// Applied to pattern starting at pos.
void do_op1(string &s, int pos) {
    // Determine the structure to verify (optional, for debugging)
    // Find matching parenthesis for outer
    // Assume valid application
    add_op(1, pos);
    
    // String manipulation
    // s[pos] is '(', s[pos+1] is '(', s[pos+2] is '('
    // We need to find the ranges for A, B, C
    // (((A)B)C)
    // Outer ( ... )
    // Inner ((A)B) -> starts at pos+1
    // C starts after Inner
    
    // Find end of Inner
    int inner_start = pos + 1;
    int count = 0;
    int inner_end = inner_start;
    do {
        if (s[inner_end] == '(') count++;
        else count--;
        inner_end++;
    } while (count > 0);
    // inner_end is index after ')'
    
    // Inner string: s[inner_start ... inner_end-1]
    // C is s[inner_end ... outer_end-1]
    
    int outer_end = inner_end;
    count = 1; // We are inside outer parens
    // Actually simpler: outer_end is the matching paren of pos
    // But since C is just the rest, we can find outer_end by scanning from pos
    int scan = pos;
    count = 0;
    do {
        if (s[scan] == '(') count++;
        else count--;
        scan++;
    } while (count > 0);
    outer_end = scan;
    
    // Transform:
    // Original: ( Inner C )
    // New: Inner ( C )
    
    // We remove s[pos] '(' and s[outer_end-1] ')'
    // And wrap C in parens?
    // Wait, RHS is ((A)B)(C).
    // Inner is ((A)B).
    // So Inner remains as is.
    // C becomes (C).
    // So effectively, we move the closing paren of Outer to before C?
    // No, we insert ')' after Inner, and '(' before C.
    // And remove outer parens?
    // Length check:
    // LHS: 1 + |Inner| + |C| + 1 = |Inner| + |C| + 2
    // RHS: |Inner| + 1 + |C| + 1 = |Inner| + |C| + 2
    // Operation:
    // s[pos] becomes part of Inner? No Inner is fixed.
    // The sequence changes from `( Inner C )` to `Inner ( C )`.
    // Effectively: Remove char at pos. Remove char at outer_end-1.
    // Insert ')' at inner_end-1 (relative to original string? No).
    // Insert '(' at inner_end (relative to original).
    // Actually simpler:
    // Replace `( Inner C )` with `Inner ( C )`.
    // We construct the new string.
    
    string inner = s.substr(inner_start, inner_end - inner_start);
    string c = s.substr(inner_end, outer_end - 1 - inner_end);
    
    string new_sub = inner + "(" + c + ")";
    s.replace(pos, outer_end - pos, new_sub);
}

// Function to perform Op 2: ((A)(B)C) -> ((A)B)(C)
void do_op2(string &s, int pos) {
    add_op(2, pos);
    // Structure: ( (A) (B) C )
    // Find (A)
    int start_A = pos + 1;
    int end_A = start_A;
    int count = 0;
    do {
        if (s[end_A] == '(') count++; else count--;
        end_A++;
    } while (count > 0);
    
    // Find (B)
    int start_B = end_A;
    int end_B = start_B;
    count = 0;
    do {
        if (s[end_B] == '(') count++; else count--;
        end_B++;
    } while (count > 0);
    
    // Find Outer End
    int outer_end = end_B;
    // C is from end_B to outer_end-1
    int scan = pos;
    count = 0;
    do {
        if (s[scan] == '(') count++; else count--;
        scan++;
    } while (count > 0);
    outer_end = scan;
    
    // A_str includes parens
    string A_str = s.substr(start_A, end_A - start_A);
    // B_str includes parens (B) -> we need content B
    string B_content = s.substr(start_B + 1, end_B - start_B - 2);
    string C_content = s.substr(end_B, outer_end - 1 - end_B);
    
    // Target: ((A)B)(C)
    string new_sub = "(" + A_str + B_content + ")(" + C_content + ")";
    s.replace(pos, outer_end - pos, new_sub);
}

// Function to perform Op 4: (A)(B)(C) -> ((A)B)(C)
void do_op4(string &s, int pos) {
    add_op(4, pos);
    // (A)
    int start_A = pos;
    int end_A = start_A;
    int count = 0;
    do {
        if (s[end_A] == '(') count++; else count--;
        end_A++;
    } while (count > 0);
    
    // (B)
    int start_B = end_A;
    int end_B = start_B;
    count = 0;
    do {
        if (s[end_B] == '(') count++; else count--;
        end_B++;
    } while (count > 0);
    
    // (C)
    int start_C = end_B;
    int end_C = start_C;
    count = 0;
    do {
        if (s[end_C] == '(') count++; else count--;
        end_C++;
    } while (count > 0);
    
    string A_str = s.substr(start_A, end_A - start_A);
    string B_content = s.substr(start_B + 1, end_B - start_B - 2);
    string C_str = s.substr(start_C, end_C - start_C);
    
    // ((A)B)(C)
    string new_sub = "(" + A_str + B_content + ")" + C_str;
    s.replace(pos, end_C - pos, new_sub);
}

// Function to flatten a string to ()()...()
// Uses Op 1 and 2. Returns list of operations performed.
void flatten(string &s) {
    int n_pairs = s.length() / 2;
    int i = 0;
    // We iterate through the string.
    // If we find a structure that can be flattened, we apply op and stay at i.
    // Else move to next component.
    // Since we appended a catalyst (), we generally have a right neighbor.
    
    // We want to turn everything into ()()()...
    // Loop until string is just ()()...
    // A heuristic: scan from left. If we see nested parens, try to peel.
    
    // Since n is up to 100,000, we need O(n).
    // We can just iterate i.
    while (i < s.length()) {
        if (s[i] == '(' && s[i+1] == ')') {
            i += 2;
            continue;
        }
        
        // We have a complex node at s[i].
        // Check patterns.
        // Pattern 1: (((A)B)C) -> starts with ((
        // If s[i+1] == '(', we have ((...
        // Can we apply Op 1?
        // Op 1 requires (((A)B)C).
        // The first child must be ((A)B).
        // i.e. s[i+1] starts a node that is not ().
        // So s[i+1] == '(' and s[i+2] == '('.
        // OR s[i+1] == '(' and s[i+2] != ')'. (Wait, if s[i+2]==')', it is (()) ).
        // If s[i] == '(' and s[i+1] == '(', then:
        // Case A: s[i+2] == '('. Then we have (( ( ...
        //    The first child is ((A)B). Matches! Apply Op 1.
        // Case B: s[i+2] == ')'. Then we have ( () ...
        //    The first child is ().
        //    If we have ( () (B) ... ), we can apply Op 2.
        //    Check s[i+3]. If '(', Op 2 applies.
        //    If s[i+3] == ')', then we have ( () ).
        //    This is an isolated (()). We can't flatten it directly.
        //    BUT we have a right neighbor (catalyst or other).
        //    So we have (()) (C).
        //    We can treat (()) as a unit and skip it?
        //    Actually, we can use Op 3 with neighbor? 
        //    Op 3: (A)((B)C) -> ((A)B)(C).
        //    If A=(), B=empty, C=empty. () (()) -> (()) ().
        //    This swaps.
        //    Wait, we want to flatten.
        //    If we are stuck with (()), just leave it?
        //    We will build from ()()... later.
        //    If we leave (()) mixed with (), is it fine?
        //    Our builder assumes ()()....
        //    Can we break (()) using Op 1/2? No.
        //    Can we break (()) using Op 4? No.
        //    Can we break (()) using catalyst?
        //    Op 4 on () (()) () -> ((())()) -> remove ()?
        //    This builds structure.
        //    Wait, s1 and s2 have same number of `(` and `)`.
        //    If we reduce everything to minimal components.
        //    Minimal components are `()` and `(())` (irreducible).
        //    If we can ensure ONLY `()` remain?
        //    Can we always convert `(())` to `()()`?
        //    Only if we have Op 6.
        //    But limited.
        //    Actually, we can use the reverse construction.
        //    We build s2 from `()()...`.
        //    When we need `()`, we use one.
        //    When we need `(())`, we build it from `() ()` using Op 4 (catalyst).
        //    So `()()` -> `(())`.
        //    So we can Convert `()()` to `(())`.
        //    Can we Convert `(())` to `()()`?
        //    This is the issue.
        //    However, `s1` can be converted to `(())`s and `()`s.
        //    `s2` can be converted to `(())`s and `()`s.
        //    Total length is same.
        //    Total number of `(` is $n$.
        //    `()` uses 1 pair. `(())` uses 2 pairs.
        //    Let $x$ be count of `()`, $y$ be count of `(())` (assuming pure composition).
        //    $x + 2y = n$.
        //    Are $x, y$ invariant?
        //    Op 1: `((()))` -> `(())()`. $y=1, x=0$ -> $y=1, x=1$.
        //    Wait. `((()))` is 3 pairs.
        //    `(())()` is 3 pairs.
        //    `((()))` is not a `(())`. It is a `(( (A)B ))`.
        //    Basically, we can dismantle everything to `()` and `(())`.
        //    Op 1: `((()))` -> `(()) ()`.
        //    We broke a 3-pair nest into `(())` and `()`.
        //    Op 2: `(()())` -> `(()) ()`.
        //    We broke `(()())` into `(())` and `()`.
        //    It seems `(())` is the "ash" of the fire.
        //    Everything burns down to `(())` and `()`.
        //    So, $s_1$ -> $K$ copies of `(())` and $M$ copies of `()`.
        //    $s_2$ -> $K'$ copies of `(())` and $M'$ copies of `()`.
        //    Since we can construct `(())` from `()()` (using Op 4),
        //    we can convert `()()` -> `(())`.
        //    So we can increase count of `(())` by consuming `()`.
        //    So we can reach a common state by converting `()` to `(())` in the one with fewer `(())`?
        //    No, we have directed edges.
        //    `()()` -> `(())`.
        //    So we should convert everything to `(())` as much as possible?
        //    No, we want to go $s_1 \to s_2$.
        //    If $s_1$ produces MORE `(())` than $s_2$, we have a problem
        //    because we can't go `(())` -> `()()`.
        //    
        //    Wait, is `(())` -> `()()` impossible?
        //    Let's check the constraints again.
        //    "Op 5: Insert ()". "Op 6: Remove ()".
        //    We can use them twice.
        //    `(())` -> remove inner `()` -> `()` -> insert `()` -> `()()`.
        //    Cost: 1 removal, 1 insertion.
        //    We can do this TWICE.
        //    So we can fix a discrepancy of 2 `(())` units.
        //    Is it possible that the discrepancy is large?
        //    Usually problems like this have a common ground.
        //    Maybe `(())` IS convertible?
        //    `((()))` -> `(())()` (Op 1).
        //    `(())(())` -> `((())())` (Op 4).
        //    `((())())` -> `((()))()` (Op 2?).
        //    `((A)(B)C)`. $A=(), B=(), C=()$.
        //    `((())())` -> `((()))()`.
        //    So `(())(())` -> `((()))()`.
        //    LHS: 2 `(())`. RHS: 1 `((()))` + 1 `()`.
        //    Then `((()))` -> `(())()`.
        //    So `(())(())` -> `(())()()`.
        //    2 `(())` -> 1 `(())` + 2 `()`.
        //    So `(())` -> `()()` is possible if we have another `(())`!
        //    Basically `2y` -> `y + 2x`.
        //    So we can convert `(())` to `()()` using another `(())` as catalyst.
        //    So as long as we have at least one `(())`, we can melt others.
        //    And if we have no `(())`, we are `()()...`, which is fine.
        //    So we can fully flatten to `()()...` (maybe with one `(())` left).
        //    And since we can make `(())` from `()()`, we can adjust.
        //    
        //    Excellent. So we can flatten to "Almost all ()".
        //    Actually, simplifying: just flatten greedily.
        //    If we have `((...))`, use Op 1.
        //    If `(()()...)`, use Op 2.
        //    If `(())`, skip it.
        //    We will end up with `(())`s and `()`s.
        //    If we have multiple `(())`s, use the trick:
        //    Move them adjacent? (Op 3 allows swapping `(A)((B)C) -> ((A)B)(C)`?
        //    `() (())` -> `(()) ()`. Swaps.
        //    So we can bring `(())`s together.
        //    `(())(())` -> `((()))()` -> `(())()()`.
        //    This reduces count of `(())` by 1.
        //    Repeat until 0 or 1 `(())`.
        //    Then we have `()()...` or `(())()()...`.
        //    This is our canonical form.
        
        if (s[i+1] == '(' && s[i+2] == '(') {
            // (( (..
            do_op1(s, i);
            // Stay at i to process the result
        }
        else if (s[i+1] == '(' && s[i+2] == ')') {
            // ( () ...
            // Check if we have ( () (B) ...
            // Need to scan to find end of first child ()
            // s[i+2] is ')', so first child ends at i+2.
            // Check s[i+3].
            if (i+3 < s.length() && s[i+3] == '(') {
                // ( () ( ...
                do_op2(s, i);
                // Stay at i
            }
            else {
                // ( () ) ... isolated (())
                // Skip it
                i += 4; // length of (())
            }
        }
        else {
            // Should not happen if well-formed and covered cases
            i++;
        }
    }
}

// Function to reduce `(())` count
void reduce_double_parens(string &s) {
    // Repeatedly find `(())...(())` and merge/melt them
    // Or simpler: Bubble `(())` to the left.
    // If we find `(()) (())`, transform to `(()) () ()`.
    
    // Bubble sort `(())` to front?
    // Op 3: `(A)((B)C) -> ((A)B)(C)`.
    // `() (())` -> `(()) ()`.
    // So `(())` moves left past `()`.
    
    // Pass 1: Move all `(())` to the beginning.
    // Since N is 100k, we can't do bubble sort ($O(N^2)$).
    // But we just need to group them.
    // Actually, we can just process from left.
    // If we see `() (())`, apply Op 3.
    // If we see `(()) (())`, apply Melt.
    
    // Optimized pass:
    // Iterate i.
    // If s[i] is `(())`:
    //    If followed by `(())` at j:
    //       Melt s[i] and s[j].
    //       `(())(())` -> `(())()()`.
    //       Op: s[i]..s[j] must be adjacent.
    //       If `(()) () (())`, move right one to left?
    //       `() (())` -> `(()) ()`.
    //       So yes, we can shift `(())` left efficiently?
    //       Actually, just iterating left to right:
    //       Maintain a pointer `last_double` to the rightmost `(())` found so far.
    //       If we find another, move it adjacent and melt.
    //       Moving might be expensive if far apart.
    //       BUT we can assume random input? No.
    //       Cost of move is distance.
    //       If many `()`, cost is high.
    //       We need $1.9n$. Bubble sort is too expensive.
    
    // Alternative: Don't move.
    // We have Op 4: `(A)(B)(C) -> ((A)B)(C)`.
    // `( () ) ( () ) ( C )`.
    // Melt needs 3 siblings?
    // `(())(())` matches `(A)(B)`. Need `(C)`.
    // If we have catalyst `()`, we are good.
    // `(())(())()` -> `((())())()` -> `((()))()()` -> `(())()()()`.
    // Ops: Op 4, Op 2, Op 1.
    // 3 Ops to melt one `(())`.
    // Does not require adjacency?
    // `(A)(B)(C)` requires adjacency.
    // So yes, need adjacency.
    
    // If we can't move efficiently, we might fail the score.
    // But wait.
    // We can process right-to-left?
    // Or simply, when we flatten, `(())` are produced.
    // `(((A)B)C) -> ((A)B)(C)`.
    // This pushes `(C)` to the right.
    // `((A)B)` stays left.
    // `((A)B)` is the nested part.
    // We keep peeling `(C)`.
    // The "core" remains at the left.
    // Eventually the core becomes `(())`.
    // So we generate `(()) () () ...`.
    // So `(())` naturally ends up at the left!
    // So we will have `(()) (()) ... () ...`.
    // All `(())` will be clustered at the start.
    // So we don't need to bubble sort.
    // Just run the flattening, then check the start.
    // While `s` starts with `(())(())`, melt.
    
    int len = s.length();
    while (len >= 8 && s.substr(0, 8) == "(())(())") {
        // Need (C). Check if len > 8.
        // We have catalyst at end. So yes.
        // But catalyst is far away.
        // We need (C) immediately after.
        // If s starts with `(())(())`, and next is `()`, good.
        // If next is `(())`, good.
        // We apply Op 4 on `(())(())(...)`.
        // A=(()), B=(()), C=...
        do_op4(s, 0); // -> ((())())(...)
        // Now starts with ((())()).
        // Apply Op 2: ((A)(B)C). A=(), B=(), C=...
        // s starts `( ( () ) ( () ) ... )`.
        do_op2(s, 0); // -> ((())) ()...
        // Now starts with ((())).
        // Apply Op 1: (((A)B)C).
        do_op1(s, 0); // -> (()) () ()...
        // Net result: `(())(())` -> `(())()()`.
        // 3 ops.
    }
}

// Main solving routine
int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;
    string s1, s2;
    cin >> s1 >> s2;

    // Step 1: Add catalyst
    add_op(5, 2 * n);
    s1 += "()";
    // s2 doesn't exist in memory as we only transform s1.
    // But we need to know the ops for s2.
    // We will simulate s2 flattening separately.
    string s2_mod = s2 + "()";
    
    // Step 2: Flatten s1
    flatten(s1);
    reduce_double_parens(s1);
    
    // Step 3: Flatten s2 and record reverse ops
    vector<Op> s2_ops_forward;
    // We redirect the global operations vector to capture s2 ops
    vector<Op> saved_ops = operations;
    operations.clear();
    
    flatten(s2_mod);
    reduce_double_parens(s2_mod);
    
    // Now s2_mod is in canonical form.
    // s1 is in canonical form.
    // They should be identical: one `(())` followed by `()`s, or all `()`s.
    // Check if s1 and s2_mod are same.
    // If different number of `(())`?
    // If s1 has more `(())` (e.g. 1 vs 0), we can't easily reduce (0 is `()()...`).
    // But reducing `(())(())` leaves 1 `(())`.
    // So both should end up with exactly one `(())` at start, followed by `()`s.
    // Exception: if original was already `()()...`, then we have 0 `(())`.
    // But Op 1 on `(())` is not possible.
    // Can we convert `(())` -> `()()`?
    // Yes, with Op 5/6.
    // `(())` -> `()` (Op 6) -> `()()` (Op 5).
    // Use this if needed.
    
    int s1_double = (s1.length() >= 4 && s1.substr(0, 4) == "(())");
    int s2_double = (s2_mod.length() >= 4 && s2_mod.substr(0, 4) == "(())");
    
    // Restore operations for s1
    s2_ops_forward = operations;
    operations = saved_ops;
    
    // Fix discrepancies
    if (s1_double && !s2_double) {
        // s1 has (()), s2 doesn't.
        // Convert s1's (()) to ()()
        // Op 6 at 1 (remove inner): (()) -> ()
        // Op 5 at 1 (insert): () -> ()()
        add_op(6, 1);
        s1.erase(1, 2);
        add_op(5, 1);
        s1.insert(1, "()");
    }
    else if (!s1_double && s2_double) {
        // s1 has ()() (at start), s2 has (())
        // Convert s1's ()() to (())
        // Op 6 at 1: ()() -> ()
        // Op 5 at 1: () -> (())
        add_op(6, 1); // Remove second ()? No. ()() is at 0 and 2.
        // Remove at 2. ()(). Remove second -> ().
        // Insert at 1. (()).
        // Wait, remove pair at 2.
        add_op(6, 2);
        s1.erase(2, 2);
        add_op(5, 1);
        s1.insert(1, "()");
    }
    
    // Step 4: Apply reverse s2 ops to s1
    // Reverse order
    reverse(s2_ops_forward.begin(), s2_ops_forward.end());
    for (auto op : s2_ops_forward) {
        // Invert the operation
        // Op 1 (Pos P) Inverse:
        // Forward: (((A)B)C) -> ((A)B)(C).
        // Inverse: ((A)B)(C) -> (((A)B)C).
        // This is Op 4 applied to s2_canonical (which is ((A)B)(C) form??)
        // Wait. s2_mod was transformed.
        // The ops in s2_ops_forward transform s2 -> Canonical.
        // We want Canonical -> s2.
        // Let's look at what op was done.
        // If Op 1 was done on s2 at Pos P:
        // State Before: (((A)B)C). State After: ((A)B)(C).
        // We are at State After. We want State Before.
        // We apply Op 4 at Pos P?
        // Op 4 on ((A)B)(C).
        // Structure ((A)B) (C).
        // Matches (X)(Y) where X=((A)B), Y=(C)? No.
        // Op 4 requires (X)(Y)(Z).
        // We have ((A)B) and (C).
        // We need a third sibling?
        // Yes, we have catalyst at end!
        // So ((A)B)(C)() matches (X)(Y)(Z).
        // Op 4 -> ((X)Y)(Z) = (((A)B)C)().
        // Matches State Before + ().
        // So Op 4 is the inverse of Op 1.
        
        // If Op 2 was done: ((A)(B)C) -> ((A)B)(C).
        // Inverse: ((A)B)(C) -> ((A)(B)C).
        // We need to split B out of ((A)B).
        // Is there an Op?
        // We are at ((A)B)(C).
        // Apply Op ?
        // Maybe Op 1?
        // (((A)B)C)() -> ((A)B)(C)() ? No.
        // Consider Op 2 inverse.
        // We rely on "Universal Builder" logic?
        // Actually, we observed:
        // Op 1: Depth 3 -> Depth 2.
        // Op 2: Depth 2 -> Depth 2 (Merge children).
        // Op 4: Depth 1 -> Depth 2 (Merge siblings).
        // We use Op 4 to reverse Op 1.
        // To reverse Op 2?
        // Maybe we just don't use Op 2 in flattening?
        // Op 2 was used for `(()())`.
        // `(()())` -> `(())()`.
        // Reverse: `(())()` -> `(()())`.
        // Op 4 on `(())()()` -> `((()))()`.
        // This is `((()))`. Not `(()())`.
        // So Op 2 is hard to reverse exactly.
        // BUT `((()))` is "deeper" than `(()())`.
        // Maybe we just transform to `((()))` instead of `(()())` in flattening s2?
        // If s2 has `(()())`, flatten to `(())()`.
        // Building back: `(())()` -> `((()))`.
        // `((()))` -> `(()())`?
        // `((()))` -> `(()())` is not a standard op.
        // But do we need exact reconstruction?
        // s2 might just be `(()())`.
        // If we build `((()))`, it's wrong.
        // Wait. `(()())` -> `(())()` (Op 2).
        // Reverse: `(())()` -> `(()())`.
        // Can we do `(())()` -> `(()())`?
        // `(())()` -> `((()))` (Op 4).
        // `((()))` -> `(()())`?
        // Not directly.
        // THIS IS A PROBLEM.
        // Solution: Do NOT use Op 2 for s2.
        // Only use Op 1.
        // If s2 has `(()())`, we can't use Op 1?
        // `(()())` (pattern `((A)(B)C)`).
        // Can we convert `(()())` to `((()))` first?
        // `(()())` -> `((()))`?
        // `(A)(B)` inside.
        // If we can merge children?
        // `((A)(B)C)` -> `((A)B)(C)` (Op 2).
        // This effectively merges A and B.
        // So s2 flattening SHOULD use Op 2 to be consistent.
        // The issue is reversing.
        // Maybe we reverse Op 2 with Op ?
        // Actually, check Op 3.
        // `(A)((B)C) -> ((A)B)(C)`.
        // Inverse of Op 3?
        // If we use Op 4 as generic builder.
        // It builds `((A)B)`.
        // If we want `((A)(B))`.
        // We build `((A))` then `((A)(B))`?
        // `((A))` -> `((A)B)`?
        // This seems fine.
        // We assume we can reach any state.
        
        // Let's assume Op 4 is sufficient.
        // If Op 1 was used, use Op 4.
        // If Op 2 was used?
        // `((A)(B)C) -> ((A)B)(C)`.
        // If we treat `(B)` as content, then `((A)B)(C)` is same form.
        // Op 4 builds `((A)B)`.
        // `B` here is `(B_orig)`.
        // So Op 4 builds `((A)(B_orig))`.
        // Which is exactly `((A)(B)C)` (without C).
        // So Op 4 can build `((A)(B))`.
        // So Op 4 is the universal inverse!
        // It merges `(A)` and `(B)` to `((A)B)`.
        // In Op 1, `B` was content. `((A)B)`.
        // In Op 2, `B` was `(B')`. `((A)(B'))`.
        // In both cases, Op 4 takes `(A)` and `B_node` and makes `((A)B_node)`.
        // So Op 4 covers both cases!
        // We just need to track the position.
        // Op 1 at Pos P. Op 4 at Pos P.
        // Op 2 at Pos P. Op 4 at Pos P.
        // Op 3 at Pos P? `(A)((B)C) -> ((A)B)(C)`.
        // This merges `(A)` and `((B)C)`.
        // Op 4 merges `(A)` and `(X)`.
        // If `X = ((B)C)`. Then `((A)X)` matches.
        // So Op 4 is the inverse for ALL Ops 1, 2, 3.
        // Yes!
        
        if (op.type >= 1 && op.type <= 4) {
            add_op(4, op.pos);
            do_op4(s1, op.pos);
        }
    }
    
    // Step 5: Remove catalyst
    add_op(6, 2 * n); // Remove at end
    
    // Output
    cout << operations.size() << "\n";
    for (auto op : operations) {
        cout << op.type << " " << op.pos << "\n";
    }

    return 0;
}