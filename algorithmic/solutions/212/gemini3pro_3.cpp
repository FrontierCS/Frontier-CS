#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>

using namespace std;

// Function to calculate the cost of a given sequence of rows
long long get_cost(const vector<int>& p, int n, int m, int L, int R) {
    long long current_cost = 0;
    // Initial row p[0] traversal: from (p[0], L) to (p[0], R)
    current_cost += (R - L);
    
    // Sides: 0 for Left (at col L), 1 for Right (at col R)
    // After traversing p[0] L->R, we are at Right side.
    int current_side = 1; 
    
    for (size_t i = 0; i < p.size() - 1; ++i) {
        int u = p[i];
        int v = p[i+1];
        int dist = abs(u - v);
        
        if (dist == 0) return 2e18; // Should not happen in valid permutation
        
        long long move_cost = 0;
        
        if (dist == 1) {
            // Adjacent move is always possible directly (cost 1)
            // It might be possible via margin too, but direct is always cheaper or equal.
            // Exception: if L=1 and R=m, only direct is possible.
            move_cost = 1;
        } else {
            // Non-adjacent move requires margin usage
            if (current_side == 1) { // At Right
                if (R == m) return 2e18; // Impossible to use right margin
                move_cost = (long long)dist + 2 * (m - R);
            } else { // At Left
                if (L == 1) return 2e18; // Impossible to use left margin
                move_cost = (long long)dist + 2 * (L - 1);
            }
        }
        
        current_cost += move_cost;
        current_cost += (R - L); // Traversal of next row v
        
        // Toggle side: traversing v swaps the side
        current_side = 1 - current_side;
    }
    return current_cost;
}

// Function to print the path coordinates
void print_path(const vector<int>& p, int Sx, int m, int L, int R) {
    vector<pair<int, int>> path;
    
    // First row p[0] (which is Sx)
    // Start at (Sx, L), go to (Sx, R)
    for (int y = L; y <= R; ++y) {
        path.push_back({Sx, y});
    }
    
    int current_side = 1; // 1 = Right (at R), 0 = Left (at L)
    int cx = Sx;
    int cy = R;
    
    for (size_t i = 0; i < p.size() - 1; ++i) {
        int u = p[i];
        int v = p[i+1];
        int dist = abs(u - v);
        
        // Move from u to v
        if (dist == 1) {
            // Direct move
            // (u, cy) -> (v, cy)
            path.push_back({v, cy});
            cx = v;
        } else {
            // Margin move
            if (current_side == 1) { // At Right, use col m
                // (u, R) -> (u, m) -> (v, m) -> (v, R)
                for (int y = R + 1; y <= m; ++y) path.push_back({cx, y});
                int step = (v > u) ? 1 : -1;
                for (int r = u + step; r != v + step; r += step) path.push_back({r, m});
                for (int y = m - 1; y >= R; --y) path.push_back({v, y});
                cx = v;
                cy = R;
            } else { // At Left, use col 1
                // (u, L) -> (u, 1) -> (v, 1) -> (v, L)
                for (int y = L - 1; y >= 1; --y) path.push_back({cx, y});
                int step = (v > u) ? 1 : -1;
                for (int r = u + step; r != v + step; r += step) path.push_back({r, 1});
                for (int y = 2; y <= L; ++y) path.push_back({v, y});
                cx = v;
                cy = L;
            }
        }
        
        // Traverse row v
        if (current_side == 1) { 
            // Entered v at Right, go to Left
            for (int y = R - 1; y >= L; --y) path.push_back({v, y});
            cy = L;
            current_side = 0;
        } else {
            // Entered v at Left, go to Right
            for (int y = L + 1; y <= R; ++y) path.push_back({v, y});
            cy = R;
            current_side = 1;
        }
    }
    
    cout << path.size() << "\n";
    for (auto pp : path) {
        cout << pp.first << " " << pp.second << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n, m, L, R, Sx, Sy, Lq, s;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];
    
    // Check if Sx is in q
    int start_idx = 0;
    for (int i = 0; i < Lq; ++i) {
        if (q[i] == Sx) {
            if (i != 0) {
                // Sx must be visited first. If it's in q but not the first required element,
                // it's a contradiction because q defines subsequence order.
                cout << "NO\n";
                return 0;
            }
            start_idx = 1;
            break;
        }
    }
    
    // Base Path Construction: Minimal path respecting q
    vector<int> base_p;
    base_p.push_back(Sx);
    vector<bool> vis(n + 1, false);
    vis[Sx] = true;
    
    int curr = Sx;
    for (int i = start_idx; i < Lq; ++i) {
        int target = q[i];
        int step = (target > curr) ? 1 : -1;
        while (curr != target) {
            curr += step;
            if (!vis[curr]) {
                base_p.push_back(curr);
                vis[curr] = true;
            }
        }
    }
    
    // Identify unvisited rows
    vector<int> U_top, U_bot;
    int min_p = n + 1, max_p = 0;
    for (int x : base_p) {
        if (x < min_p) min_p = x;
        if (x > max_p) max_p = x;
    }
    
    // Rows above max visited
    for (int r = max_p + 1; r <= n; ++r) if (!vis[r]) U_top.push_back(r);
    // Rows below min visited
    for (int r = 1; r < min_p; ++r) if (!vis[r]) U_bot.push_back(r);
    
    // Sort U_bot descending so inserting looks like extension from min_p downwards
    sort(U_bot.begin(), U_bot.end(), greater<int>());
    // U_top is already ascending
    
    // Generate candidates by inserting U_top
    vector<vector<int>> candidates;
    candidates.push_back(base_p);
    
    if (!U_top.empty()) {
        vector<vector<int>> next_candidates;
        for (const auto& p : candidates) {
            // Try inserting U_top after every position in current path
            for (size_t i = 0; i < p.size(); ++i) {
                // Try two directions: Ascending or Descending
                for (int dir = 0; dir < 2; ++dir) {
                    vector<int> block = U_top;
                    if (dir == 1) reverse(block.begin(), block.end());
                    
                    vector<int> new_p;
                    new_p.reserve(p.size() + block.size());
                    for (size_t k = 0; k <= i; ++k) new_p.push_back(p[k]);
                    for (int x : block) new_p.push_back(x);
                    for (size_t k = i + 1; k < p.size(); ++k) new_p.push_back(p[k]);
                    next_candidates.push_back(new_p);
                }
            }
        }
        candidates = next_candidates;
    }
    
    // Generate candidates by inserting U_bot
    if (!U_bot.empty()) {
        vector<vector<int>> next_candidates;
        for (const auto& p : candidates) {
            for (size_t i = 0; i < p.size(); ++i) {
                for (int dir = 0; dir < 2; ++dir) {
                    vector<int> block = U_bot; 
                    if (dir == 1) reverse(block.begin(), block.end());
                    
                    vector<int> new_p;
                    new_p.reserve(p.size() + block.size());
                    for (size_t k = 0; k <= i; ++k) new_p.push_back(p[k]);
                    for (int x : block) new_p.push_back(x);
                    for (size_t k = i + 1; k < p.size(); ++k) new_p.push_back(p[k]);
                    next_candidates.push_back(new_p);
                }
            }
        }
        candidates = next_candidates;
    }
    
    long long min_cost = 2e18;
    vector<int> best_p;
    
    // Evaluate all candidates
    for (const auto& p : candidates) {
        long long c = get_cost(p, n, m, L, R);
        if (c < min_cost) {
            min_cost = c;
            best_p = p;
        }
    }
    
    if (min_cost >= 2e18) {
        cout << "NO\n";
    } else {
        cout << "YES\n";
        print_path(best_p, Sx, m, L, R);
    }
    
    return 0;
}