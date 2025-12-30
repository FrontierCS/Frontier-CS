#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

void ask_query(int n, const std::vector<int>& q) {
    std::cout << "0";
    for (int i = 0; i < n; ++i) {
        std::cout << " " << q[i];
    }
    std::cout << std::endl;
}

void submit_answer(int n, const std::vector<int>& p) {
    std::cout << "1";
    for (int i = 0; i < n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int n;
    std::cin >> n;

    if (n == 1) {
        submit_answer(1, {1});
        return 0;
    }

    std::vector<int> pos_val(n + 1, 0);
    
    int log_n = 0;
    if (n > 1) {
        log_n = std::floor(std::log2(n - 1)) + 1;
    }

    std::vector<int> q(n);
    std::vector<int> d(n + 1);

    for (int k = 0; k < log_n; ++k) {
        std::vector<int> S_indices;
        for (int i = 0; i < n; ++i) {
            if (((i >> k) & 1)) {
                S_indices.push_back(i);
            }
        }

        if (S_indices.empty()) {
            continue;
        }
        if (S_indices.size() == n) {
            for (int v = 1; v <= n; ++v) {
                pos_val[v] |= (1 << k);
            }
            continue;
        }

        long long rhs = S_indices.size();
        
        for (int v = 2; v <= n; ++v) {
            std::fill(q.begin(), q.end(), v);
            for(int idx : S_indices) {
                q[idx] = 1;
            }
            
            ask_query(n, q);
            int K;
            std::cin >> K;
            
            d[v] = K - 1;
            rhs += d[v];
        }

        int b1 = 0;
        if (rhs > 0 && rhs % n == 0) {
            b1 = 1;
        }

        if (b1 == 1) {
            pos_val[1] |= (1 << k);
        }

        for (int v = 2; v <= n; ++v) {
            int bv = b1 - d[v];
            if (bv == 1) {
                pos_val[v] |= (1 << k);
            }
        }
    }

    std::vector<int> p(n);
    for (int v = 1; v <= n; ++v) {
        p[pos_val[v]] = v;
    }

    submit_answer(n, p);

    return 0;
}