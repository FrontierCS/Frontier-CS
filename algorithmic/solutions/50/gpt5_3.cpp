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
    for (int i = 1; i <= m; ++i) cin >> cost[i];
    
    vector<vector<int>> elemSets(n + 1);
    vector<vector<int>> sets(m + 1);
    
    for (int i = 1; i <= n; ++i) {
        int k; cin >> k;
        elemSets[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int a; cin >> a;
            elemSets[i].push_back(a);
            sets[a].push_back(i);
        }
    }
    
    vector<int> uncoveredCount(m + 1);
    for (int s = 1; s <= m; ++s) uncoveredCount[s] = (int)sets[s].size();
    
    vector<char> covered(n + 1, 0);
    int uncovered = n;
    
    vector<int> selected;
    vector<char> selectedFlag(m + 1, 0);
    
    while (uncovered > 0) {
        int best = -1;
        int bestCount = 1;
        long long bestCost = 1;
        for (int s = 1; s <= m; ++s) {
            int c = uncoveredCount[s];
            if (c <= 0) continue;
            if (best == -1) {
                best = s; bestCount = c; bestCost = cost[s];
            } else {
                __int128 lhs = (__int128)cost[s] * bestCount;
                __int128 rhs = (__int128)bestCost * c;
                if (lhs < rhs) {
                    best = s; bestCount = c; bestCost = cost[s];
                } else if (lhs == rhs) {
                    if (c > bestCount || (c == bestCount && (cost[s] < bestCost || (cost[s] == bestCost && s < best)))) {
                        best = s; bestCount = c; bestCost = cost[s];
                    }
                }
            }
        }
        if (best == -1) break;
        if (!selectedFlag[best]) {
            selected.push_back(best);
            selectedFlag[best] = 1;
        }
        for (int e : sets[best]) {
            if (!covered[e]) {
                covered[e] = 1;
                --uncovered;
                for (int t : elemSets[e]) {
                    if (uncoveredCount[t] > 0) --uncoveredCount[t];
                }
            }
        }
    }
    
    if (uncovered > 0) {
        // Fallback: cover remaining elements greedily with cheapest covering set for each uncovered element
        for (int i = 1; i <= n; ++i) {
            if (!covered[i]) {
                int best = -1;
                long long bestC = LLONG_MAX;
                for (int s : elemSets[i]) {
                    if (cost[s] < bestC) {
                        bestC = cost[s];
                        best = s;
                    }
                }
                if (best != -1) {
                    if (!selectedFlag[best]) {
                        selectedFlag[best] = 1;
                        selected.push_back(best);
                    }
                    for (int e : sets[best]) {
                        if (!covered[e]) {
                            covered[e] = 1;
                            --uncovered;
                        }
                    }
                }
            }
        }
    }
    
    // Ensure all covered; if still not, do nothing more (assume valid input makes it coverable)
    
    // Redundancy removal: try to remove sets not needed
    vector<int> coverCount(n + 1, 0);
    for (int s = 1; s <= m; ++s) {
        if (!selectedFlag[s]) continue;
        for (int e : sets[s]) ++coverCount[e];
    }
    vector<int> order;
    order.reserve(selected.size());
    for (int s = 1; s <= m; ++s) if (selectedFlag[s]) order.push_back(s);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (cost[a] != cost[b]) return cost[a] > cost[b];
        return a < b;
    });
    for (int s : order) {
        bool canRemove = true;
        for (int e : sets[s]) {
            if (coverCount[e] <= 1) { canRemove = false; break; }
        }
        if (canRemove) {
            selectedFlag[s] = 0;
            for (int e : sets[s]) --coverCount[e];
        }
    }
    
    vector<int> result;
    result.reserve(selected.size());
    for (int s = 1; s <= m; ++s) if (selectedFlag[s]) result.push_back(s);
    
    cout << result.size() << "\n";
    for (size_t i = 0; i < result.size(); ++i) {
        if (i) cout << ' ';
        cout << result[i];
    }
    cout << "\n";
    return 0;
}