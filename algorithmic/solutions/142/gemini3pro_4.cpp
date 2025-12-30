#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global variables to store the state of poles
int n, m;
vector<int> poles[55]; // Poles 1 to n+1. Index 0 unused.
vector<pair<int, int>> ans; // To store the sequence of operations

// Function to perform a move
void op(int x, int y) {
    if (poles[x].empty()) return; // Should not happen with correct logic
    int c = poles[x].back();
    poles[x].pop_back();
    poles[y].push_back(c);
    ans.push_back({x, y});
}

// Helper to determine if a color belongs to the "small" set
bool is_small(int color, int mid) {
    return color <= mid;
}

// Recursive function to solve for color range [l, r]
void solve(int l, int r) {
    if (l == r) return;
    int mid = (l + r) / 2;

    // Identify poles belonging to the left (small colors) and right (large colors) sets
    vector<int> left_poles, right_poles;
    for (int i = l; i <= mid; ++i) left_poles.push_back(i);
    for (int i = mid + 1; i <= r; ++i) right_poles.push_back(i);

    int empty_pole = n + 1;

    // Iterate through pairs of poles to partition balls
    int li = 0, ri = 0;
    while (li < left_poles.size() && ri < right_poles.size()) {
        int u = left_poles[li];
        int v = right_poles[ri];

        // Count wrongly placed balls to check if current poles need processing
        int u_large = 0;
        for (int c : poles[u]) if (!is_small(c, mid)) u_large++;
        
        int v_small = 0;
        for (int c : poles[v]) if (is_small(c, mid)) v_small++;

        // If u is clean, move to next left pole
        if (u_large == 0) {
            li++;
            continue;
        }
        // If v is clean, move to next right pole
        if (v_small == 0) {
            ri++;
            continue;
        }

        // Calculate depth of the first WRONG ball (which is buried under correct ones)
        // g_u: number of correct Small balls on top of u
        int g_u = 0;
        for (int k = poles[u].size() - 1; k >= 0; --k) {
            if (is_small(poles[u][k], mid)) g_u++;
            else break;
        }

        // b_v: number of correct Large balls on top of v
        int b_v = 0;
        for (int k = poles[v].size() - 1; k >= 0; --k) {
            if (!is_small(poles[v][k], mid)) b_v++;
            else break;
        }

        // Choose strategy based on how deep we need to dig
        if (g_u + b_v + 1 <= m) {
            // Strategy 1: Simple Dig & Swap
            // Used when correct prefixes are shallow enough to fit in buffer
            
            // Move correct tops to buffer
            for (int k = 0; k < g_u; ++k) op(u, empty_pole);
            for (int k = 0; k < b_v; ++k) op(v, empty_pole);
            
            // Perform 1 swap: Top of u is Large (wrong), Top of v is Small (wrong)
            op(u, empty_pole); // Move Large from u to temp
            op(v, u);          // Move Small from v to u
            op(empty_pole, v); // Move Large from temp to v

            // Restore correct tops
            for (int k = 0; k < b_v; ++k) op(empty_pole, v);
            for (int k = 0; k < g_u; ++k) op(empty_pole, u);
            
        } else {
            // Strategy 2: Bulk Move (Hard Case)
            // Used when correct prefixes are too deep. Requires flipping stacks.
            
            // 1. Move all balls from u to empty_pole. 
            // This reverses u, so correct Small balls (top) go to bottom of empty_pole.
            // Wrong Large balls (deep in u) become exposed on top of empty_pole.
            int sz_u = poles[u].size();
            for (int k = 0; k < sz_u; ++k) op(u, empty_pole);

            // 2. Move the correct Large prefix from v to u.
            // This exposes the wrong Small balls in v.
            for (int k = 0; k < b_v; ++k) op(v, u);

            // 3. Swap loop
            // empty_pole has Large balls on top. v has Small balls on top.
            while (true) {
                if (poles[empty_pole].empty()) break;
                int ball_e = poles[empty_pole].back();
                if (is_small(ball_e, mid)) break; // Found a Small ball, stop (prefix of Large exhausted)

                if (poles[v].empty()) break;
                int ball_v = poles[v].back();
                if (!is_small(ball_v, mid)) break; // Found a Large ball, stop (prefix of Small exhausted)
                
                // Swap logic:
                op(v, u);          // Small ball from v goes to u (on top of b_v Large balls)
                op(empty_pole, v); // Large ball from empty_pole goes to v
            }
            
            // 4. Restore u
            // Move remaining balls from empty_pole (which are Small) back to u
            while (!poles[empty_pole].empty()) {
                op(empty_pole, u);
            }
            // Now u contains: [b_v Large balls] [Swapped Small balls] [Original Small balls]
            // We need to move the [b_v Large balls] at the bottom of u back to v.

            // 5. Cleanup u
            // Count all Small balls currently in u (they are all on top)
            int s_cnt = 0;
            for (int k = poles[u].size() - 1; k >= 0; --k) {
                if (is_small(poles[u][k], mid)) s_cnt++;
                else break;
            }
            
            // Move all Small balls to empty_pole to expose the Large balls at bottom
            for(int k=0; k<s_cnt; ++k) op(u, empty_pole);
            
            // Move the Large balls to v
            while(!poles[u].empty()) op(u, v); 
            
            // Restore Small balls to u
            while(!poles[empty_pole].empty()) op(empty_pole, u); 
        }
    }
    
    // Recurse
    solve(l, mid);
    solve(mid + 1, r);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n >> m)) return 0;

    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            poles[i].push_back(c);
        }
    }

    solve(1, n);

    cout << ans.size() << "\n";
    for (auto p : ans) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}