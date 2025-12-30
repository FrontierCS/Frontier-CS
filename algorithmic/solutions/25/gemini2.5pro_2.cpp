#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

int n;

int make_query(const std::vector<int>& s_nodes) {
    if (s_nodes.empty()) {
        return 0;
    }
    std::string s(n, '0');
    for (int node : s_nodes) {
        s[node - 1] = '1';
    }
    std::cout << "? " << s << std::endl;
    int response;
    std::cin >> response;
    return response;
}

int make_query_union(const std::vector<int>& s1, const std::vector<int>& s2) {
    if (s1.empty() && s2.empty()) {
        return 0;
    }
    std::string s(n, '0');
    for (int node : s1) {
        s[node - 1] = '1';
    }
    for (int node : s2) {
        s[node - 1] = '1';
    }
    std::cout << "? " << s << std::endl;
    int response;
    std::cin >> response;
    return response;
}

void solve() {
    std::cin >> n;
    if (n == 1) {
        std::cout << "! 1" << std::endl;
        return;
    }

    std::vector<int> component;
    component.push_back(1);
    std::vector<bool> in_component(n + 1, false);
    in_component[1] = true;

    for (int i = 1; i < n; ++i) {
        std::vector<int> unknown;
        for (int j = 1; j <= n; ++j) {
            if (!in_component[j]) {
                unknown.push_back(j);
            }
        }

        int q_comp = make_query(component);
        if (q_comp == 0) {
            std::cout << "! 0" << std::endl;
            return;
        }

        int low = 0, high = unknown.size() - 1;
        int neighbor_node = -1;

        while (low < high) {
            int mid = low + (high - low) / 2;
            std::vector<int> U1;
            for (int k = low; k <= mid; ++k) {
                U1.push_back(unknown[k]);
            }
            
            int q_U1 = make_query(U1);
            int q_comp_union_U1 = make_query_union(component, U1);

            if (q_comp + q_U1 - q_comp_union_U1 > 0) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        neighbor_node = unknown[low];
        
        component.push_back(neighbor_node);
        in_component[neighbor_node] = true;
    }

    std::cout << "! 1" << std::endl;
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