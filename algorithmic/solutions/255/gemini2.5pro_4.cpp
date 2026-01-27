#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    auto query = [](const std::vector<int>& left, const std::vector<int>& right) {
        if (left.empty() || right.empty()) {
            return 0;
        }
        std::cout << "? " << left.size() << " " << right.size() << std::endl;
        for (size_t i = 0; i < left.size(); ++i) {
            std::cout << left[i] << (i == left.size() - 1 ? "" : " ");
        }
        std::cout << std::endl;
        for (size_t i = 0; i < right.size(); ++i) {
            std::cout << right[i] << (i == right.size() - 1 ? "" : " ");
        }
        std::cout << std::endl;
        int force;
        std::cin >> force;
        return force;
    };
    
    int pivot = -1;
    std::vector<int> demagnetized;
    std::vector<bool> classified(n + 1, false);

    for (int i = 1; i <= n; ++i) {
        if (classified[i]) {
            continue;
        }

        std::vector<int> magnets_in_between;
        for (int j = i + 1; j <= n; ++j) {
            if (classified[j]) {
                continue;
            }
            if (query({i}, {j}) != 0) {
                pivot = i;
                classified[i] = true;
                classified[j] = true;
                for (int k : magnets_in_between) {
                    if (!classified[k]) {
                        demagnetized.push_back(k);
                        classified[k] = true;
                    }
                }
                break;
            } else {
                magnets_in_between.push_back(j);
            }
        }

        if (pivot != -1) {
            break;
        }
        
        // If i vs all subsequent unclassified magnets is 0, i must be demagnetized.
        // This is because there are at least 2 polarized magnets in total.
        // If i were polarized, all others it was tested against would be demagnetized.
        // But then we might not find the guaranteed second polarized magnet from the remaining set.
        // So, i must be demagnetized.
        demagnetized.push_back(i);
        classified[i] = true;
    }
    
    // It's guaranteed that there are at least two polarized magnets, so a pivot will be found.

    for (int i = 1; i <= n; ++i) {
        if (!classified[i]) {
            if (query({pivot}, {i}) == 0) {
                demagnetized.push_back(i);
            }
        }
    }

    std::sort(demagnetized.begin(), demagnetized.end());

    std::cout << "! " << demagnetized.size();
    for (int magnet : demagnetized) {
        std::cout << " " << magnet;
    }
    std::cout << std::endl;
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