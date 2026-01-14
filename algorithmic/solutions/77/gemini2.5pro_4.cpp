#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <iomanip>

void solve() {
    int n, m;
    std::cin >> n >> m;

    int num_experts = 2 * n;
    std::vector<long double> weights(num_experts, 1.0L);

    for (int t = 1; t <= m; ++t) {
        std::string s;
        std::cin >> s;

        long double w0 = 0.0L;
        long double w1 = 0.0L;
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') {
                w0 += weights[i];     // Expert i agrees with prediction 0
                w1 += weights[i + n]; // Anti-expert i predicts 1
            } else {
                w1 += weights[i];     // Expert i agrees with prediction 1
                w0 += weights[i + n]; // Anti-expert i predicts 0
            }
        }

        int prediction = (w1 >= w0) ? 1 : 0;
        std::cout << prediction << std::endl;

        int outcome;
        std::cin >> outcome;

        double eta = std::sqrt(2.0 * std::log(static_cast<double>(num_experts)) / t);
        if (eta > 0.5) {
            eta = 0.5;
        }
        long double beta = 1.0L - eta;

        long double max_w = 0.0L;
        for (int i = 0; i < n; ++i) {
            int p_i = s[i] - '0';
            if (p_i != outcome) {
                weights[i] *= beta;
            } else {
                weights[i + n] *= beta;
            }
        }
        
        for(int i = 0; i < num_experts; ++i) {
            if(weights[i] > max_w) {
                max_w = weights[i];
            }
        }

        if (max_w < 1e-100 && max_w > 0) {
            for (int i = 0; i < num_experts; ++i) {
                weights[i] /= max_w;
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}