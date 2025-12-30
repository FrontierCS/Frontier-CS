#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

// Global variables to be used by recursive functions
std::string s_ans;
int n_global;

// Helper to ask a query and get a response
int ask_query(const std::vector<int>& indices) {
    if (indices.empty()) {
        return 0;
    }
    std::cout << "0 " << indices.size();
    for (int idx : indices) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) exit(0); // Terminate on error
    return response;
}

// Counts the number of ')' in s_U by pairing with a known '(' at opener_idx
int count_closers_pairs(const std::vector<int>& U, int opener_idx) {
    if (U.empty()) return 0;
    int closers = 0;
    const int chunk_size = 499; // k_max = 1000, 2 indices per pair. 1000/2=500. Use a safe margin.
    for (size_t i = 0; i < U.size(); i += chunk_size) {
        std::vector<int> query_indices;
        for (size_t j = i; j < U.size() && j < i + chunk_size; ++j) {
            query_indices.push_back(opener_idx);
            query_indices.push_back(U[j]);
        }
        closers += ask_query(query_indices);
    }
    return closers;
}

// Counts the number of '(' in s_U by pairing with a known ')' at closer_idx
int count_openers_pairs(const std::vector<int>& U, int closer_idx) {
    if (U.empty()) return 0;
    int openers = 0;
    const int chunk_size = 499;
    for (size_t i = 0; i < U.size(); i += chunk_size) {
        std::vector<int> query_indices;
        for (size_t j = i; j < U.size() && j < i + chunk_size; ++j) {
            query_indices.push_back(U[j]);
            query_indices.push_back(closer_idx);
        }
        openers += ask_query(query_indices);
    }
    return openers;
}

// Recursively determines characters for indices in U using a known opener
void solve_recursive(std::vector<int>& U, int opener_idx) {
    if (U.empty()) {
        return;
    }
    
    int k = U.size();
    if (k == 1) {
        std::vector<int> query_v = {opener_idx, U[0]};
        if (ask_query(query_v) == 1) {
            s_ans[U[0]-1] = ')';
        } else {
            s_ans[U[0]-1] = '(';
        }
        return;
    }

    int num_closers = count_closers_pairs(U, opener_idx);

    if (num_closers == 0) {
        for (int idx : U) s_ans[idx - 1] = '(';
        return;
    }
    if (num_closers == k) {
        for (int idx : U) s_ans[idx - 1] = ')';
        return;
    }

    int mid_idx = k / 2;
    std::vector<int> U1(U.begin(), U.begin() + mid_idx);
    std::vector<int> U2(U.begin() + mid_idx, U.end());

    solve_recursive(U1, opener_idx);
    solve_recursive(U2, opener_idx);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    n_global = n;
    s_ans.assign(n, ' ');

    int opener_idx = -1;
    int closer_idx = -1;

    // Phase 1: Find one opener
    // Determine s_1's type
    std::vector<int> all_indices(n);
    std::iota(all_indices.begin(), all_indices.end(), 1);
    int f_all = ask_query(all_indices);
    
    std::vector<int> indices_no_1;
    if (n > 1) {
        indices_no_1.resize(n-1);
        std::iota(indices_no_1.begin(), indices_no_1.end(), 2);
    }
    int f_no_1 = ask_query(indices_no_1);

    if (f_all > f_no_1) {
        s_ans[0] = '(';
        opener_idx = 1;
    } else {
        s_ans[0] = ')';
        closer_idx = 1;
    }

    if (opener_idx == -1) {
        // s_1 is a closer, find the leftmost opener in [2, n] via binary search
        int low = 2, high = n;
        int p = n + 1;
        while(low <= high) {
            int mid = low + (high - low) / 2;
            std::vector<int> U;
            for(int i = 2; i <= mid; ++i) U.push_back(i);
            if (count_openers_pairs(U, closer_idx) > 0) {
                p = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        opener_idx = p;
        s_ans[p-1] = '(';
    }

    // Phase 2: Determine all other characters using the known opener
    std::vector<int> unknown_indices;
    for (int i = 1; i <= n; ++i) {
        if (s_ans[i-1] == ' ') {
            unknown_indices.push_back(i);
        }
    }
    
    solve_recursive(unknown_indices, opener_idx);

    std::cout << "1 " << s_ans << std::endl;

    return 0;
}