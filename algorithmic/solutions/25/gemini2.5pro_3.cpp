#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

int n;

// Helper to create a binary string from a mask and make a query
int make_query(const std::vector<bool>& s_mask) {
    std::cout << "? ";
    for (int i = 0; i < n; ++i) {
        std::cout << (s_mask[i] ? '1' : '0');
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    return response;
}

// Helper to query q_in(S) = q(V \ S)
int query_q_in(const std::vector<bool>& s_mask) {
    std::vector<bool> complement_mask(n);
    for (int i = 0; i < n; ++i) {
        complement_mask[i] = !s_mask[i];
    }
    return make_query(complement_mask);
}

void solve() {
    std::cin >> n;
    if (n == 1) {
        std::cout << "! 1" << std::endl;
        return;
    }

    std::vector<bool> component_mask(n, false);
    component_mask[0] = true;
    int component_size = 1;

    std::vector<int> unknown_vertices(n - 1);
    std::iota(unknown_vertices.begin(), unknown_vertices.end(), 1);

    while (component_size < n) {
        int q_out_C = make_query(component_mask);
        if (q_out_C == 0) {
            break; // C is a full connected component
        }

        if (unknown_vertices.size() == 1) {
            int v = unknown_vertices[0];
            component_mask[v] = true;
            component_size++;
            unknown_vertices.clear();
            continue;
        }

        int q_in_C = query_q_in(component_mask);

        int l = 0, r = unknown_vertices.size() - 1;
        while (l < r) {
            int mid = l + (r - l) / 2;
            std::vector<bool> u1_mask(n, false);
            for (int j = l; j <= mid; ++j) {
                u1_mask[unknown_vertices[j]] = true;
            }

            int q_in_U1 = query_q_in(u1_mask);

            std::vector<bool> c_u1_mask = component_mask;
            for (int j = l; j <= mid; ++j) {
                c_u1_mask[unknown_vertices[j]] = true;
            }
            int q_in_CU1 = query_q_in(c_u1_mask);

            // conn_metric = |N(U1)∩C| + |N(C)∩U1| = q_in(C) + q_in(U1) - q_in(C U U1)
            int conn_metric = q_in_C + q_in_U1 - q_in_CU1;
            if (conn_metric > 0) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }

        int new_vertex = unknown_vertices[l];
        component_mask[new_vertex] = true;
        component_size++;
        unknown_vertices.erase(unknown_vertices.begin() + l);
    }

    if (component_size == n) {
        std::cout << "! 1" << std::endl;
    } else {
        std::cout << "! 0" << std::endl;
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