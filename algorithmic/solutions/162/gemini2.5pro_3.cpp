#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <tuple>

const int N = 30;
int b[N][N];

struct Op {
    int r1, c1, r2, c2;
};

std::vector<Op> ops;

void do_swap(int r1, int c1, int r2, int c2) {
    if (ops.size() >= 10000) {
        return;
    }
    std::swap(b[r1][c1], b[r2][c2]);
    ops.push_back({r1, c1, r2, c2});
}

void solve() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j <= i; ++j) {
            std::cin >> b[i][j];
        }
    }

    // N-1 passes are theoretically sufficient to sort the pyramid.
    for (int i = 0; i < N - 1; ++i) {
        // Iterate from bottom to top to "bubble up" small numbers.
        for (int r = N - 2; r >= 0; --r) {
            // Serpentine scan for columns to help propagation.
            if (r % 2 == 0) {
                for (int c = 0; c <= r; ++c) {
                    int c1_r = r + 1, c1_c = c;
                    int c2_r = r + 1, c2_c = c + 1;
                    
                    int target_r, target_c;
                    if (b[c1_r][c1_c] < b[c2_r][c2_c]) {
                        target_r = c1_r;
                        target_c = c1_c;
                    } else {
                        target_r = c2_r;
                        target_c = c2_c;
                    }

                    if (b[r][c] > b[target_r][target_c]) {
                        do_swap(r, c, target_r, target_c);
                    }
                }
            } else {
                for (int c = r; c >= 0; --c) {
                    int c1_r = r + 1, c1_c = c;
                    int c2_r = r + 1, c2_c = c + 1;
                    
                    int target_r, target_c;
                    if (b[c1_r][c1_c] < b[c2_r][c2_c]) {
                        target_r = c1_r;
                        target_c = c1_c;
                    } else {
                        target_r = c2_r;
                        target_c = c2_c;
                    }

                    if (b[r][c] > b[target_r][target_c]) {
                        do_swap(r, c, target_r, target_c);
                    }
                }
            }
        }
    }

    std::cout << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.r1 << " " << op.c1 << " " << op.r2 << " " << op.c2 << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}