#include <bits/stdc++.h>
using namespace std;

using ll = long long;
const ll INF = 1e18;

struct Result {
    ll cost;
    int r, c;
    int aux1, aux2; // for construction specific: for A: s, b0; for B: h, w0
    int type; // 0 for A, 1 for B
};

ll x, y;

// ------------------------------------------------------------
// Construction A: vertical black lines, background white
// Applicable when b >= w-1
// ------------------------------------------------------------
Result solve_A(int b, int w) {
    Result best = {INF, -1, -1, -1, -1, 0};

    // Special case w == 1
    if (w == 1) {
        // We need b isolated black cells in a white grid, one white component.
        // Place black cells at (odd, odd) positions.
        // Requirement: ceil(r/2) * ceil(c/2) >= b.
        // Cost = y * r * c + (x - y) * b.
        // r must be at least 2 to keep white connected.
        for (int r = 2; r <= 100000; ++r) {
            int row_odd = (r + 1) / 2;
            // Needed odd columns count:
            int need_odd = (b + row_odd - 1) / row_odd;
            int c = 2 * need_odd - 1;
            if (c < 1) c = 1;
            if (1LL * r * c > 100000) continue;
            ll cost = y * r * c + (x - y) * b;
            if (cost < best.cost) {
                best = {cost, r, c, row_odd, need_odd, 0};
            }
        }
        return best;
    }

    // General case w >= 2
    int b0 = b - (w - 1);
    if (b0 < 0) return best; // not applicable, but caller checks

    for (int r = 1; r <= 100000; ++r) {
        ll max_c = 100000 / r;
        if (max_c < w) continue;
        int s_max = (max_c - w + 1) / w;
        if (s_max < 1) s_max = 1;
        for (int s = 1; s <= s_max; ++s) {
            // usable columns per strip
            int u_edge = s - 1;
            int u_mid = s - 2;
            // capacity: sum of independent set sizes of each strip
            ll cap = 0;
            // two edge strips
            cap += ((1LL * r * u_edge + 1) / 2) * 2;
            // interior strips
            if (w - 2 > 0) {
                cap += ((1LL * r * u_mid + 1) / 2) * (w - 2);
            }
            if (cap >= b0) {
                int c = w * s + w - 1;
                ll cost = y * r * c + (x - y) * (1LL * (w - 1) * r + b0);
                if (cost < best.cost) {
                    best = {cost, r, c, s, b0, 0};
                }
                break; // for this r, increasing s only increases cost
            }
        }
    }
    return best;
}

// ------------------------------------------------------------
// Construction B: horizontal white lines, background black
// Applicable when w >= b-1
// ------------------------------------------------------------
Result solve_B(int b, int w) {
    Result best = {INF, -1, -1, -1, -1, 1};

    // Special case b == 1
    if (b == 1) {
        // symmetric to w==1 in A
        for (int c = 2; c <= 100000; ++c) {
            int col_odd = (c + 1) / 2;
            int need_odd = (w + col_odd - 1) / col_odd;
            int r = 2 * need_odd - 1;
            if (r < 1) r = 1;
            if (1LL * r * c > 100000) continue;
            ll white_cells = w;
            ll black_cells = r * c - white_cells;
            ll cost = x * black_cells + y * white_cells;
            if (cost < best.cost) {
                best = {cost, r, c, col_odd, need_odd, 1};
            }
        }
        return best;
    }

    // General case b >= 2
    int w0 = w - (b - 1);
    if (w0 < 0) return best;

    for (int c = 1; c <= 100000; ++c) {
        ll max_r = 100000 / c;
        if (max_r < b) continue;
        int h_max = (max_r - (b - 1)) / b;
        if (h_max < 1) h_max = 1;
        for (int h = 1; h <= h_max; ++h) {
            int u_edge = h - 1;
            int u_mid = h - 2;
            ll cap = 0;
            // two edge black strips
            cap += ((1LL * c * u_edge + 1) / 2) * 2;
            // interior black strips
            if (b - 2 > 0) {
                cap += ((1LL * c * u_mid + 1) / 2) * (b - 2);
            }
            if (cap >= w0) {
                int r = b * h + (b - 1);
                ll white_cells = 1LL * (b - 1) * c + w0;
                ll black_cells = 1LL * r * c - white_cells;
                ll cost = x * black_cells + y * white_cells;
                if (cost < best.cost) {
                    best = {cost, r, c, h, w0, 1};
                }
                break;
            }
        }
    }
    return best;
}

// ------------------------------------------------------------
// Generate grid for Construction A
// ------------------------------------------------------------
vector<string> generate_A(int r, int c, int w, int s, int b0) {
    vector<string> grid(r, string(c, '.'));
    // draw vertical black lines
    for (int k = 1; k <= w - 1; ++k) {
        int col = k * (s + 1) - 1; // 0-based: column index = k*(s+1) - 1
        for (int i = 0; i < r; ++i) grid[i][col] = '@';
    }

    // place isolated black cells
    // collect usable columns in each strip
    vector<int> usable_cols;
    // strip 1 (leftmost)
    for (int col = 0; col < s - 1; ++col) usable_cols.push_back(col);
    // interior strips
    for (int idx = 2; idx <= w - 1; ++idx) {
        int start = (idx - 1) * (s + 1);
        for (int col = start + 1; col < start + s - 1; ++col) usable_cols.push_back(col);
    }
    // strip w (rightmost)
    int start_last = (w - 1) * (s + 1);
    for (int col = start_last + 1; col < start_last + s; ++col) usable_cols.push_back(col);

    int placed = 0;
    for (int col : usable_cols) {
        for (int row = 0; row < r; ++row) {
            if ((row + col