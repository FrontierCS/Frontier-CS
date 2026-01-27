#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Function to perform a query
int ask(const vector<int>& pepes) {
    cout << "?";
    for (int pepe : pepes) {
        cout << " " << pepe;
    }
    cout << endl;
    int winner;
    cin >> winner;
    return winner;
}

// Function to report the answer
void answer(const vector<int>& sorted_pepes) {
    cout << "!";
    for (int pepe : sorted_pepes) {
        cout << " " << pepe;
    }
    cout << endl;
}

void solve() {
    int n;
    cin >> n;

    int n_sq = n * n;

    // 1. Partition into n groups
    vector<vector<int>> groups(n);
    for (int i = 0; i < n_sq; ++i) {
        groups[i / n].push_back(i + 1);
    }

    // 2. Sort each group
    vector<vector<int>> sorted_groups(n);
    for (int i = 0; i < n; ++i) {
        vector<int> current_group = groups[i];
        vector<int> sorted_part;
        set<int> current_group_set(current_group.begin(), current_group.end());

        while (!current_group.empty()) {
            vector<int> to_race;
            if (current_group.size() >= n) {
                to_race = current_group;
            } else {
                to_race = current_group;
                // Add fillers. For simplicity, use pepes from a different group.
                // Using group (i+1)%n ensures we don't use pepes from the current group.
                int filler_group_idx = (i + 1) % n;
                for (int p : groups[filler_group_idx]) {
                    if (to_race.size() == n) break;
                    to_race.push_back(p);
                }
            }

            int winner = ask(to_race);

            bool winner_in_group = (current_group_set.count(winner) > 0);
            
            if (winner_in_group) {
                sorted_part.insert(sorted_part.begin(), winner);
                current_group.erase(remove(current_group.begin(), current_group.end(), winner), current_group.end());
            }
            // If the winner is a filler, we retry with the same set of unsorted pepes.
            // The interactor is adaptive but consistent, so we will eventually
            // find a filler that is slower than the max of the current group.
        }
        sorted_groups[i] = sorted_part;
    }

    // 3. Merge sorted groups
    vector<int> result;
    set<int> in_result;
    vector<int> ptrs(n, 0);

    int to_find = n_sq - n + 1;

    for (int k = 0; k < to_find; ++k) {
        vector<int> candidates;
        vector<int> candidate_group_indices;
        
        for (int i = 0; i < n; ++i) {
            if (ptrs[i] < n) {
                candidates.push_back(sorted_groups[i][ptrs[i]]);
                candidate_group_indices.push_back(i);
            }
        }

        if (candidates.empty()) break;

        vector<int> to_race = candidates;
        if (to_race.size() < n) {
            set<int> in_query;
            for(int p : to_race) in_query.insert(p);

            for (int j = n - 1; j >= 0 && to_race.size() < n; --j) {
                for (int i = 0; i < n && to_race.size() < n; ++i) {
                    int p = sorted_groups[i][j];
                    if (in_result.find(p) == in_result.end() && in_query.find(p) == in_query.end()) {
                         to_race.push_back(p);
                         in_query.insert(p);
                    }
                }
            }
        }

        int winner = ask(to_race);
        result.push_back(winner);
        in_result.insert(winner);

        for (size_t i = 0; i < candidates.size(); ++i) {
            if (candidates[i] == winner) {
                ptrs[candidate_group_indices[i]]++;
                break;
            }
        }
    }

    answer(result);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}