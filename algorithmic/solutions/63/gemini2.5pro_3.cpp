#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

void ask_query(int M, const std::vector<int>& directions) {
    std::cout << 0;
    for (int i = 0; i < M; ++i) {
        std::cout << " " << directions[i];
    }
    std::cout << std::endl;
}

int read_response() {
    int x;
    std::cin >> x;
    return x;
}

void give_answer(int A, int B) {
    std::cout << 1 << " " << A << " " << B << std::endl;
}

struct Edge {
    int u, v;
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    std::vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> edges[i].u >> edges[i].v;
    }

    int C = 0;
    int logN = 0;
    if (N > 1) {
        logN = std::floor(std::log2(N - 1)) + 1;
    }

    for (int k = 0; k < logN; ++k) {
        std::vector<int> directions(M);
        std::vector<bool> S(N, false);
        for (int i = 0; i < N; ++i) {
            if ((i >> k) & 1) {
                S[i] = true;
            }
        }

        for (int i = 0; i < M; ++i) {
            bool u_in_S = S[edges[i].u];
            bool v_in_S = S[edges[i].v];
            if (u_in_S && !v_in_S) {
                directions[i] = 0; // U_i -> V_i
            } else if (!u_in_S && v_in_S) {
                directions[i] = 1; // V_i -> U_i
            } else {
                if (edges[i].u < edges[i].v) {
                    directions[i] = 0;
                } else {
                    directions[i] = 1;
                }
            }
        }

        ask_query(M, directions);
        int res = read_response();
        if (res == 1) {
            C |= (1 << k);
        }
    }

    std::vector<int> cand_A(N);
    std::iota(cand_A.begin(), cand_A.end(), 0);

    while (cand_A.size() > 1) {
        int mid_size = cand_A.size() / 2;
        if (mid_size == 0) { // If cand_A has only one element, this loop should have terminated.
             break;
        }
        std::vector<bool> S_map(N, false);
        for(int i = 0; i < mid_size; ++i) {
            S_map[cand_A[i]] = true;
        }

        std::vector<int> directions(M);
        for (int i = 0; i < M; ++i) {
            bool u_in_S = S_map[edges[i].u];
            bool v_in_S = S_map[edges[i].v];

            if (u_in_S && !v_in_S) {
                directions[i] = 0;
            } else if (!u_in_S && v_in_S) {
                directions[i] = 1;
            } else {
                if (edges[i].u < edges[i].v) {
                    directions[i] = 0;
                } else {
                    directions[i] = 1;
                }
            }
        }
        
        ask_query(M, directions);
        int res = read_response();

        std::vector<int> next_cand_A;
        if (res == 1) { // rule out (a not in S, b in S)
            for (int a : cand_A) {
                int b = a ^ C;
                if (!(!S_map[a] && S_map[b])) {
                    next_cand_A.push_back(a);
                }
            }
        } else { // rule out (a in S, b not in S)
            for (int a : cand_A) {
                int b = a ^ C;
                if (!(S_map[a] && !S_map[b])) {
                    next_cand_A.push_back(a);
                }
            }
        }
        cand_A = next_cand_A;
    }

    int A = cand_A[0];
    int B = A ^ C;

    give_answer(A, B);

    return 0;
}