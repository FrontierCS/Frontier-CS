#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <tuple>

const int N = 30;
const int TOTAL_BALLS = N * (N + 1) / 2;
const int MAX_OPS = 10000;

std::vector<std::vector<int>> b(N);
std::vector<std::pair<int, int>> pos(TOTAL_BALLS);
std::vector<std::tuple<int, int, int, int>> history;

bool limit_reached = false;

bool do_swap(int r1, int c1, int r2, int c2) {
    if (history.size() >= MAX_OPS) {
        limit_reached = true;
        return false;
    }

    int val1 = b[r1][c1];
    int val2 = b[r2][c2];

    std::swap(b[r1][c1], b[r2][c2]);
    std::swap(pos[val1], pos[val2]);
    
    history.emplace_back(r1, c1, r2, c2);
    return true;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    for (int i = 0; i < N; ++i) {
        b[i].resize(i + 1);
        for (int j = 0; j <= i; ++j) {
            std::cin >> b[i][j];
            pos[b[i][j]] = {i, j};
        }
    }

    int max_passes = N - 1;
    for (int i = 0; i < max_passes; ++i) {
        bool swapped_in_pass = false;
        if (i % 2 == 0) {
            for (int r = N - 2; r >= 0; --r) {
                for (int c = 0; c <= r; ++c) {
                    int p_val = b[r][c];
                    int l_val = b[r + 1][c];
                    int r_val = b[r + 1][c + 1];

                    if (l_val < r_val) {
                        if (p_val > l_val) {
                            swapped_in_pass |= do_swap(r, c, r + 1, c);
                        }
                    } else {
                        if (p_val > r_val) {
                            swapped_in_pass |= do_swap(r, c, r + 1, c + 1);
                        }
                    }
                    if (limit_reached) break;
                }
                if (limit_reached) break;
            }
        } else {
            for (int r = N - 2; r >= 0; --r) {
                for (int c = r; c >= 0; --c) {
                    int p_val = b[r][c];
                    int l_val = b[r + 1][c];
                    int r_val = b[r + 1][c + 1];

                    if (l_val < r_val) {
                        if (p_val > l_val) {
                            swapped_in_pass |= do_swap(r, c, r + 1, c);
                        }
                    } else {
                        if (p_val > r_val) {
                           swapped_in_pass |= do_swap(r, c, r + 1, c + 1);
                        }
                    }
                    if (limit_reached) break;
                }
                if (limit_reached) break;
            }
        }
        if (!swapped_in_pass) {
            break;
        }
        if (limit_reached) break;
    }

    std::cout << history.size() << "\n";
    for (const auto& t : history) {
        std::cout << std::get<0>(t) << " " << std::get<1>(t) << " " << std::get<2>(t) << " " << std::get<3>(t) << "\n";
    }

    return 0;
}