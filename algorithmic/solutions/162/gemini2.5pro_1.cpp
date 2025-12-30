#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <tuple>

struct Pos {
    int r, c;
};

const int N = 30;
const int OP_LIMIT = 10000;

std::vector<std::vector<int>> b;
std::vector<std::tuple<int, int, int, int>> history;

void do_swap(Pos p1, Pos p2) {
    if (history.size() >= OP_LIMIT) {
        return;
    }
    std::swap(b[p1.r][p1.c], b[p2.r][p2.c]);
    history.emplace_back(p1.r, p1.c, p2.r, p2.c);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    b.resize(N);
    for (int i = 0; i < N; ++i) {
        b[i].resize(i + 1);
        for (int j = 0; j <= i; ++j) {
            std::cin >> b[i][j];
        }
    }

    int num_passes = N;
    for (int k = 0; k < num_passes; ++k) {
        if (history.size() >= OP_LIMIT) {
            break;
        }
        
        size_t swaps_before_pass = history.size();

        if (k % 2 == 0) {
            for (int i = 0; i < N - 1; ++i) {
                for (int j = 0; j <= i; ++j) {
                    if (b[i][j] > b[i+1][j]) {
                        do_swap({i, j}, {i + 1, j});
                    }
                    if (b[i][j] > b[i+1][j+1]) {
                        do_swap({i, j}, {i + 1, j + 1});
                    }
                }
            }
        } else {
            for (int i = N - 2; i >= 0; --i) {
                for (int j = 0; j <= i; ++j) {
                    if (b[i][j] > b[i+1][j]) {
                        do_swap({i, j}, {i + 1, j});
                    }
                    if (b[i][j] > b[i+1][j+1]) {
                        do_swap({i, j}, {i + 1, j + 1});
                    }
                }
            }
        }
        
        if (history.size() == swaps_before_pass) {
            break;
        }
    }

    std::cout << history.size() << "\n";
    for (const auto& t : history) {
        std::cout << std::get<0>(t) << " " << std::get<1>(t) << " " << std::get<2>(t) << " " << std::get<3>(t) << "\n";
    }

    return 0;
}