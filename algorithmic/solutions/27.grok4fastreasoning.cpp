#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    long long k_sim = (long long)n + m - 1;
    int best_b_row = -1;
    long long max_k_row = 0;
    for (int bb = 1; bb <= n && (long long)bb * bb <= m; ++bb) {
        int nums = bb;
        if (nums > n) continue;
        long long nnon = n - nums;
        long long thisk;
        if (bb == 1) {
            thisk = (long long)m + nnon;
        } else {
            long long maxn = (long long)bb * bb;
            long long ann = min(nnon, maxn);
            thisk = (long long)m + ann * (long long)bb;
        }
        if (thisk > max_k_row) {
            max_k_row = thisk;
            best_b_row = bb;
        }
    }
    int best_b_col = -1;
    long long max_k_col = 0;
    for (int bb = 1; bb <= m && (long long)bb * bb <= n; ++bb) {
        int nums = bb;
        if (nums > m) continue;
        long long nnon = m - nums;
        long long thisk;
        if (bb == 1) {
            thisk = (long long)n + nnon;
        } else {
            long long maxn = (long long)bb * bb;
            long long ann = min(nnon, maxn);
            thisk = (long long)n + ann * (long long)bb;
        }
        if (thisk > max_k_col) {
            max_k_col = thisk;
            best_b_col = bb;
        }
    }
    long long overall_max = max({max_k_row, max_k_col, k_sim});
    vector<pair<int, int>> points;
    bool use_row = (max_k_row == overall_max);
    bool use_col = (!use_row && max_k_col == overall_max);
    bool use_simple = (!use_row && !use_col);
    int chosen_b = 0;
    if (use_row) {
        chosen_b = best_b_row;
        int b = chosen_b;
        vector<int> block_start(b + 1, 0);
        int current_col = 1;
        for (int z = 0; z < b; ++z) {
            block_start[z] = current_col;
            int sz = m / b + (z < m % b ? 1 : 0);
            current_col += sz;
        }
        block_start[b] = current_col;
        // special rows 1 to b
        for (int sr = 1; sr <= b; ++sr) {
            int z = sr - 1;
            int startc = block_start[z];
            int sz = block_start[z + 1] - startc;
            for (int off = 0; off < sz; ++off) {
                points.emplace_back(sr, startc + off);
            }
        }
        // non-special
        long long num_non_gen;
        if (b == 1) {
            num_non_gen = (long long)n - b;
        } else {
            num_non_gen = min((long long)n - b, (long long)b * b);
        }
        int first_non_r = b + 1;
        for (long long ii = 0; ii < num_non_gen; ++ii) {
            int r = first_non_r + ii;
            if (r > n) break;
            int x = ii / b;
            int y = ii % b;
            for (int z = 0; z < b; ++z) {
                long long temp = (long long)x + (long long)y * z;
                int label = temp % b;
                if (label < 0) label += b;
                int c = block_start[z] + label;
                points.emplace_back(r, c);
            }
        }
    } else if (use_col) {
        chosen_b = best_b_col;
        int b = chosen_b;
        vector<int> row_block_start(b + 1, 0);
        int current_row = 1;
        for (int z = 0; z < b; ++z) {
            row_block_start[z] = current_row;
            int sz = n / b + (z < n % b ? 1 : 0);
            current_row += sz;
        }
        row_block_start[b] = current_row;
        // special columns 1 to b
        for (int sc = 1; sc <= b; ++sc) {
            int z = sc - 1;
            int startr = row_block_start[z];
            int sz = row_block_start[z + 1] - startr;
            for (int off = 0; off < sz; ++off) {
                points.emplace_back(startr + off, sc);
            }
        }
        // non-special columns
        long long num_non_gen;
        if (b == 1) {
            num_non_gen = (long long)m - b;
        } else {
            num_non_gen = min((long long)m - b, (long long)b * b);
        }
        int first_non_c = b + 1;
        for (long long ii = 0; ii < num_non_gen; ++ii) {
            int c = first_non_c + ii;
            if (c > m) break;
            int x = ii / b;
            int y = ii % b;
            for (int z = 0; z < b; ++z) {
                long long temp = (long long)x + (long long)y * z;
                int label = temp % b;
                if (label < 0) label += b;
                int r = row_block_start[z] + label;
                points.emplace_back(r, c);
            }
        }
    } else { // simple
        if (n <= m) {
            // fill row 1
            for (int c = 1; c <= m; ++c) {
                points.emplace_back(1, c);
            }
            // rows 2 to n, col 1
            for (int r = 2; r <= n; ++r) {
                points.emplace_back(r, 1);
            }
        } else {
            // fill col 1
            for (int r = 1; r <= n; ++r) {
                points.emplace_back(r, 1);
            }
            // cols 2 to m, row 1
            for (int c = 2; c <= m; ++c) {
                points.emplace_back(1, c);
            }
        }
    }
    cout << points.size() << endl;
    for (auto& p : points) {
        cout << p.first << " " << p.second << endl;
    }
    return 0;
}