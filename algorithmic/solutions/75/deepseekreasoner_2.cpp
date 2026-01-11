#include <bits/stdc++.h>
using namespace std;

struct Params {
    int type; // 1: r=1 alternating, 2: white-base, 3: black-base
    int r, c;
    int b, w; // original b,w
    int k;    // for type2: k = b - (w-1), for type3: k = w - (b-1)
    int cost;
};

const int INF = 2e9;

int ceil_div(int a, int b) {
    return (a + b - 1) / b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    cin >> b >> w >> x >> y;

    Params best;
    best.cost = INF;

    // Case 1: r=1 alternating (only if |b-w| <= 1)
    if (abs(b - w) <= 1) {
        int c = b + w;
        int cost = x * b + y * w;
        if (cost < best.cost) {
            best = {1, 1, c, b, w, 0, cost};
        }
    }

    // Case 2: white-base (requires b >= w-1)
    if (b >= w - 1) {
        int k = b - (w - 1);
        for (int r = 2; r <= 100000; ++r) {
            int c;
            if (k == 0) {
                c = 2 * w - 1;
            } else {
                c = 2 * w + ceil_div(2 * k, r);
            }
            if (c > 100000) break;
            if (1LL * r * c > 100000) break;
            int black = (w - 1) * r + k;
            int white = r * c - black;
            int cost = x * black + y * white;
            if (cost < best.cost) {
                best = {2, r, c, b, w, k, cost};
            }
            // If k == 0, increasing r only increases cost (since c fixed), so break.
            if (k == 0) break;
        }
    }

    // Case 3: black-base (requires w >= b-1)
    if (w >= b - 1) {
        int k = w - (b - 1);
        for (int r = 2; r <= 100000; ++r) {
            int c;
            if (k == 0) {
                c = 2 * b - 1;
            } else {
                c = 2 * b + ceil_div(2 * k, r);
            }
            if (c > 100000) break;
            if (1LL * r * c > 100000) break;
            int white = (b - 1) * r + k;
            int black = r * c - white;
            int cost = x * black + y * white;
            if (cost < best.cost) {
                best = {3, r, c, b, w, k, cost};
            }
            if (k == 0) break;
        }
    }

    // Construction
    int r = best.r, c = best.c;
    cout << r << " " << c << "\n";

    if (best.type == 1) {
        // alternating single row
        string row;
        if (b == w) {
            for (int i = 0; i < c; ++i)
                row += (i % 2 == 0 ? '@' : '.');
        } else if (b > w) { // b = w+1
            for (int i = 0; i < c; ++i)
                row += (i % 2 == 0 ? '@' : '.');
        } else { // w = b+1
            for (int i = 0; i < c; ++i)
                row += (i % 2 == 0 ? '.' : '@');
        }
        cout << row << "\n";
        return 0;
    }

    vector<string> grid(r, string(c, '.')); // default white
    if (best.type == 2) {
        // white-base: barriers are black columns
        int w_cnt = best.w;
        int k = best.k;
        // place barriers at columns 2,4,...,2*(w_cnt-1)
        for (int col = 2; col <= 2*(w_cnt-1); col += 2) {
            for (int row = 0; row < r; ++row)
                grid[row][col-1] = '@'; // 0-indexed
        }
        // place k isolated black tiles in the last white strip
        // last white strip columns from 2*w_cnt - 1 to c (1-indexed)
        int start_col = 2 * w_cnt - 1; // 1-indexed, first column of last strip
        // we will use columns from start_col (1-indexed) to c, but avoid first column for safety
        int first_avail = start_col; // actually we can use start_col, but to avoid adjacency to barrier, we skip start_col? barrier is at start_col-1.
        // Actually, start_col is odd, barrier at start_col-1 is even. So start_col is not adjacent horizontally? start_col - (start_col-1) =1, so they are adjacent. So we should not use start_col.
        // So we use columns from start_col+1 to c.
        int col_begin = start_col; // 1-indexed, we will use 0-indexed in code
        // Convert to 0-indexed: columns from col_begin to c-1.
        // But we want to avoid col_begin because it's adjacent to barrier? Let's avoid it.
        int avoid = 1; // avoid first column of the strip
        // Collect candidate cells with (i+j) % 2 == 0 in the region [0, r) x [col_begin+avoid, c)
        vector<pair<int,int>> candidates;
        for (int i = 0; i < r; ++i) {
            for (int j = col_begin + avoid; j < c; ++j) {
                if ((i + j) % 2 == 0) {
                    candidates.emplace_back(i, j);
                }
            }
        }
        // Take first k
        for (int idx = 0; idx < k && idx < (int)candidates.size(); ++idx) {
            int i = candidates[idx].first;
            int j = candidates[idx].second;
            grid[i][j] = '@';
        }
        // Output grid
        for (const string& row : grid)
            cout << row << "\n";
    } else { // type 3: black-base
        int b_cnt = best.b;
        int k = best.k; // k = w - (b-1)
        // Initialize all black
        grid.assign(r, string(c, '@'));
        // place white barriers at columns 2,4,...,2*(b_cnt-1)
        for (int col = 2; col <= 2*(b_cnt-1); col += 2) {
            for (int row = 0; row < r; ++row)
                grid[row][col-1] = '.';
        }
        // place k isolated white tiles in the last black strip
        int start_col = 2 * b_cnt - 1;
        int col_begin = start_col; // 1-indexed
        int avoid = 1; // avoid first column adjacent to barrier
        vector<pair<int,int>> candidates;
        for (int i = 0; i < r; ++i) {
            for (int j = col_begin + avoid; j < c; ++j) {
                if ((i + j) % 2 == 0) {
                    candidates.emplace_back(i, j);
                }
            }
        }
        for (int idx = 0; idx < k && idx < (int)candidates.size(); ++idx) {
            int i = candidates[idx].first;
            int j = candidates[idx].second;
            grid[i][j] = '.';
        }
        for (const string& row : grid)
            cout << row << "\n";
    }

    return 0;
}