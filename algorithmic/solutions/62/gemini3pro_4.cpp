#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int n, m;
vector<int> pillars[55];
struct Op {
    int x, y;
};
vector<Op> ans;

void move_ball(int x, int y) {
    if (pillars[x].empty()) return; 
    pillars[y].push_back(pillars[x].back());
    pillars[x].pop_back();
    ans.push_back({x, y});
}

int get_type(int color, int mid) {
    return color <= mid ? 0 : 1;
}

// Sort pillar col so that all balls of type 'target_type' are on TOP.
// Uses helper pillar h and empty pillar E.
// color mapping: <= mid is 0, > mid is 1.
void sort_col(int col, int h, int E, int mid, int target_type) {
    int cnt_target = 0;
    for (int c : pillars[col]) {
        if (get_type(c, mid) == target_type) cnt_target++;
    }
    
    // Check if already sorted
    bool ok = true;
    for(int i=0; i<m; ++i) {
        int type = get_type(pillars[col][i], mid);
        if (i < m - cnt_target) { // Bottom part should be non-target
            if (type == target_type) ok = false;
        } else { // Top part should be target
            if (type != target_type) ok = false;
        }
    }
    if (ok) return;

    // Move cnt_target balls from h to E to reserve space
    for (int i = 0; i < cnt_target; ++i) move_ball(h, E);
    
    // Distribute col: target -> E, non-target -> h
    // Note: E has balls from h, so we append target balls on top of them.
    // h receives non-target balls on top of its remaining balls.
    for (int i = 0; i < m; ++i) {
        int c = pillars[col].back();
        int type = get_type(c, mid);
        if (type == target_type) move_ball(col, E);
        else move_ball(col, h);
    }
    
    // Now E has [h_top_balls] [col_target_balls]
    // h has [h_bottom] [col_non_target_balls]
    // col is empty
    
    // Move target balls back to col (they are on top of E)
    for (int i = 0; i < cnt_target; ++i) move_ball(E, col);
    
    // Move non-target balls back to col (they are on top of h)
    for (int i = 0; i < m - cnt_target; ++i) move_ball(h, col);
    
    // Restore h balls from E
    for (int i = 0; i < cnt_target; ++i) move_ball(E, h);
    
    // Currently col has Target at Bottom, Non-Target at Top.
    // We want Target at Top. Reverse the blocks.
    
    // Move Non-Target to h
    for (int i = 0; i < m - cnt_target; ++i) move_ball(col, h);
    // Move Target to E
    for (int i = 0; i < cnt_target; ++i) move_ball(col, E);
    // Move Non-Target to col
    for (int i = 0; i < m - cnt_target; ++i) move_ball(h, col);
    // Move Target to col
    for (int i = 0; i < cnt_target; ++i) move_ball(E, col);
}

void solve(int L, int R) {
    if (L == R) return;
    int mid = (L + R) >> 1;
    int E = n + 1;
    
    // Pre-sort
    for (int i = L; i <= R; ++i) {
        int c0 = 0;
        for (int c : pillars[i]) if (get_type(c, mid) == 0) c0++;
        int c1 = m - c0;
        int target = (c0 <= c1) ? 0 : 1; // Put minority on top
        int h = (i == L) ? L + 1 : L; 
        sort_col(i, h, E, mid, target);
    }
    
    int l = L, r = mid + 1;
    while (l <= mid && r <= R) {
        int u = l, v = r;
        
        // Count top consecutive balls
        int type_u = get_type(pillars[u].back(), mid);
        int cnt_u = 0;
        for (int i = m - 1; i >= 0; --i) {
            if (get_type(pillars[u][i], mid) == type_u) cnt_u++;
            else break;
        }
        
        int type_v = get_type(pillars[v].back(), mid);
        int cnt_v = 0;
        for (int i = m - 1; i >= 0; --i) {
            if (get_type(pillars[v][i], mid) == type_v) cnt_v++;
            else break;
        }
        
        // Check for pure pillars
        int c0_u = 0; for(int c: pillars[u]) if(get_type(c, mid) == 0) c0_u++;
        if (c0_u == m) { l++; continue; }
        int c1_v = 0; for(int c: pillars[v]) if(get_type(c, mid) == 1) c1_v++;
        if (c1_v == m) { r++; continue; }

        if (type_u == 1 && type_v == 0) {
            // Case 1: u exposes 1 (unwanted), v exposes 0 (unwanted). Swap tops.
            int k = min(cnt_u, cnt_v);
            for(int i=0; i<k; ++i) move_ball(u, E);
            for(int i=0; i<k; ++i) move_ball(v, u);
            for(int i=0; i<k; ++i) move_ball(E, v);
        } else if (type_u == 0 && type_v == 1) {
            // Case 2: u exposes 0 (wanted but min), v exposes 1 (wanted but min).
            // Swap to make them pure opposites, then swap columns.
            int k = min(cnt_u, cnt_v);
            for(int i=0; i<k; ++i) move_ball(u, E);
            for(int i=0; i<k; ++i) move_ball(v, u);
            for(int i=0; i<k; ++i) move_ball(E, v);
            
            // Check purity
            int u_pure1 = 1; 
            for(int c: pillars[u]) if(get_type(c, mid) == 0) u_pure1 = 0;
            if (u_pure1) {
                // u is Pure 1. Swap with v.
                for(int i=0; i<m; ++i) move_ball(u, E);
                for(int i=0; i<m; ++i) move_ball(v, u);
                for(int i=0; i<m; ++i) move_ball(E, v);
                // v is now Pure 1 (done), u is mixed.
                r++;
                continue;
            }
            int v_pure0 = 1;
            for(int c: pillars[v]) if(get_type(c, mid) == 1) v_pure0 = 0;
            if (v_pure0) {
                // v is Pure 0. Swap with u.
                for(int i=0; i<m; ++i) move_ball(u, E);
                for(int i=0; i<m; ++i) move_ball(v, u);
                for(int i=0; i<m; ++i) move_ball(E, v);
                // u is now Pure 0 (done), v is mixed.
                l++;
                continue;
            }
        } else if (type_u == 0 && type_v == 0) {
            // Case 3: u bad (0 top), v good (0 top).
            for(int i=0; i<cnt_u; ++i) move_ball(u, E);
            for(int i=0; i<cnt_v; ++i) move_ball(v, E);
            int move_k = min(m - cnt_u, cnt_v);
            for(int i=0; i<move_k; ++i) move_ball(u, v);
            for(int i=0; i<cnt_u + move_k; ++i) move_ball(E, u);
            for(int i=0; i<cnt_v - move_k; ++i) move_ball(E, v);
        } else { // 1, 1
            // Case 4: u good (1 top), v bad (1 top).
            for(int i=0; i<cnt_v; ++i) move_ball(v, E);
            int move_k = min(cnt_u, cnt_v);
            for(int i=0; i<move_k; ++i) move_ball(u, v);
            for(int i=0; i<move_k; ++i) move_ball(v, u); // From exposed 0s in v
            for(int i=0; i<cnt_v; ++i) move_ball(E, v);
        }
    }
    
    solve(L, mid);
    solve(mid + 1, R);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n >> m)) return 0;
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            pillars[i].push_back(c);
        }
    }
    
    solve(1, n);
    
    cout << ans.size() << "\n";
    for (auto p : ans) cout << p.x << " " << p.y << "\n";
    
    return 0;
}