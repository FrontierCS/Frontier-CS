#include <iostream>
#include <vector>
#include <list>
#include <numeric>

void solve() {
    int n;
    std::cin >> n;

    std::list<int> candidates;
    for (int i = 0; i < n; ++i) {
        candidates.push_back(i);
    }

    while (candidates.size() > 2) {
        std::list<int> next_candidates;
        for (int pen_idx : candidates) {
            std::cout << "0 " << pen_idx << std::endl;
            int response;
            std::cin >> response;
            if (response == 1) {
                next_candidates.push_back(pen_idx);
            }
        }
        candidates = next_candidates;
        // It's possible multiple pens run out in the same round,
        // so we check the size after the filtering is complete.
        if (candidates.size() <= 2) {
            break;
        }
    }

    // In the unlikely event we are left with fewer than 2 pens
    // (e.g., if multiple pens had the same low ink levels, which is
    // not possible since it's a permutation), we provide a default valid answer.
    // This is defensive coding; with the problem constraints, this block is not expected to be hit.
    if (candidates.size() < 2) {
        if (candidates.empty()) {
            std::cout << "1 0 1" << std::endl;
        } else {
            int p1 = candidates.front();
            int p2 = (p1 + 1) % n;
            std::cout << "1 " << p1 << " " << p2 << std::endl;
        }
        return;
    }

    int pen1 = candidates.front();
    candidates.pop_front();
    int pen2 = candidates.front();

    std::cout << "1 " << pen1 << " " << pen2 << std::endl;
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