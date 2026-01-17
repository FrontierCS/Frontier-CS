#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to store the state of the game
int n, m;
vector<int> a[60]; // pillars, 1-based. a[n+1] is initially empty.
struct Move {
    int x, y;
};
vector<Move> ops;

// Function to perform a move and record it
void move_ball(int x, int y) {
    // In a valid solution, x should not be empty and y should have space.
    // The algorithm guarantees this.
    int c = a[x].back();
    a[x].pop_back();
    a[y].push_back(c);
    ops.push_back({x, y});
}

// Helper to check if a color c belongs to the "left" set [L, mid]
bool in_range(int c, int L, int mid) {
    return c >= L && c <= mid;
}

// Reorders a specific column `col` such that:
// If `bottom` is true: balls with color in [L, mid] (Set A) are at the BOTTOM, others (Set B) at TOP.
// If `bottom` is false: balls with color in [L, mid] (Set A) are at the TOP, others (Set B) at BOTTOM.
// Uses `empty_p` (n+1) and a `helper` column. 
// Precondition: `col` and `helper` are full (size m), `empty_p` is empty.
// Postcondition: `col` is sorted as requested, `helper` is restored to original state, `empty_p` is empty.
void reorder(int col, int L, int mid, bool bottom) {
    int cntA = 0;
    for (int c : a[col]) {
        if (in_range(c, L, mid)) cntA++;
    }
    // If already pure, nothing to do (also handles cntA=0 or cntA=m)
    if (cntA == 0 || cntA == m) return; 

    int cntB = m - cntA;
    // Choose a helper column different from col. 
    // Since n >= 2, if col is 1, use 2; else use 1.
    int helper = (col == 1) ? 2 : 1;
    int empty_p = n + 1;

    // We want to filter `col` using `helper` and `empty_p`.
    // The strategy requires space in `empty_p` and `helper`.
    // We create space by moving balls from `helper` to `empty_p`.
    
    // Determine how many balls to move from `helper` to `empty_p`.
    // This depends on which set goes to `empty_p` during filtering.
    // If bottom=true (A to Bottom), we want A entering `col` first.
    // To achieve this, A balls should reside in `empty_p` and B balls in `helper` after filtering.
    // So we need space for A in `empty_p`, i.e., cntA slots.
    // But `empty_p` already will contain balls from `helper`.
    // Capacity constraint: The balls from `helper` + cntA balls from `col` <= m.
    // Let x be balls moved from `helper`. Total in `empty_p` = x + cntA.
    // Also `helper` must hold B balls. Space needed: cntB.
    // `helper` had m, moved x, so space is x. We need x >= cntB.
    // So we need x >= m - cntA.
    // And x + cntA <= m => x <= m - cntA.
    // Thus, we must move exactly m - cntA balls from `helper` to `empty_p`.

    int k; 
    if (bottom) {
        // Target: [Bottom: A, Top: B]
        // Filter plan: A -> empty_p, B -> helper
        k = cntA; // We move A balls to empty_p
    } else {
        // Target: [Bottom: B, Top: A]
        // Filter plan: B -> empty_p, A -> helper
        k = cntB; // We move B balls to empty_p
    }

    // Prepare helper and empty_p
    // We need to move (m - k) balls from helper to empty_p
    int setup_moves = m - k;
    for (int i = 0; i < setup_moves; ++i) move_ball(helper, empty_p);

    // Filter `col`
    for (int i = 0; i < m; ++i) {
        int c = a[col].back();
        bool isA = in_range(c, L, mid);
        
        // Decide destination based on target configuration
        bool to_empty; 
        if (bottom) {
            // If bottom=true, we want A at bottom. 
            // So A goes to empty_p (to be put back first), B goes to helper.
            to_empty = isA;
        } else {
            // If bottom=false, we want B at bottom.
            // So B goes to empty_p, A goes to helper.
            to_empty = !isA;
        }

        if (to_empty) move_ball(col, empty_p);
        else move_ball(col, helper);
    }

    // Now `col` is empty.
    // If bottom=true: empty_p has A's (on top), helper has B's (on top).
    //   Move A's from empty_p to col (goes to bottom).
    //   Move B's from helper to col (goes to top).
    // If bottom=false: empty_p has B's, helper has A's.
    //   Move B's from empty_p to col (goes to bottom).
    //   Move A's from helper to col (goes to top).

    if (bottom) {
        for (int i = 0; i < cntA; ++i) move_ball(empty_p, col);
        for (int i = 0; i < cntB; ++i) move_ball(helper, col);
    } else {
        for (int i = 0; i < cntB; ++i) move_ball(empty_p, col);
        for (int i = 0; i < cntA; ++i) move_ball(helper, col);
    }

    // Restore helper
    // Move the setup balls back from empty_p to helper
    for (int i = 0; i < setup_moves; ++i) move_ball(empty_p, helper);
}

// Divide and Conquer solver
// Arranges balls such that pillars l..mid contain colors l..mid
// and pillars mid+1..r contain colors mid+1..r
void solve(int l, int r) {
    if (l >= r) return;
    int mid = (l + r) / 2;

    // Phase 1: Reorder all columns in range [l, r]
    // Left pillars (l..mid): Put target colors (l..mid) at BOTTOM, others at TOP.
    // Right pillars (mid+1..r): Put target colors (l..mid) at TOP, others at BOTTOM.
    for (int i = l; i <= r; ++i) {
        if (i <= mid) reorder(i, l, mid, true); 
        else reorder(i, l, mid, false); 
    }

    // Phase 2: Swap tops
    // Left pillars have B on top, Right pillars have A on top.
    // Swap them so Left gets A, Right gets B.
    int i = l;
    int j = mid + 1;
    int empty_p = n + 1;

    while (i <= mid && j <= r) {
        // Count B balls (colors > mid) on top of pillar i
        int cntB_top = 0;
        for (int k = a[i].size() - 1; k >= 0; --k) {
            if (!in_range(a[i][k], l, mid)) cntB_top++;
            else break;
        }

        // Count A balls (colors <= mid) on top of pillar j
        int cntA_top = 0;
        for (int k = a[j].size() - 1; k >= 0; --k) {
            if (in_range(a[j][k], l, mid)) cntA_top++;
            else break;
        }

        if (cntB_top == 0) {
            i++;
            continue;
        }
        if (cntA_top == 0) {
            j++;
            continue;
        }

        int k = min(cntB_top, cntA_top);
        
        // Swap k balls between i and j using empty_p
        // i -> empty_p
        // j -> i
        // empty_p -> j
        for (int x = 0; x < k; ++x) move_ball(i, empty_p);
        for (int x = 0; x < k; ++x) move_ball(j, i);
        for (int x = 0; x < k; ++x) move_ball(empty_p, j);
    }

    // Recursive calls
    solve(l, mid);
    solve(mid + 1, r);
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int c;
            cin >> c;
            a[i].push_back(c);
        }
    }

    solve(1, n);

    cout << ops.size() << "\n";
    for (const auto& p : ops) {
        cout << p.x << " " << p.y << "\n";
    }

    return 0;
}