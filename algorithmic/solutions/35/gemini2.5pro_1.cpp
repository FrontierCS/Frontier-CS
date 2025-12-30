#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

bool ask_query(int x, const std::vector<int>& s) {
    if (s.empty()) {
        return false;
    }
    std::cout << "? " << x << " " << s.size();
    for (int idx : s) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response == 1;
}

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> o_indices, e_indices;
    for (int i = 1; i < n; ++i) {
        o_indices.push_back(2 * i - 1);
        e_indices.push_back(2 * i);
    }

    std::vector<bool> in_o(n + 1, false);
    std::vector<bool> in_e(n + 1, false);

    for (int x = 1; x <= n; ++x) {
        in_o[x] = ask_query(x, o_indices);
    }
    for (int x = 1; x <= n; ++x) {
        in_e[x] = ask_query(x, e_indices);
    }

    std::vector<int> candidates;
    for (int x = 1; x <= n; ++x) {
        if (in_o[x] != in_e[x]) {
            candidates.push_back(x);
        }
    }
    
    int v = -1;
    for (int x = 1; x <= n; ++x) {
        if (ask_query(x, {2 * n - 1})) {
            v = x;
            break;
        }
    }
    
    bool v_in_cand = false;
    for (int c : candidates) {
        if (c == v) {
            v_in_cand = true;
            break;
        }
    }

    if (!v_in_cand) {
        std::cout << "! " << v << std::endl;
        return;
    }

    std::vector<int> final_candidates;
    for (int c : candidates) {
        if (c != v) {
            final_candidates.push_back(c);
        }
    }

    for (int y : final_candidates) {
        std::vector<int> search_space;
        for (int i = 1; i < 2 * n - 1; ++i) {
            search_space.push_back(i);
        }

        int p1 = -1;
        int low = 0, high = search_space.size() - 1;
        
        while(low < high) {
            int mid = low + (high - low) / 2;
            std::vector<int> query_indices;
            for(int i = low; i <= mid; ++i) {
                query_indices.push_back(search_space[i]);
            }
            if(ask_query(y, query_indices)) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        p1 = search_space[low];

        std::vector<int> remaining_space;
        for (int i = 1; i < 2 * n - 1; ++i) {
            if (i != p1) {
                remaining_space.push_back(i);
            }
        }

        if (!ask_query(y, remaining_space)) {
            std::cout << "! " << y << std::endl;
            return;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}