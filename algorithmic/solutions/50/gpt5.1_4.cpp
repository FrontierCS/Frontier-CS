#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 400;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; ++i) cin >> cost[i];

    vector<vector<int>> setElements(m + 1);
    vector<vector<int>> elementSets(n); // elements are 0-based
    vector<bitset<MAXN>> setMask(m + 1);

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        while (k--) {
            int a;
            cin >> a;
            if (a < 1 || a > m) continue;
            setElements[a].push_back(i);
            elementSets[i].push_back(a);
            setMask[a].set(i);
        }
    }

    bitset<MAXN> uncovered;
    for (int i = 0; i < n; ++i) uncovered.set(i);

    vector<int> chosen;
    vector<char> used(m + 1, 0);

    // Greedy weighted set cover
    while (uncovered.any()) {
        int bestSet = -1;
        long long bestCost = 0;
        int bestGain = 1;

        for (int s = 1; s <= m; ++s) {
            if (used[s]) continue;
            bitset<MAXN> tmp = setMask[s] & uncovered;
            int gain = (int)tmp.count();
            if (gain <= 0) continue;

            if (bestSet == -1) {
                bestSet = s;
                bestCost = cost[s];
                bestGain = gain;
            } else {
                __int128 left = (__int128)cost[s] * bestGain;
                __int128 right = (__int128)bestCost * gain;
                if (left < right || (left == right && cost[s] < bestCost)) {
                    bestSet = s;
                    bestCost = cost[s];
                    bestGain = gain;
                }
            }
        }

        if (bestSet == -1) break; // cannot cover remaining elements
        used[bestSet] = 1;
        chosen.push_back(bestSet);
        uncovered &= ~setMask[bestSet];
    }

    // Fallback: if some elements remain uncovered, cover each with a cheapest containing set
    if (uncovered.any()) {
        for (int i = 0; i < n; ++i) {
            if (!uncovered.test(i)) continue;
            long long bestC = (1LL << 62);
            int bestS = -1;
            for (int s : elementSets[i]) {
                if (cost[s] < bestC) {
                    bestC = cost[s];
                    bestS = s;
                }
            }
            if (bestS != -1) {
                if (!used[bestS]) {
                    used[bestS] = 1;
                    chosen.push_back(bestS);
                    uncovered &= ~setMask[bestS];
                }
            }
        }
    }

    // Compute cover count per element
    vector<int> coverCount(n, 0);
    for (int s : chosen) {
        for (int e : setElements[s]) {
            ++coverCount[e];
        }
    }

    // Remove redundant sets (those whose elements are covered by others)
    sort(chosen.begin(), chosen.end(), [&](int a, int b) {
        if (cost[a] != cost[b]) return cost[a] > cost[b]; // remove expensive ones first
        return a < b;
    });

    for (int s : chosen) {
        if (!used[s]) continue;
        bool canRemove = true;
        for (int e : setElements[s]) {
            if (coverCount[e] <= 1) {
                canRemove = false;
                break;
            }
        }
        if (canRemove) {
            used[s] = 0;
            for (int e : setElements[s]) {
                --coverCount[e];
            }
        }
    }

    // Prepare and output result
    vector<int> output;
    for (int s = 1; s <= m; ++s) {
        if (used[s]) output.push_back(s);
    }

    cout << output.size() << '\n';
    for (size_t i = 0; i < output.size(); ++i) {
        if (i) cout << ' ';
        cout << output[i];
    }
    cout << '\n';

    return 0;
}