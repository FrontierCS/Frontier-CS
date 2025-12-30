#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <cassert>

int N_val, l1_val, l2_val;

// Function to perform a query of type 1
int ask(int l, int r) {
    std::cout << "1 " << l << " " << r << std::endl;
    int x;
    std::cin >> x;
    return x;
}

// Function to perform a swap of type 2
void swap_op(int i, int j) {
    std::cout << "2 " << i << " " << j << std::endl;
    int confirmation;
    std::cin >> confirmation;
}

// Function to submit the final answer
void answer(const std::vector<int>& p) {
    std::cout << "3";
    for (int i = 1; i <= N_val; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

// State tracking for permutations
std::vector<int> orig_at_pos;
std::vector<int> pos_of_orig;

// Custom swap function that updates state
void do_swap(int i, int j) {
    if (i == j) return;
    swap_op(i, j);
    int orig_i = orig_at_pos[i];
    int orig_j = orig_at_pos[j];
    std::swap(orig_at_pos[i], orig_at_pos[j]);
    std::swap(pos_of_orig[orig_i], pos_of_orig[orig_j]);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N_val >> l1_val >> l2_val;
    
    if (N_val == 1) {
        std::vector<int> p = {0, 1};
        answer(p);
        return 0;
    }

    orig_at_pos.resize(N_val + 1);
    pos_of_orig.resize(N_val + 1);
    std::iota(orig_at_pos.begin() + 1, orig_at_pos.end(), 1);
    std::iota(pos_of_orig.begin() + 1, pos_of_orig.end(), 1);

    std::vector<int> C1(N_val + 1), C2(N_val + 2);
    C1[0] = 0; C1[1] = 1;
    for (int k = 2; k <= N_val; ++k) {
        C1[k] = ask(1, k);
    }
    
    C2[N_val + 1] = 0; C2[N_val] = 1;
    for (int k = N_val - 1; k >= 1; --k) {
        C2[k] = ask(k, N_val);
    }

    std::vector<int> deg(N_val + 1);
    std::vector<int> endpoints;
    
    deg[1] = (C2[2] - C2[1] + 1);
    if (deg[1] == 1) endpoints.push_back(1);
    
    if (N_val > 1) {
        deg[N_val] = (C1[N_val - 1] - C1[N_val] + 1);
        if (deg[N_val] == 1) endpoints.push_back(N_val);
    }

    for (int k = 2; k < N_val; ++k) {
        int adj1 = C1[k - 1] - C1[k] + 1;
        int adj2 = C2[k + 1] - C2[k] + 1;
        deg[k] = adj1 + adj2;
        if (deg[k] == 1) {
            endpoints.push_back(k);
        }
    }
    
    int ep1 = endpoints[0];
    int ep2 = endpoints[1];

    std::vector<int> p_ans(N_val + 1);
    std::vector<int> pos_of_val(N_val + 1);
    
    pos_of_val[1] = ep1;
    pos_of_val[N_val] = ep2;

    do_swap(pos_of_orig[ep1], 1);
    
    int chain_len_in_pos = 1;
    for (int v = 1; v <= N_val - 2; ++v) {
        int pos_v_curr = chain_len_in_pos;
        int L = pos_v_curr + 1, R = N_val;
        int found_pos = -1;

        if (L == R) {
            found_pos = L;
        } else {
            while (L < R) {
                int mid = L + (R - L) / 2;
                int adj = ask(pos_v_curr + 1, mid) - ask(pos_v_curr, mid) + 1;
                if (adj == 1) {
                    R = mid;
                } else {
                    L = mid + 1;
                }
            }
            found_pos = L;
        }
        
        int orig_idx_of_v_plus_1 = orig_at_pos[found_pos];
        pos_of_val[v + 1] = orig_idx_of_v_plus_1;
        
        chain_len_in_pos++;
        do_swap(found_pos, chain_len_in_pos);
    }

    for (int v = 1; v <= N_val; ++v) {
        p_ans[pos_of_val[v]] = v;
    }
    
    answer(p_ans);

    return 0;
}