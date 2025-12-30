#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

void answer(int i) {
    std::cout << "! " << i << std::endl;
}

std::pair<int, int> query(int i) {
    std::cout << "? " << i << std::endl;
    int a0, a1;
    std::cin >> a0 >> a1;
    return {a0, a1};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    int pos = std::uniform_int_distribution<int>(0, n - 1)(rng);
    int last_pos = -1;

    int best_pos = -1;
    int min_s = n + 1;

    // A budget of 100 queries should be sufficient for the search to converge.
    for (int i = 0; i < 100; ++i) {
        if (pos < 0 || pos >= n) { // Should be caught by clamping
             pos = std::uniform_int_distribution<int>(0, n - 1)(rng);
        }

        std::pair<int, int> res = query(pos);
        int a0 = res.first;
        int a1 = res.second;
        int s = a0 + a1;
        
        if (s < min_s) {
            min_s = s;
            best_pos = pos;
        }

        if (s == 0) {
            answer(pos);
            return 0;
        }

        last_pos = pos;
        
        // This heuristic moves pos to the estimated median of the S more valuable items.
        // The step is (a1 - a0 + 1) / 2.
        pos = pos - a0 + (s + 1) / 2;

        if (pos == last_pos) {
            // Perturb if stuck.
            if (pos < n - 1) {
                pos++;
            } else {
                pos--;
            }
        }

        // Clamp to valid range
        if (pos < 0) {
            pos = 0;
        }
        if (pos >= n) {
            pos = n - 1;
        }
    }
    
    answer(best_pos);

    return 0;
}