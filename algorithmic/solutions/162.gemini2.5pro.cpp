#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

const int N = 30;

struct Operation {
    int r1, c1, r2, c2;
};

std::vector<std::vector<int>> b(N);
std::vector<Operation> ops;

void apply_swap(int r1, int c1, int r2, int c2) {
    std::swap(b[r1][c1], b[r2][c2]);
    ops.push_back({r1, c1, r2, c2});
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    for (int i = 0; i < N; ++i) {
        b[i].resize(i + 1);
        for (int j = 0; j <= i; ++j) {
            std::cin >> b[i][j];
        }
    }

    int max_passes = N + 5; 

    for (int i = 0; i < max_passes; ++i) {
        if (ops.size() >= 10000) {
            break;
        }

        bool changed = false;

        for (int r = N - 2; r >= 0; --r) {
            if (i % 2 == 0) {
                for (int c = 0; c <= r; ++c) {
                    if (ops.size() >= 10000) break;
                    
                    int p_val = b[r][c];
                    int c1_val = b[r+1][c];
                    int c2_val = b[r+1][c+1];

                    if (c1_val < p_val && c1_val <= c2_val) {
                        apply_swap(r, c, r + 1, c);
                        changed = true;
                    } else if (c2_val < p_val) {
                        apply_swap(r, c, r + 1, c + 1);
                        changed = true;
                    }
                }
            } else {
                for (int c = r; c >= 0; --c) {
                    if (ops.size() >= 10000) break;
                    
                    int p_val = b[r][c];
                    int c1_val = b[r+1][c];
                    int c2_val = b[r+1][c+1];

                    if (c1_val < p_val && c1_val <= c2_val) {
                        apply_swap(r, c, r + 1, c);
                        changed = true;
                    } else if (c2_val < p_val) {
                        apply_swap(r, c, r + 1, c + 1);
                        changed = true;
                    }
                }
            }
            if (ops.size() >= 10000) break;
        }

        if (!changed) {
            break;
        }
    }

    std::cout << ops.size() << std::endl;
    for (const auto& op : ops) {
        std::cout << op.r1 << " " << op.c1 << " " << op.r2 << " " << op.c2 << std::endl;
    }

    return 0;
}