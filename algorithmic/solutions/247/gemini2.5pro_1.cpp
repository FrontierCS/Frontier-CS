#include <iostream>
#include <vector>
#include <numeric>
#include <utility>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;
    std::vector<long long> a(n), b(n);
    long long sum_a = 0, sum_b = 0;
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
        sum_a += a[i];
    }
    for (int i = 0; i < n; ++i) {
        std::cin >> b[i];
        sum_b += b[i];
    }

    if (sum_a != sum_b) {
        std::cout << "No\n";
        return 0;
    }

    std::vector<std::pair<int, int>> ops;
    
    int max_ops = 200000;

    for (int k = 0; k < max_ops; ++k) {
        if (a == b) {
            break;
        }

        bool move_found = false;
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                if (i == j) continue;

                if (a[i] > b[i] && a[j] < b[j]) {
                    if (i < j) {
                        if (a[i] >= a[j] && a[j] >= 2) {
                            ops.push_back({i + 1, j + 1});
                            long long old_ai = a[i];
                            long long old_aj = a[j];
                            a[i] = old_aj - 1;
                            a[j] = old_ai + 1;
                            move_found = true;
                            break;
                        }
                    } else { // j < i
                        if (a[i] > a[j] + 1 && a[i] >= 2) {
                            ops.push_back({j + 1, i + 1});
                            long long old_ai = a[i];
                            long long old_aj = a[j];
                            a[j] = old_ai - 1;
                            a[i] = old_aj + 1;
                            move_found = true;
                            break;
                        }
                    }
                }
            }
            if (move_found) break;
        }
        
        if (!move_found) {
            break; 
        }
    }

    if (a == b) {
        std::cout << "Yes\n";
        std::cout << ops.size() << "\n";
        for (const auto& p : ops) {
            std::cout << p.first << " " << p.second << "\n";
        }
    } else {
        std::cout << "No\n";
    }

    return 0;
}