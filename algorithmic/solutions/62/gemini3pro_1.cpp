#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables for problem state
int n, m;
// Pillars are 1-indexed, p[n+1] is initially empty
vector<vector<int>> p;
struct Move {
    int x, y;
};
vector<Move> moves;

// Helper function to perform a move and record it
void op(int x, int y) {
    moves.push_back({x, y});
    p[y].push_back(p[x].back());
    p[x].pop_back();
}

// Swap top k elements between pillar x and pillar y using empty pillar E
// Assumes x and y have at least k elements and E is empty.
void swap_tops(int x, int y, int k, int E) {
    for(int i=0; i<k; ++i) op(x, E);
    for(int i=0; i<k; ++i) op(y, x);
    for(int i=0; i<k; ++i) op(E, y);
}

// Sort column x using helper column y and empty column E.
// The goal is to move all "target" balls in x to the bottom, and "other" balls to the top.
// A ball is "target" if (ball_color <= mid) == keep_small.
// y is assumed to be full (m balls), E is assumed to be empty.
// After the operation, x is sorted, y is restored to full (though order of top elements may change), and E is empty.
void sort_column(int x, int y, int E, int mid, bool keep_small) {
    int c_target = 0;
    for(int c : p[x]) {
        bool is_small = (c <= mid);
        if(is_small == keep_small) c_target++;
    }
    int c_other = m - c_target;
    if(c_other == 0) return; // Already pure/sorted

    // Move c_other balls from y to E to make space in y and fill E partially
    for(int i=0; i<c_other; ++i) op(y, E);

    // Distribute balls from x: target balls to E, other balls to y.
    // E currently has c_other balls, space m - c_other = c_target.
    // y currently has m - c_other balls, space c_other.
    // This fits exactly.
    int initial_x_sz = p[x].size();
    for(int i=0; i<initial_x_sz; ++i) {
        int c = p[x].back();
        bool is_small = (c <= mid);
        bool is_target = (is_small == keep_small);
        
        if(is_target) {
            op(x, E);
        } else {
            op(x, y);
        }
    }

    // Now x is empty.
    // E contains: Bottom [balls from y], Top [target balls from x].
    // y contains: Bottom [remaining y], Top [other balls from x].
    
    // Move all balls from E to x.
    // x will get: Bottom [target balls from x (reversed)], Top [balls from y].
    while(!p[E].empty()) {
        op(E, x);
    }
    
    // Now swap the top c_other balls between x and y.
    // x top has balls that originally came from y. We want them back in y.
    // y top has balls that originally came from x (others). We want them in x top.
    swap_tops(x, y, c_other, E);
    
    // Final state:
    // x: Bottom [target balls], Top [other balls]. (Sorted as desired)
    // y: Bottom [remaining y], Top [balls returned from x]. (Restored count m)
    // E: Empty.
}

// Divide and Conquer solution
// Range of pillars [L, R] corresponds to colors [c_min, c_max].
void solve(int L, int R, int c_min, int c_max) {
    if(L == R) return;
    int mid_c = (c_min + c_max) >> 1;
    // Number of colors in the left set [c_min, mid_c]
    int left_colors_count = mid_c - c_min + 1;
    // The pillars corresponding to these colors
    int M = L + left_colors_count - 1;
    int E = n + 1;

    // Partition step: Move all balls with color <= mid_c to pillars L...M
    // and balls with color > mid_c to pillars M+1...R.
    
    // Iterate through left pillars i
    for(int i = L; i <= M; ++i) {
        // Calculate how many balls in i belong to the right set (bad balls)
        int bad = 0;
        for(int c : p[i]) if(c > mid_c) bad++;
        
        int j = M + 1;
        while(bad > 0) {
            // Find a pillar j in the right set that has balls belonging to the left set (good balls)
            while(j <= R) {
                int cnt = 0;
                for(int c : p[j]) if(c <= mid_c) cnt++;
                if(cnt > 0) break;
                j++;
            }
            // Logic guarantees such j exists if bad > 0
            
            // Sort pillar i so that small balls (target) are at bottom, large (bad) at top.
            // Use j as helper.
            sort_column(i, j, E, mid_c, true); 
            
            // Sort pillar j so that large balls (target for j) are at bottom, small (good) at top.
            // Use i as helper.
            sort_column(j, i, E, mid_c, false); 
            
            // Now i has 'bad' balls on top. j has 'good' balls on top.
            // Swap them.
            int goods_in_j = 0;
            for(int c : p[j]) if(c <= mid_c) goods_in_j++;
            
            int k = min(bad, goods_in_j);
            swap_tops(i, j, k, E);
            bad -= k;
        }
    }

    solve(L, M, c_min, mid_c);
    solve(M+1, R, mid_c+1, c_max);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if(!(cin >> n >> m)) return 0;
    p.resize(n + 2);
    for(int i=1; i<=n; ++i) {
        for(int j=0; j<m; ++j) {
            int c; cin >> c;
            p[i].push_back(c);
        }
    }

    solve(1, n, 1, n);

    cout << moves.size() << "\n";
    for(auto &mv : moves) {
        cout << mv.x << " " << mv.y << "\n";
    }
    return 0;
}