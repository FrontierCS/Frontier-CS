#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <list>

// Function to perform a query
int query(const std::vector<int>& pepes) {
    std::cout << "?";
    for (int p : pepes) {
        std::cout << " " << p;
    }
    std::cout << std::endl;
    int winner;
    std::cin >> winner;
    if (winner == -1) {
        exit(0); // Exit on error signal from interactor
    }
    return winner;
}

void solve() {
    int n;
    std::cin >> n;

    // Use a list for efficient removal of elements by value
    std::list<int> remaining_pepes;
    for (int i = 1; i <= n * n; ++i) {
        remaining_pepes.push_back(i);
    }

    std::vector<int> sorted_pepes;
    int num_to_find = n * n - n + 1;

    // Find the fastest pepes one by one
    for (int k = 0; k < num_to_find; ++k) {
        // Find the maximum of the currently remaining pepes
        std::list<int> candidates = remaining_pepes;
        
        while (candidates.size() > 1) {
            // Form a race group with at most n pepes from the front of the candidates
            std::vector<int> race_group;
            auto it = candidates.begin();
            for(int i = 0; i < n && it != candidates.end(); ++i) {
                race_group.push_back(*it);
                it++;
            }
            
            int winner = query(race_group);

            // The losers of this race cannot be the fastest overall among candidates.
            // Remove them from the candidate list.
            // Using list::erase(iterator) is more efficient than rebuilding the list.
            auto it_cand = candidates.begin();
            while(it_cand != candidates.end()){
                bool is_loser = false;
                // Check if the current candidate was in the race and lost
                if (*it_cand != winner) {
                    for(int p_race : race_group){
                        if(*it_cand == p_race){
                            is_loser = true;
                            break;
                        }
                    }
                }

                if(is_loser){
                    it_cand = candidates.erase(it_cand);
                } else {
                    ++it_cand;
                }
            }
        }

        // The only remaining candidate is the fastest
        int next_fastest = candidates.front();
        sorted_pepes.push_back(next_fastest);
        remaining_pepes.remove(next_fastest);
    }

    // Output the final sorted list
    std::cout << "!";
    for (size_t i = 0; i < sorted_pepes.size(); ++i) {
        std::cout << " " << sorted_pepes[i];
    }
    std::cout << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}