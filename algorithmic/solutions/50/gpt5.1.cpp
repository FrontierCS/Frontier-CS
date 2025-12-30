#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<long long> cost(m + 1);
    for (int j = 1; j <= m; ++j) cin >> cost[j];

    vector<vector<int>> setsOfElement(n + 1);
    vector<vector<int>> elementsOfSet(m + 1);
    vector<double> elemWeight(n + 1);

    for (int i = 1; i <= n; ++i) {
        int k;
        cin >> k;
        setsOfElement[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int s;
            cin >> s;
            setsOfElement[i].push_back(s);
            elementsOfSet[s].push_back(i);
        }
        if (k > 0) elemWeight[i] = 1.0 / k;
        else elemWeight[i] = 0.0;
    }

    const double EPS = 1e-12;

    vector<double> setWeight(m + 1, 0.0);
    for (int s = 1; s <= m; ++s) {
        double w = 0.0;
        for (int e : elementsOfSet[s]) w += elemWeight[e];
        setWeight[s] = w;
    }

    vector<char> covered(n + 1, false);
    vector<char> chosen(m + 1, false);
    vector<int> version(m + 1, 0);

    struct Node {
        double ratio;
        int setId;
        int version;
    };
    struct Cmp {
        bool operator()(Node const& a, Node const& b) const {
            return a.ratio > b.ratio; // min-heap by ratio
        }
    };
    priority_queue<Node, vector<Node>, Cmp> pq;

    for (int s = 1; s <= m; ++s) {
        if (setWeight[s] > EPS) {
            pq.push(Node{ (double)cost[s] / setWeight[s], s, 0 });
        }
    }

    int uncoveredRem = n;
    vector<int> selectedList;

    while (uncoveredRem > 0 && !pq.empty()) {
        Node cur = pq.top();
        pq.pop();
        int s = cur.setId;
        if (cur.version != version[s]) continue;
        if (chosen[s]) continue;
        if (setWeight[s] <= EPS) continue;

        chosen[s] = true;
        selectedList.push_back(s);

        for (int e : elementsOfSet[s]) {
            if (!covered[e]) {
                covered[e] = true;
                --uncoveredRem;

                double we = elemWeight[e];
                if (we <= 0) continue;

                for (int t : setsOfElement[e]) {
                    if (setWeight[t] <= EPS) continue;
                    setWeight[t] -= we;
                    if (setWeight[t] < 0) setWeight[t] = 0;
                    ++version[t];
                    if (!chosen[t] && setWeight[t] > EPS) {
                        pq.push(Node{ (double)cost[t] / setWeight[t], t, version[t] });
                    }
                }
            }
        }
    }

    // Fallback if some elements still uncovered (should not happen for feasible instances)
    if (uncoveredRem > 0) {
        for (int e = 1; e <= n; ++e) {
            if (covered[e]) continue;
            if (setsOfElement[e].empty()) continue;
            int s = setsOfElement[e][0];
            if (!chosen[s]) {
                chosen[s] = true;
                selectedList.push_back(s);
                for (int ee : elementsOfSet[s]) {
                    if (!covered[ee]) {
                        covered[ee] = true;
                        --uncoveredRem;
                    }
                }
            }
        }
    }

    // Redundancy elimination
    vector<int> coverage(n + 1, 0);
    for (int s = 1; s <= m; ++s) {
        if (!chosen[s]) continue;
        for (int e : elementsOfSet[s]) coverage[e]++;
    }

    vector<int> chosenList;
    for (int s = 1; s <= m; ++s)
        if (chosen[s]) chosenList.push_back(s);

    sort(chosenList.begin(), chosenList.end(),
         [&](int a, int b) {
             if (cost[a] != cost[b]) return cost[a] > cost[b]; // remove expensive first
             return a < b;
         });

    for (int s : chosenList) {
        if (!chosen[s]) continue;
        bool canRemove = true;
        for (int e : elementsOfSet[s]) {
            if (coverage[e] == 1) {
                canRemove = false;
                break;
            }
        }
        if (canRemove) {
            chosen[s] = false;
            for (int e : elementsOfSet[s]) coverage[e]--;
        }
    }

    vector<int> finalSets;
    finalSets.reserve(m);
    for (int s = 1; s <= m; ++s)
        if (chosen[s]) finalSets.push_back(s);

    sort(finalSets.begin(), finalSets.end());

    cout << finalSets.size() << "\n";
    for (size_t i = 0; i < finalSets.size(); ++i) {
        if (i) cout << ' ';
        cout << finalSets[i];
    }
    cout << "\n";

    return 0;
}