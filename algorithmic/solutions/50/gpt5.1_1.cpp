#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; ++i) {
        cin >> cost[i];
    }

    vector<vector<int>> elemSets(n + 1);      // for each element, sets containing it
    vector<vector<int>> setElems(m + 1);      // for each set, elements it contains

    for (int i = 1; i <= n; ++i) {
        int k;
        cin >> k;
        elemSets[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int s;
            cin >> s;
            elemSets[i].push_back(s);
            setElems[s].push_back(i);
        }
    }

    vector<int> gain(m + 1);
    for (int s = 1; s <= m; ++s) {
        gain[s] = (int)setElems[s].size();
    }

    vector<char> chosen(m + 1, 0);
    vector<char> covered(n + 1, 0);
    int uncovered = n;
    vector<int> solution;

    // Greedy selection
    while (uncovered > 0) {
        int bestSet = -1;
        long long bestCost = 0;
        int bestGain = 1;

        for (int s = 1; s <= m; ++s) {
            if (chosen[s] || gain[s] <= 0) continue;
            if (bestSet == -1) {
                bestSet = s;
                bestCost = cost[s];
                bestGain = gain[s];
            } else {
                long long lhs = cost[s] * (long long)bestGain;
                long long rhs = bestCost * (long long)gain[s];
                if (lhs < rhs || (lhs == rhs && cost[s] < bestCost)) {
                    bestSet = s;
                    bestCost = cost[s];
                    bestGain = gain[s];
                }
            }
        }

        // Fallback (should not trigger if input is solvable and logic is correct)
        if (bestSet == -1) {
            for (int e = 1; e <= n && bestSet == -1; ++e) {
                if (!covered[e]) {
                    for (int s : elemSets[e]) {
                        if (!chosen[s]) {
                            if (bestSet == -1 || cost[s] < cost[bestSet]) {
                                bestSet = s;
                            }
                        }
                    }
                }
            }
            if (bestSet == -1) break; // no way to cover remaining elements
        }

        chosen[bestSet] = 1;
        solution.push_back(bestSet);

        for (int e : setElems[bestSet]) {
            if (!covered[e]) {
                covered[e] = 1;
                --uncovered;
                for (int s : elemSets[e]) {
                    if (!chosen[s]) {
                        --gain[s];
                    }
                }
            }
        }
    }

    // Redundancy elimination
    vector<int> coverCount(n + 1, 0);
    vector<int> currentSets;
    currentSets.reserve(solution.size());
    for (int s : solution) {
        if (chosen[s]) {
            currentSets.push_back(s);
            for (int e : setElems[s]) {
                ++coverCount[e];
            }
        }
    }

    // Order sets by descending cost to try to remove expensive ones first
    sort(currentSets.begin(), currentSets.end(),
         [&](int a, int b) {
             if (cost[a] != cost[b]) return cost[a] > cost[b];
             return a < b;
         });

    for (int s : currentSets) {
        if (!chosen[s]) continue;
        bool canRemove = true;
        for (int e : setElems[s]) {
            if (coverCount[e] <= 1) {
                canRemove = false;
                break;
            }
        }
        if (canRemove) {
            chosen[s] = 0;
            for (int e : setElems[s]) {
                --coverCount[e];
            }
        }
    }

    // Collect final solution
    vector<int> finalSets;
    finalSets.reserve(solution.size());
    for (int s = 1; s <= m; ++s) {
        if (chosen[s]) finalSets.push_back(s);
    }

    cout << finalSets.size() << '\n';
    for (size_t i = 0; i < finalSets.size(); ++i) {
        if (i) cout << ' ';
        cout << finalSets[i];
    }
    cout << '\n';

    return 0;
}