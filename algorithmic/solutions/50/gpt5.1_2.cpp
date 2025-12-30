#include <bits/stdc++.h>
using namespace std;

const double TIME_LIMIT = 9.3; // total time limit in seconds (safety margin)

int n, m;
vector<long long> cost;
vector<vector<int>> elementsInSet;   // for each set, list of elements
vector<vector<int>> setsOfElement;   // for each element, list of sets containing it

vector<char> chosen; // whether a set is chosen in current solution
vector<int> coverCnt; // for each element, how many chosen sets cover it
long long totalCost = 0;

void buildInitialSolution() {
    chosen.assign(m, 0);
    coverCnt.assign(n, 0);
    totalCost = 0;

    // Forced selection: elements that appear in exactly one set
    for (int e = 0; e < n; ++e) {
        if (setsOfElement[e].size() == 1) {
            int s = setsOfElement[e][0];
            if (!chosen[s]) {
                chosen[s] = 1;
                totalCost += cost[s];
                for (int u : elementsInSet[s])
                    ++coverCnt[u];
            }
        }
    }

    vector<int> candNew(m);
    vector<int> uncovered;

    // Greedy set-cover
    while (true) {
        uncovered.clear();
        for (int e = 0; e < n; ++e)
            if (coverCnt[e] == 0)
                uncovered.push_back(e);

        if (uncovered.empty())
            break;

        fill(candNew.begin(), candNew.end(), 0);

        for (int e : uncovered) {
            for (int s : setsOfElement[e]) {
                ++candNew[s];
            }
        }

        int bestS = -1;
        for (int s = 0; s < m; ++s) {
            int newCnt = candNew[s];
            if (!newCnt || chosen[s])
                continue;
            if (bestS == -1) {
                bestS = s;
            } else {
                long long lhs = cost[s] * (long long)candNew[bestS];
                long long rhs = cost[bestS] * (long long)newCnt;
                if (lhs < rhs || (lhs == rhs && cost[s] < cost[bestS])) {
                    bestS = s;
                }
            }
        }

        if (bestS == -1) {
            // No way to cover remaining uncovered elements (should not happen for valid instances)
            break;
        }

        chosen[bestS] = 1;
        totalCost += cost[bestS];
        for (int u : elementsInSet[bestS])
            ++coverCnt[u];
    }

    // Make sure all elements are covered; if not, add cheapest covering set per uncovered element
    for (int e = 0; e < n; ++e) {
        if (coverCnt[e] == 0) {
            int bestS = -1;
            long long bestC = (long long)4e18;
            for (int s : setsOfElement[e]) {
                if (cost[s] < bestC) {
                    bestC = cost[s];
                    bestS = s;
                }
            }
            if (bestS != -1) {
                if (!chosen[bestS]) {
                    chosen[bestS] = 1;
                    totalCost += cost[bestS];
                    for (int u : elementsInSet[bestS])
                        ++coverCnt[u];
                }
            }
        }
    }

    // Remove redundant sets
    bool changed;
    do {
        changed = false;
        for (int s = 0; s < m; ++s) {
            if (!chosen[s]) continue;
            bool canRemove = true;
            for (int e : elementsInSet[s]) {
                if (coverCnt[e] <= 1) {
                    canRemove = false;
                    break;
                }
            }
            if (canRemove) {
                chosen[s] = 0;
                totalCost -= cost[s];
                for (int e : elementsInSet[s])
                    --coverCnt[e];
                changed = true;
            }
        }
    } while (changed);
}

void localSearch(const chrono::steady_clock::time_point &startTime) {
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> tempCoverCnt(n);
    vector<int> chosenList;
    bool needRebuild = true;
    long long iterations = 0;

    while (true) {
        if ((iterations & 63) == 0) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
            if (elapsed > TIME_LIMIT)
                break;
        }
        ++iterations;

        if (needRebuild) {
            chosenList.clear();
            for (int s = 0; s < m; ++s) {
                if (chosen[s])
                    chosenList.push_back(s);
            }
            needRebuild = false;
            if (chosenList.empty())
                break;
        }

        // pick random not-chosen set that has at least one element
        int s0 = -1;
        for (int tries = 0; tries < 50; ++tries) {
            int cand = (int)(rng() % (unsigned long long)m);
            if (!chosen[cand] && !elementsInSet[cand].empty()) {
                s0 = cand;
                break;
            }
        }
        if (s0 == -1)
            break;

        // simulate addition of s0 and greedy removal of now-redundant sets
        for (int e = 0; e < n; ++e)
            tempCoverCnt[e] = coverCnt[e];

        long long candCost = totalCost + cost[s0];
        for (int e : elementsInSet[s0])
            ++tempCoverCnt[e];

        vector<int> removed;
        removed.reserve(chosenList.size());

        for (int s : chosenList) {
            bool canRemove = true;
            for (int e : elementsInSet[s]) {
                if (tempCoverCnt[e] <= 1) {
                    canRemove = false;
                    break;
                }
            }
            if (canRemove) {
                removed.push_back(s);
                candCost -= cost[s];
                for (int e : elementsInSet[s])
                    --tempCoverCnt[e];
            }
        }

        if (candCost < totalCost) {
            // commit
            totalCost = candCost;
            for (int e = 0; e < n; ++e)
                coverCnt[e] = tempCoverCnt[e];
            chosen[s0] = 1;
            for (int s : removed)
                chosen[s] = 0;
            needRebuild = true;
        }
    }

    // Final redundant-set cleanup
    bool changed;
    do {
        changed = false;
        for (int s = 0; s < m; ++s) {
            if (!chosen[s]) continue;
            bool canRemove = true;
            for (int e : elementsInSet[s]) {
                if (coverCnt[e] <= 1) {
                    canRemove = false;
                    break;
                }
            }
            if (canRemove) {
                chosen[s] = 0;
                totalCost -= cost[s];
                for (int e : elementsInSet[s])
                    --coverCnt[e];
                changed = true;
            }
        }
    } while (changed);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) {
        return 0;
    }
    cost.assign(m, 0);
    for (int i = 0; i < m; ++i) {
        cin >> cost[i];
    }

    elementsInSet.assign(m, {});
    setsOfElement.assign(n, {});

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        setsOfElement[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int a;
            cin >> a;
            --a; // convert to 0-based
            if (a < 0 || a >= m) continue;
            setsOfElement[i].push_back(a);
            elementsInSet[a].push_back(i);
        }
    }

    auto startTime = chrono::steady_clock::now();

    buildInitialSolution();
    localSearch(startTime);

    vector<int> result;
    result.reserve(m);
    for (int s = 0; s < m; ++s) {
        if (chosen[s])
            result.push_back(s + 1); // back to 1-based
    }

    cout << result.size() << '\n';
    for (size_t i = 0; i < result.size(); ++i) {
        if (i) cout << ' ';
        cout << result[i];
    }
    cout << '\n';

    return 0;
}