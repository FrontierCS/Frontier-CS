#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

// Represents the state of a basket as a set of balls
typedef vector<int> Basket;

// Function to calculate the center of a basket
int get_center(const Basket& b) {
    if (b.empty()) return 0;
    // Balls are sorted
    int k = b.size();
    int idx = k / 2; // 0-based index. Formula is floor(k/2) + 1 (1-based) -> floor(k/2) (0-based)
    return b[idx];
}

// Global vector to store moves
vector<pair<int, int>> moves;

// Helper to check validity (for debugging/verification)
bool can_move(const Basket& from, const Basket& to) {
    if (from.empty()) return false;
    int ball = get_center(from);
    Basket next_to = to;
    next_to.push_back(ball);
    sort(next_to.begin(), next_to.end());
    if (get_center(next_to) == ball) return true;
    return false;
}

// Function to execute a move
void do_move(vector<Basket>& baskets, int a, int b) {
    int ball = get_center(baskets[a]);
    // remove ball from a
    auto it = lower_bound(baskets[a].begin(), baskets[a].end(), ball);
    baskets[a].erase(it);
    // add to b
    baskets[b].push_back(ball);
    sort(baskets[b].begin(), baskets[b].end());
    moves.push_back({a + 1, b + 1});
}

// Recursive solver
// Strategy: To move a range [L, R] from 'src' to 'dst' using 'aux'.
// The balls forming the range are assumed to be present in 'src' and accessible (i.e., center logic applies).
// The 'aux' and 'dst' baskets may contain other balls, but we must respect compatibility.
//
// Based on the N=4 manual solution:
// Order of insertion into Dst: Reverse Pre-Order of the BST.
// R_L, L, R_R -> R, L, u ? No.
//
// We use a specific pattern:
// To move tree rooted at u with children L and R from src to dst:
// 1. Move u to Aux.
// 2. Move R to Aux. (Compatible since R > u)
// 3. Move L to Dst. (Compatible with whatever is in Dst usually)
// 4. Move R from Aux to Dst.
// 5. Move u from Aux to Dst.
//
// Let's refine step 3. L < u. Dst might be empty or have smaller stuff.
// Step 4. R > u. R > L. Dst has L. R is compatible with L?
// Example {1, 2} in Dst. Add 4 -> {1, 2, 4}. Center 2. Fail.
// So R is NOT compatible with L in Dst directly.
//
// Correct Pattern derived from N=1,2,3:
// Move u to Aux.
// Move L to Dst.
// Move R to Dst.
// Move u to Dst.
// This works for N=3. Fails for N=4 ({1,2} to Dst).
//
// Alternative Pattern for Left Child failure:
// If moving L to Dst fails because Aux is blocked, maybe we need to use Dst as Aux for L?
// No.
//
// The fallback is: The standard algorithm works for Right-heavy trees.
// For Left-heavy, we need to handle carefully.
//
// Implementation of the "Center Ball Problem" recursive algorithm:
// Move(k, S, D, A):
//   m = center(1..k)
//   Move(m-1, S, A, D)  <-- Move Left to Aux?
//   Move ball m S->D
//   Move(k-m, S, D, A)  <-- Move Right to Dst?
//   Move(m-1, A, D, S)  <-- Move Left to Dst
// This is the standard Hanoi. But moves are restricted.
//
// Since we only need code, I will implement a deep search for N up to 6 to confirm pattern or just a heuristic solver.
// But N=30 requires O(1) recursion.
// The pattern 3-to-Aux, 4-to-Dst, 1-to-Dst, 2-to-Dst, 3-to-Dst worked for N=4.
// This corresponds to:
// u -> Aux
// R -> Dst
// L -> Dst
// u -> Dst
// This implies L can be moved to Dst even if Dst has R?
// Dst has {4}. Move {1, 2} to Dst.
// 1 to Dst ({4}->{1,4}). 2 to Dst ({1,4}->{1,2,4}).
// It works!
//
// So the pattern IS:
// solve(Range):
//   u = center
//   move u to Aux
//   solve(Right, src, dst, aux)
//   solve(Left, src, dst, aux)
//   move u to Dst
//
// Wait, this worked for N=4. Let's check N=3.
// u=2, L=1, R=3.
// 2 to Aux.
// Solve(3, src, dst, aux):
//    3 to Aux? (Has 2). {2, 3}. OK.
//    L, R empty.
//    3 to Dst? (Has 1?? No Dst empty). OK.
//    Wait, in N=3 trace: 2->Aux, 1->Dst, 3->Dst, 2->Dst.
//    My pattern says: 2->Aux, R->Dst, L->Dst, 2->Dst.
//    R->Dst means 3->Dst.
//    L->Dst means 1->Dst.
//    So: 2->Aux, 3->Dst, 1->Dst, 2->Dst.
//    Check:
//    2->B. A:{1,3}, B:{2}, C:{}.
//    3->C. C:{3}.
//    1->C. C:{1,3}. Center 3. Fail.
//
// So N=3 requires L then R. N=4 requires R then L.
// Why?
// N=3: L={1}, R={3}. Dst gets 1 then 3 -> {1, 3} (Center 3, ball 3). OK.
// N=4: L={1, 2}, R={4}. Dst gets 4 then {1, 2}.
//      {4} -> +1 -> {1, 4} (Center 1). +2 -> {1, 2, 4} (Center 2). OK.
//
// It seems we must inspect the sets to decide order.
// Heuristic: Try L then R. If invalid, try R then L.
// Since it's recursive, valid means "compatible".
// Compatibility check:
// Can we place L on R?
// Can we place R on L?
//
// Code structure:
// solve(balls, src, dst, aux)
//   if empty return
//   m = center
//   move m to aux
//   // Try L then R
//   if (can_stack(L, R)) { solve L; solve R; }
//   else { solve R; solve L; }
//   move m to dst

Basket s1, s2, s3;

int get_center_val(int n, int start_idx) {
    return start_idx + n/2; // 0-based from start_idx? No balls are 1..N.
    // If balls are 1..N. size N.
    // Index N/2. Value is balls[N/2].
    // If consecutive, start..start+n-1.
    // Center is start + n/2.
}

// Function to generate the balls in a range
vector<int> get_range(int start, int count) {
    vector<int> res;
    for(int i=0; i<count; ++i) res.push_back(start + i);
    return res;
}

void solve(int start, int count, int src, int dst, int aux) {
    if (count == 0) return;
    if (count == 1) {
        do_move({&s1, &s2, &s3}, src, dst);
        return;
    }

    int center = start + count / 2;
    int left_count = center - start;
    int right_count = count - 1 - left_count;
    int right_start = center + 1;

    // Move center to aux
    do_move({&s1, &s2, &s3}, src, aux);

    // Decide order.
    // We simulate the effect on Dst.
    // We assume Dst currently has some state S.
    // Option 1: Add L then R.
    //   Ball sequence: L's reverse-preorder, then R's reverse-preorder.
    // Option 2: Add R then L.
    
    // We can verify base cases.
    // N=3 (1, 3). L=1, R=3.
    // L then R: {1} -> {1, 3} (ball 3, center 3). OK.
    // R then L: {3} -> {1, 3} (ball 1, center 3). Fail.
    // So N=3 needs L then R.
    
    // N=4 (1, 2; 4). L={1, 2}, R={4}.
    // L then R: {1, 2} -> {1, 2, 4} (ball 4, center 2). Fail.
    // R then L: {4} -> {1, 4} (ball 1) -> {1, 2, 4} (ball 2). OK.
    
    // Condition seems to be parity of Left size?
    // Left size 1 (odd) -> L then R.
    // Left size 2 (even) -> R then L.
    
    if (left_count % 2 != 0) {
        // L then R
        solve(start, left_count, src, dst, aux);
        solve(right_start, right_count, src, dst, aux);
    } else {
        // R then L
        solve(right_start, right_count, src, dst, aux);
        solve(start, left_count, src, dst, aux);
    }

    // Move center to dst
    do_move({&s1, &s2, &s3}, aux, dst);
}

int main() {
    int N;
    if (cin >> N) {
        for(int i=1; i<=N; ++i) s1.push_back(i);
        solve(1, N, 0, 2, 1);
        cout << moves.size() << endl;
        for(auto p : moves) cout << p.first << " " << p.second << endl;
    }
    return 0;
}