#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to store the state
int n, m;
struct Move {
    int x, y;
};
vector<Move> ans;
// pillars[i] stores the balls on pillar i (1-based index)
// Using vector as a stack: back() is the top.
vector<int> pillars[60]; 

// Helper to record a move
void record_move(int x, int y) {
    ans.push_back({x, y});
    int ball = pillars[x].back();
    pillars[x].pop_back();
    pillars[y].push_back(ball);
}

// Check if a color is in the range [l, r]
bool is_in_range(int color, int l, int r) {
    return color >= l && color <= r;
}

/**
 * Sorts pillar p_idx such that all balls with color in [c_l, c_r] are moved to the top.
 * Other balls are at the bottom.
 * Uses h_idx as a helper pillar and n+1 as the empty pillar.
 * Assumes h_idx is full and n+1 is empty.
 * Post-condition: p_idx is sorted, h_idx is restored, n+1 is empty.
 */
void sort_column(int p_idx, int c_l, int c_r, int h_idx) {
    int cnt = 0; // Number of balls with target colors
    for (int c : pillars[p_idx]) {
        if (is_in_range(c, c_l, c_r)) cnt++;
    }
    
    // Optimization: if already all target or none, structure is effectively 
    // sorted relative to the partition.
    if (cnt == 0 || cnt == m) return;

    // 1. Move cnt balls from helper (h_idx) to empty (n+1) to make space in helper.
    for(int k=0; k<cnt; ++k) record_move(h_idx, n+1);
    
    // 2. Move all balls from p_idx.
    // Target balls go to helper (h_idx).
    // Non-target balls go to empty (n+1).
    int current_m = pillars[p_idx].size();
    for(int k=0; k<current_m; ++k) {
        int c = pillars[p_idx].back();
        if (is_in_range(c, c_l, c_r)) {
            record_move(p_idx, h_idx);
        } else {
            record_move(p_idx, n+1);
        }
    }
    
    // 3. Move non-target balls from empty to p_idx.
    // Currently empty has [cnt balls from helper] at bottom, and [m-cnt non-target from p_idx] at top.
    // We move m-cnt balls.
    for(int k=0; k<m-cnt; ++k) record_move(n+1, p_idx);
    
    // 4. Move target balls from helper to p_idx.
    // Helper has [m-cnt original] at bottom, and [cnt target from p_idx] at top.
    // Moving them to p_idx places them on top.
    for(int k=0; k<cnt; ++k) record_move(h_idx, p_idx);
    
    // 5. Restore helper. Move cnt balls from empty to h_idx.
    // Empty has [cnt balls from helper].
    for(int k=0; k<cnt; ++k) record_move(n+1, h_idx);
}

// Recursive divide and conquer solver
void solve(int l, int r) {
    if (l == r) return;
    int mid = (l + r) >> 1;
    
    // We want to partition balls such that pillars l...mid contain colors l...mid (Good)
    // and pillars mid+1...r contain colors mid+1...r (Bad).
    
    int i = l;       // Current pillar in left set we are fixing
    int j = mid + 1; // Current pillar in right set we are sourcing from
    
    while (i <= mid && j <= r) {
        // Count bad balls in i (colors > mid)
        int cnt_bad_i = 0;
        for (int c : pillars[i]) if (c > mid) cnt_bad_i++;
        
        // Count good balls in j (colors <= mid)
        int cnt_good_j = 0;
        for (int c : pillars[j]) if (c <= mid) cnt_good_j++;
        
        if (cnt_bad_i == 0) {
            i++;
            continue;
        }
        if (cnt_good_j == 0) {
            j++;
            continue;
        }
        
        int k = min(cnt_bad_i, cnt_good_j);
        
        // Strategy: Swap k bad balls from i with k good balls from j.
        
        // 1. Sort i: put bad balls (range mid+1...r) at top. Use j as helper.
        sort_column(i, mid + 1, r, j);
        
        // 2. Sort j: put good balls (range l...mid) at top. Use i as helper.
        sort_column(j, l, mid, i);
        
        // 3. Perform the swap of top k balls.
        // Move k good balls from j to empty
        for(int step=0; step<k; ++step) record_move(j, n+1);
        // Move k bad balls from i to j
        for(int step=0; step<k; ++step) record_move(i, j);
        // Move k good balls from empty to i
        for(int step=0; step<k; ++step) record_move(n+1, i);
    }
    
    solve(l, mid);
    solve(mid + 1, r);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;
    
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int c; 
            cin >> c;
            pillars[i].push_back(c);
        }
    }
    
    solve(1, n);
    
    cout << ans.size() << "\n";
    for (const auto &mv : ans) {
        cout << mv.x << " " << mv.y << "\n";
    }
    
    return 0;
}