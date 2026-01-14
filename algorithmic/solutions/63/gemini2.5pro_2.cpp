#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>

int make_query(int M, const std::vector<std::pair<int, int>>& edges, const std::vector<char>& is_in_S, bool S_to_T) {
    std::cout << 0;
    for (const auto& edge : edges) {
        int u = edge.first;
        int v = edge.second;
        bool u_in_S = is_in_S[u];
        bool v_in_S = is_in_S[v];

        if (u_in_S == v_in_S) {
            // Internal edge, orient u->v (U_i < V_i is given)
            std::cout << " 0";
        } else {
            // Cut edge
            if (S_to_T) { // We want S -> T
                if (u_in_S) { // u in S, v in T. u->v is correct. This is direction 0.
                    std::cout << " 0";
                } else { // v in S, u in T. v->u is correct. This is direction 1.
                    std::cout << " 1";
                }
            } else { // We want T -> S
                if (u_in_S) { // u in S, v in T. v->u is correct. This is direction 1.
                    std::cout << " 1";
                } else { // v in S, u in T. u->v is correct. This is direction 0.
                    std::cout << " 0";
                }
            }
        }
    }
    std::cout << std::endl;

    int response;
    std::cin >> response;
    return response;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;
    std::vector<std::pair<int, int>> edges(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> edges[i].first >> edges[i].second;
    }

    int max_bit = 0;
    if (N > 1) {
        max_bit = static_cast<int>(floor(log2(N - 1)));
    }
    
    std::vector<int> A_bits(max_bit + 1, -1);
    std::vector<int> B_bits(max_bit + 1, -1);
    std::vector<int> I_same;

    for (int k = 0; k <= max_bit; ++k) {
        std::vector<char> is_in_S1(N, 0);
        for (int i = 0; i < N; ++i) {
            if ((i >> k) & 1) {
                is_in_S1[i] = 1;
            }
        }
        
        // Q1: orient S1 -> S0. S=S1, T=S0. S->T is true.
        int resp1 = make_query(M, edges, is_in_S1, true);

        // Q2: orient S0 -> S1. S=S1, T=S0. T->S is true, so S->T is false.
        int resp2 = make_query(M, edges, is_in_S1, false);

        if (resp1 == 0) { // No path A->B with S1->S0. So A in S1, B in S0.
            A_bits[k] = 1;
            B_bits[k] = 0;
        } else if (resp2 == 0) { // No path A->B with S0->S1. So A in S0, B in S1.
            A_bits[k] = 0;
            B_bits[k] = 1;
        } else {
            I_same.push_back(k);
        }
    }

    int A_val = 0;
    int C = 0;
    long long A_known_mask = 0;

    for (int k = 0; k <= max_bit; ++k) {
        if (A_bits[k] != -1) {
            if (A_bits[k] == 1) A_val |= (1 << k);
            if (A_bits[k] != B_bits[k]) C |= (1 << k);
            A_known_mask |= (1LL << k);
        }
    }

    for (int j : I_same) {
        std::vector<char> is_in_S(N, 0);
        for (int v = 0; v < N; ++v) {
            if (((v & A_known_mask) == A_val) && !((v >> j) & 1)) {
                is_in_S[v] = 1;
            }
        }
        
        // Partition S = CAND_A_IF_0, T=V\S. Query with T->S, so S->T is false.
        int resp = make_query(M, edges, is_in_S, false);

        if (resp == 1) { // path exists -> A not in S -> A_j=1
            A_val |= (1 << j);
        }
        A_known_mask |= (1LL << j);
    }
    
    int final_A = A_val;
    int final_B = final_A ^ C;

    std::cout << 1 << " " << final_A << " " << final_B << std::endl;

    return 0;
}