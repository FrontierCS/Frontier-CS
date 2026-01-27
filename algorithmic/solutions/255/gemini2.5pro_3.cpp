#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> G;
    G.push_back(1);
    
    for (int i = 2; i <= n; ++i) {
        std::cout << "? " << G.size() << " 1" << std::endl;
        for (size_t j = 0; j < G.size(); ++j) {
            std::cout << G[j] << (j == G.size() - 1 ? "" : " ");
        }
        std::cout << std::endl;
        std::cout << i << std::endl;
        std::cout.flush();

        int F;
        std::cin >> F;

        if (F != 0) {
            // Split found. `i` is polar. G has one polar magnet.
            // Find the polar magnet in G using binary search.
            int polar_in_G;
            int low = 0, high = G.size() - 1, pivot_idx = -1;
            while(low <= high) {
                int mid = low + (high - low) / 2;
                
                std::cout << "? " << mid + 1 << " 1" << std::endl;
                for (int k = 0; k <= mid; ++k) {
                    std::cout << G[k] << (k == mid ? "" : " ");
                }
                std::cout << std::endl;
                std::cout << i << std::endl;
                std::cout.flush();
                
                int new_F;
                std::cin >> new_F;

                if (new_F != 0) {
                    pivot_idx = mid;
                    high = mid - 1;
                } else {
                    low = mid + 1;
                }
            }
            polar_in_G = G[pivot_idx];

            std::vector<int> demagnetized;
            std::vector<bool> known(n + 1, false);

            for(int magnet : G) {
                if (magnet != polar_in_G) {
                    demagnetized.push_back(magnet);
                }
                known[magnet] = true;
            }
            known[i] = true;
            
            for (int j = 1; j <= n; ++j) {
                if (!known[j]) {
                    std::cout << "? 1 1" << std::endl;
                    std::cout << polar_in_G << std::endl;
                    std::cout << j << std::endl;
                    std::cout.flush();
                    int F_j;
                    std::cin >> F_j;
                    if (F_j == 0) {
                        demagnetized.push_back(j);
                    }
                }
            }
            
            std::cout << "! " << demagnetized.size();
            for(int d : demagnetized) {
                std::cout << " " << d;
            }
            std::cout << std::endl;
            std::cout.flush();
            return;
        } else {
            G.push_back(i);
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