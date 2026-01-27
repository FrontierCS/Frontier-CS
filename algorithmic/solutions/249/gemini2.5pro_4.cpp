#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int query(int i, int j) {
    std::cout << "? " << i + 1 << " " << j + 1 << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) exit(0);
    return result;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    std::vector<int> p(n);
    int u = 0, v = 1;
    int min_or = query(u, v);

    for (int i = 2; i < n; ++i) {
        int or_u_i = query(u, i);
        if (or_u_i < min_or) {
            min_or = or_u_i;
            v = i;
        }
    }
    
    // Now u,v is a pair with a minimal OR value.
    // One of them is very likely to be the index of 0.
    int zero_idx = u;
    int or_v_u = query(v,u);

    for (int i=0; i<n; ++i) {
        if (i == u || i == v) continue;
        int or_u_i = query(u, i);
        int or_v_i = query(v, i);
        if (or_u_i > or_v_i) {
            // p[u]|p[i] > p[v]|p[i]. This suggests p[u] > p[v], so v is a better candidate for 0
            zero_idx = v;
            break;
        } else if (or_v_i > or_u_i) {
            // p[v]|p[i] > p[u]|p[i]. u is a better candidate for 0
            zero_idx = u;
            break;
        }
    }
    
    p[zero_idx] = 0;
    for (int i = 0; i < n; i++) {
        if (i == zero_idx) continue;
        p[i] = query(zero_idx, i);
    }

    std::cout << "! ";
    for (int i = 0; i < n; ++i) {
        std::cout << p[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}