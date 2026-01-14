#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to perform a query and read the response
int query(int pen_idx) {
    std::cout << "0 " << pen_idx << std::endl;
    int response;
    std::cin >> response;
    return response;
}

// Function to submit the final answer
void answer(int pen1_idx, int pen2_idx) {
    std::cout << "1 " << pen1_idx << " " << pen2_idx << std::endl;
}

void solve() {
    int n;
    std::cin >> n;

    // 1. Initial Screening
    std::vector<int> candidates;
    for (int i = 0; i < n; ++i) {
        if (query(i) == 1) {
            candidates.push_back(i);
        }
    }

    // 2. Main Tournament
    std::vector<int> survivors = candidates;
    std::map<int, std::vector<int>> defeated_by;

    while (survivors.size() > 1) {
        std::vector<int> next_survivors;
        if (survivors.size() % 2 == 1) {
            next_survivors.push_back(survivors.back());
            survivors.pop_back();
        }

        for (size_t i = 0; i < survivors.size(); i += 2) {
            int p1 = survivors[i];
            int p2 = survivors[i + 1];
            int r1 = query(p1);
            int r2 = query(p2);
            int winner, loser;

            if (r1 > r2) {
                winner = p1;
                loser = p2;
            } else if (r2 > r1) {
                winner = p2;
                loser = p1;
            } else { // Responses are equal (both 1 or both 0), pick arbitrarily
                winner = p1;
                loser = p2;
            }
            
            next_survivors.push_back(winner);
            defeated_by[winner].push_back(loser);
        }
        survivors = next_survivors;
    }

    int champ = survivors[0];

    // 3. Second Tournament
    std::vector<int> second_contenders = defeated_by[champ];
    survivors = second_contenders;
    
    while (survivors.size() > 1) {
        std::vector<int> next_survivors;
        if (survivors.size() % 2 == 1) {
            next_survivors.push_back(survivors.back());
            survivors.pop_back();
        }

        for (size_t i = 0; i < survivors.size(); i += 2) {
            int p1 = survivors[i];
            int p2 = survivors[i + 1];
            int r1 = query(p1);
            int r2 = query(p2);
            int winner;
            if (r1 > r2) {
                winner = p1;
            } else if (r2 > r1) {
                winner = p2;
            } else {
                winner = p1;
            }
            next_survivors.push_back(winner);
        }
        survivors = next_survivors;
    }

    int second_place = survivors[0];

    // 4. Final Selection
    answer(champ, second_place);
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