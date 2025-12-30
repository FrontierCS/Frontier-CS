#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    if (n == 1) {
        std::cout << "1 1" << std::endl;
        std::cout.flush();
        return;
    }

    int L = 0;
    if (n > 1) {
        L = std::ceil(std::log2(n));
    }
    
    std::vector<std::vector<int>> bits(n + 1, std::vector<int>(L));

    for (int k = 0; k < L; ++k) {
        std::vector<int> diffs(n - 1); 
        for (int v = 1; v < n; ++v) {
            std::cout << "0";
            for (int i = 1; i <= n; ++i) {
                if (((i - 1) >> k) & 1) {
                    std::cout << " " << v;
                } else {
                    std::cout << " " << v + 1;
                }
            }
            std::cout << std::endl;
            std::cout.flush();

            int m;
            std::cin >> m;
            if (std::cin.fail()) return;
            diffs[v - 1] = m - 1;
        }

        std::vector<int> s(n + 1, 0);
        for (int v = 1; v < n; ++v) {
            s[v + 1] = s[v] + diffs[v - 1];
        }

        std::vector<int> b0(n + 1);
        bool b0_valid = true;
        for (int v = 1; v <= n; ++v) {
            int val = -s[v];
            if (val < 0 || val > 1) {
                b0_valid = false;
                break;
            }
            b0[v] = val;
        }
        
        int ik_size = 0;
        for (int i = 1; i <= n; ++i) {
            if (((i - 1) >> k) & 1) {
                ik_size++;
            }
        }

        if (b0_valid) {
            int sum_b0 = 0;
            for(int v = 1; v <= n; ++v) sum_b0 += b0[v];
            if (sum_b0 == ik_size) {
                for (int v = 1; v <= n; ++v) {
                    bits[v][k] = b0[v];
                }
            } else {
                for (int v = 1; v <= n; ++v) {
                    bits[v][k] = 1 - s[v];
                }
            }
        } else {
            for (int v = 1; v <= n; ++v) {
                bits[v][k] = 1 - s[v];
            }
        }
    }

    std::vector<int> pos(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        for (int k = 0; k < L; ++k) {
            if (bits[v][k] == 1) {
                pos[v] |= (1 << k);
            }
        }
        pos[v]++;
    }

    std::vector<int> p(n + 1);
    for (int v = 1; v <= n; ++v) {
        p[pos[v]] = v;
    }

    std::cout << "1";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
    std::cout.flush();
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}