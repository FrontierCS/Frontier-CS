#include <iostream>
#include <vector>
#include <numeric>
#include <list>

void solve() {
    int n;
    std::cin >> n;

    std::list<int> candidates;
    for (int i = 0; i < n; ++i) {
        candidates.push_back(i);
    }

    while (candidates.size() > 2) {
        // Take 3 candidates from the front of the list.
        int p1 = candidates.front(); candidates.pop_front();
        int p2 = candidates.front(); candidates.pop_front();
        int p3 = candidates.front(); candidates.pop_front();

        // Query the first two candidates.
        std::cout << "0 " << p1 << std::endl;
        int r1;
        std::cin >> r1;

        std::cout << "0 " << p2 << std::endl;
        int r2;
        std::cin >> r2;

        // Decide which two pens to keep based on the query results.
        if (r1 == 1 && r2 == 1) {
            // Both p1 and p2 have ink. They are strong. p3 is discarded.
            // The survivors are returned to the list to be considered in later rounds.
            candidates.push_back(p1);
            candidates.push_back(p2);
        } else if (r1 == 1 && r2 == 0) {
            // p1 has ink, p2 is empty. p1 and p3 survive.
            candidates.push_back(p1);
            candidates.push_back(p3);
        } else if (r1 == 0 && r2 == 1) {
            // p2 has ink, p1 is empty. p2 and p3 survive.
            candidates.push_back(p2);
            candidates.push_back(p3);
        } else { // r1 == 0 && r2 == 0
            // Both p1 and p2 are empty. Only p3 survives from this group.
            candidates.push_back(p3);
        }
    }

    // After the loop, exactly two candidates remain.
    int final_p1 = candidates.front();
    candidates.pop_front();
    int final_p2 = candidates.front();
    candidates.pop_front();

    // Output the final selection.
    std::cout << "1 " << final_p1 << " " << final_p2 << std::endl;
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