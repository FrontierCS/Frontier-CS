#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; i++) cin >> cost[i];

    vector<vector<int>> elemSets(n + 1);
    vector<vector<int>> setElems(m + 1);

    for (int e = 1; e <= n; e++) {
        int k;
        cin >> k;
        elemSets[e].resize(k);
        for (int j = 0; j < k; j++) {
            int s;
            cin >> s;
            elemSets[e][j] = s;
            if (1 <= s && s <= m) setElems[s].push_back(e);
        }
        sort(elemSets[e].begin(), elemSets[e].end());
        elemSets[e].erase(unique(elemSets[e].begin(), elemSets[e].end()), elemSets[e].end());
    }

    vector<int> cntUncov(m + 1);
    for (int s = 1; s <= m; s++) {
        auto &v = setElems[s];
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
        cntUncov[s] = (int)v.size();
    }

    vector<char> covered(n + 1, 0);
    vector<char> chosen(m + 1, 0);
    vector<int> selected;
    int remaining = n;

    auto better = [&](int s, int t) -> bool {
        if (t == -1) return true;
        if (cost[s] == 0 && cost[t] == 0) {
            if (cntUncov[s] != cntUncov[t]) return cntUncov[s] > cntUncov[t];
            return s < t;
        }
        if (cost[s] == 0) return true;
        if (cost[t] == 0) return false;

        long long lhs = 1LL * cntUncov[s] * cost[t];
        long long rhs = 1LL * cntUncov[t] * cost[s];
        if (lhs != rhs) return lhs > rhs;
        if (cntUncov[s] != cntUncov[t]) return cntUncov[s] > cntUncov[t];
        if (cost[s] != cost[t]) return cost[s] < cost[t];
        return s < t;
    };

    while (remaining > 0) {
        int best = -1;
        for (int s = 1; s <= m; s++) {
            if (chosen[s]) continue;
            if (cntUncov[s] <= 0) continue;
            if (better(s, best)) best = s;
        }

        if (best == -1) {
            int e = -1;
            for (int i = 1; i <= n; i++) {
                if (!covered[i]) { e = i; break; }
            }
            if (e == -1) break;

            long long bestC = (1LL<<62);
            int bestS = -1;
            for (int s : elemSets[e]) {
                if (!chosen[s] && cost[s] < bestC) {
                    bestC = cost[s];
                    bestS = s;
                }
            }
            if (bestS == -1) break;
            best = bestS;
        }

        chosen[best] = 1;
        selected.push_back(best);

        for (int e : setElems[best]) {
            if (covered[e]) continue;
            covered[e] = 1;
            remaining--;
            for (int s2 : elemSets[e]) {
                if (!chosen[s2] && cntUncov[s2] > 0) cntUncov[s2]--;
            }
        }
    }

    // If still uncovered (should not happen if cover exists), attempt forced picks.
    if (remaining > 0) {
        for (int e = 1; e <= n; e++) {
            if (covered[e]) continue;
            int bestS = -1;
            long long bestC = (1LL<<62);
            for (int s : elemSets[e]) {
                if (!chosen[s] && cost[s] < bestC) {
                    bestC = cost[s];
                    bestS = s;
                }
            }
            if (bestS == -1) continue;
            chosen[bestS] = 1;
            selected.push_back(bestS);
            for (int ee : setElems[bestS]) covered[ee] = 1;
        }
    }

    // Redundancy removal: remove expensive sets first if possible.
    vector<int> coverCnt(n + 1, 0);
    for (int s : selected) {
        for (int e : setElems[s]) coverCnt[e]++;
    }

    vector<int> order = selected;
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (cost[a] != cost[b]) return cost[a] > cost[b];
        if (setElems[a].size() != setElems[b].size()) return setElems[a].size() < setElems[b].size();
        return a < b;
    });

    vector<char> keep(m + 1, 0);
    for (int s : selected) keep[s] = 1;

    for (int s : order) {
        if (!keep[s]) continue;
        bool canRemove = true;
        for (int e : setElems[s]) {
            if (coverCnt[e] <= 1) { canRemove = false; break; }
        }
        if (!canRemove) continue;
        keep[s] = 0;
        for (int e : setElems[s]) coverCnt[e]--;
    }

    vector<int> ans;
    ans.reserve(selected.size());
    for (int s : selected) if (keep[s]) ans.push_back(s);

    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); i++) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}