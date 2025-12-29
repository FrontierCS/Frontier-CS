#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables
int n, m;
// Pillars are 1-based. n+1 is the auxiliary empty pillar.
// a[i] stores the colors of the balls in pillar i, from bottom to top.
vector<int> a[60]; 

struct Step {
    int x, y;
};
vector<Step> ans;

// Function to perform move and record it
void move_ball(int x, int y) {
    // Constraint check: y must have < m balls (so <= m-1).
    // The algorithm ensures this by only moving to non-full pillars or the empty pillar.
    // However, the auxiliary pillar (n+1) capacity is effectively m in our logic usage.
    a[y].push_back(a[x].back());
    a[x].pop_back();
    ans.push_back({x, y});
}

// Sorts pillar 'id' using 'helper' and 'empty_idx'.
// type 0: Balls with color <= mid go to bottom, > mid go to top.
// type 1: Balls with color > mid go to bottom, <= mid go to top.
// The pillar 'id' ends up sorted. 'helper' is restored to its original state.
void sort_pillar(int id, int type, int mid, int L, int R) {
    int cnt0 = 0; // Count of balls that should be at the bottom
    for (int c : a[id]) {
        bool is_small = (c <= mid);
        // type 0: small at bottom
        // type 1: large at bottom
        if (type == 0 && is_small) cnt0++;
        if (type == 1 && !is_small) cnt0++;
    }

    // Find a helper pillar in range [L, R] different from id
    int helper = -1;
    for (int k = L; k <= R; k++) {
        if (k != id) {
            helper = k;
            break;
        }
    }

    int empty_idx = n + 1;

    // 1. Move cnt0 balls from helper to empty
    // These are temporary storage to make space in helper
    for (int k = 0; k < cnt0; k++) move_ball(helper, empty_idx);

    // 2. Distribute balls from id
    // Balls intended for bottom -> helper
    // Balls intended for top -> empty
    int original_m = a[id].size(); 
    for (int k = 0; k < original_m; k++) {
        int c = a[id].back();
        bool is_small = (c <= mid);
        bool is_bottom_type = (type == 0 && is_small) || (type == 1 && !is_small);

        if (is_bottom_type) {
            move_ball(id, helper);
        } else {
            move_ball(id, empty_idx);
        }
    }

    // 3. Move 'bottom' balls from helper to id
    // Helper has cnt0 balls from id on top.
    for (int k = 0; k < cnt0; k++) move_ball(helper, id);

    // 4. Move 'top' balls from empty to id
    // Empty has 'top' balls on top.
    for (int k = 0; k < original_m - cnt0; k++) move_ball(empty_idx, id);

    // 5. Restore helper: move cnt0 balls from empty to helper
    // These are the original balls from helper we moved in step 1.
    for (int k = 0; k < cnt0; k++) move_ball(empty_idx, helper);
}

void solve(int L, int R) {
    if (L == R) return;
    int mid = (L + R) / 2;

    // Sort phase
    // Pillars in [L, mid] want small colors (<= mid) at bottom
    for (int i = L; i <= mid; i++) sort_pillar(i, 0, mid, L, R);
    // Pillars in [mid+1, R] want large colors (> mid) at bottom
    for (int i = mid + 1; i <= R; i++) sort_pillar(i, 1, mid, L, R);

    // Merge phase
    int pL = L;
    int pR = mid + 1;
    int empty_idx = n + 1;

    while (pL <= mid && pR <= R) {
        // We want to clear large balls (1s) from pL and small balls (0s) from pR.
        // Due to sorting:
        // pL has smalls at bottom, larges at top.
        // pR has larges at bottom, smalls at top.

        int cnt1_in_L = 0; // count of large balls in pL
        for (int c : a[pL]) if (c > mid) cnt1_in_L++;

        if (cnt1_in_L == 0) {
            pL++;
            continue;
        }

        int cnt0_in_R = 0; // count of small balls in pR
        // Note: pR might have been modified in previous steps, but smalls are always kept on top.
        for (int c : a[pR]) if (c <= mid) cnt0_in_R++;

        if (cnt0_in_R == 0) {
            pR++;
            continue;
        }

        int k = min(cnt1_in_L, cnt0_in_R);

        // 1. Move all available smalls from pR to empty
        for (int i = 0; i < cnt0_in_R; i++) move_ball(pR, empty_idx);

        // 2. Move k larges from pL to pR
        for (int i = 0; i < k; i++) move_ball(pL, pR);

        // 3. Move k smalls from empty to pL
        for (int i = 0; i < k; i++) move_ball(empty_idx, pL);

        // 4. Move remaining smalls from empty back to pR
        for (int i = 0; i < cnt0_in_R - k; i++) move_ball(empty_idx, pR);

        // If we removed all larges from pL, it is done
        if (k == cnt1_in_L) pL++;
        // If we removed all smalls from pR, it is effectively full of larges
        if (k == cnt0_in_R) pR++;
    }

    solve(L, mid);
    solve(mid + 1, R);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    for (int i = 1; i <= n; i++) {
        for (int j = 0; j < m; j++) {
            int c;
            cin >> c;
            a[i].push_back(c);
        }
    }

    solve(1, n);

    cout << ans.size() << "\n";
    for (auto &p : ans) {
        cout << p.x << " " << p.y << "\n";
    }

    return 0;
}