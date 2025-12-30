#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<long long> cost(m);
    for (int j = 0; j < m; ++j) cin >> cost[j];

    vector<vector<int>> elementsOfSet(m);
    vector<vector<int>> setsOfElement(n);

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        vector<int> tmp;
        tmp.reserve(k);
        for (int t = 0; t < k; ++t) {
            int a;
            cin >> a;
            --a;
            if (0 <= a && a < m) tmp.push_back(a);
        }
        sort(tmp.begin(), tmp.end());
        tmp.erase(unique(tmp.begin(), tmp.end()), tmp.end());
        setsOfElement[i] = tmp;
        for (int a : tmp) {
            elementsOfSet[a].push_back(i);
        }
    }

    vector<int> curGain(m);
    for (int j = 0; j < m; ++j) curGain[j] = (int)elementsOfSet[j].size();

    vector<char> chosenSet(m, false);
    vector<char> uncovered(n, true);
    int remaining = n;
    vector<int> selected;
    selected.reserve(m);

    const long double INF = 1e100L;

    while (remaining > 0) {
        int best = -1;
        long double bestScore = -1.0L;
        for (int j = 0; j < m; ++j) {
            if (chosenSet[j]) continue;
            int gain = curGain[j];
            if (gain <= 0) continue;
            long double score;
            if (cost[j] == 0) {
                score = INF;
            } else {
                score = (long double)gain / (long double)cost[j];
            }
            if (score > bestScore) {
                bestScore = score;
                best = j;
            }
        }
        if (best == -1) break;
        chosenSet[best] = true;
        selected.push_back(best);
        for (int e : elementsOfSet[best]) {
            if (uncovered[e]) {
                uncovered[e] = false;
                --remaining;
                for (int s : setsOfElement[e]) {
                    if (!chosenSet[s] && curGain[s] > 0) {
                        --curGain[s];
                    }
                }
            }
        }
    }

    // Fallback for any remaining uncovered elements
    if (remaining > 0) {
        for (int e = 0; e < n; ++e) {
            if (uncovered[e]) {
                const vector<int>& containing = setsOfElement[e];
                if (containing.empty()) continue; // impossible to cover
                int bestSet = containing[0];
                for (int s : containing) {
                    if (cost[s] < cost[bestSet]) bestSet = s;
                }
                if (!chosenSet[bestSet]) {
                    chosenSet[bestSet] = true;
                    selected.push_back(bestSet);
                    for (int ee : elementsOfSet[bestSet]) {
                        if (uncovered[ee]) {
                            uncovered[ee] = false;
                            --remaining;
                            for (int s : setsOfElement[ee]) {
                                if (!chosenSet[s] && curGain[s] > 0) {
                                    --curGain[s];
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Redundant set removal
    vector<int> coverCount(n, 0);
    for (int s : selected) {
        for (int e : elementsOfSet[s]) {
            ++coverCount[e];
        }
    }

    vector<char> removeFlag(m, false);
    vector<int> order = selected;
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (cost[a] != cost[b]) return cost[a] > cost[b]; // more expensive first
        return a < b;
    });

    for (int s : order) {
        bool canRemove = true;
        for (int e : elementsOfSet[s]) {
            if (coverCount[e] <= 1) {
                canRemove = false;
                break;
            }
        }
        if (canRemove) {
            removeFlag[s] = true;
            for (int e : elementsOfSet[s]) {
                --coverCount[e];
            }
        }
    }

    vector<int> finalSel;
    for (int s : selected) {
        if (!removeFlag[s]) finalSel.push_back(s);
    }

    cout << finalSel.size() << "\n";
    for (size_t i = 0; i < finalSel.size(); ++i) {
        if (i) cout << ' ';
        cout << (finalSel[i] + 1);
    }
    cout << "\n";

    return 0;
}