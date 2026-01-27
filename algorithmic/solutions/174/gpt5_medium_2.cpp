#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    // Data structures
    vector<array<int,3>> cnt(n);              // cnt[v][c] = number of neighbors of v colored c
    vector<int> color(n, -1);                 // current colors 0..2
    vector<int> conf(n, 0);                   // conf[v] = cnt[v][color[v]]
    vector<int> bestColor(n, 0);
    long long bestConfEdges = (long long)m;   // initialize worst

    // Greedy initialization (degree-based order with slight randomness)
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (adj[a].size() != adj[b].size()) return adj[a].size() > adj[b].size();
        return a < b;
    });

    for (int v = 0; v < n; ++v) cnt[v] = {0,0,0};
    for (int v : order) {
        int bestC = 0;
        int bestVal = INT_MAX;
        int vals[3] = {cnt[v][0], cnt[v][1], cnt[v][2]};
        for (int c = 0; c < 3; ++c) {
            if (vals[c] < bestVal) {
                bestVal = vals[c];
                bestC = c;
            } else if (vals[c] == bestVal && uniform_int_distribution<int>(0,1)(rng)) {
                bestC = c;
            }
        }
        color[v] = bestC;
        for (int u : adj[v]) {
            cnt[u][bestC]++;
        }
    }
    long long totalConfEdges = 0;
    for (int v = 0; v < n; ++v) {
        conf[v] = cnt[v][color[v]];
        totalConfEdges += conf[v];
    }
    totalConfEdges /= 2;
    bestConfEdges = totalConfEdges;
    bestColor = color;

    // Conflicted vertex list with O(1) add/remove
    vector<int> pos(n, -1);
    vector<int> confList;
    confList.reserve(n);
    auto addIfConflicted = [&](int v){
        if (conf[v] > 0 && pos[v] == -1) {
            pos[v] = (int)confList.size();
            confList.push_back(v);
        }
    };
    auto removeIfResolved = [&](int v){
        if (conf[v] == 0 && pos[v] != -1) {
            int i = pos[v];
            int last = confList.back();
            confList[i] = last;
            pos[last] = i;
            confList.pop_back();
            pos[v] = -1;
        }
    };
    auto maintainMembership = [&](int v){
        if (conf[v] > 0) {
            if (pos[v] == -1) addIfConflicted(v);
        } else {
            if (pos[v] != -1) removeIfResolved(v);
        }
    };

    for (int v = 0; v < n; ++v) if (conf[v] > 0) addIfConflicted(v);

    // Min-conflicts local search within time budget
    auto start = chrono::steady_clock::now();
    const long long timeBudgetMs = 800; // conservative time budget for local search
    const int checkInterval = 1024;
    int steps = 0;

    while (true) {
        if (confList.empty()) break;
        if ((steps & (checkInterval - 1)) == 0) {
            auto now = chrono::steady_clock::now();
            long long elapsed = chrono::duration_cast<chrono::milliseconds>(now - start).count();
            if (elapsed >= timeBudgetMs) break;
        }
        steps++;

        // Pick a conflicted vertex, biased towards higher conflict by sampling
        int v;
        if (confList.size() <= 3) {
            v = confList[uniform_int_distribution<int>(0, (int)confList.size()-1)(rng)];
        } else {
            int bestIdx = -1;
            int bestVal = -1;
            for (int t = 0; t < 3; ++t) {
                int idx = uniform_int_distribution<int>(0, (int)confList.size()-1)(rng);
                int u = confList[idx];
                if (conf[u] > bestVal) {
                    bestVal = conf[u];
                    bestIdx = idx;
                }
            }
            v = confList[bestIdx];
        }

        int oldC = color[v];
        int vals[3] = {cnt[v][0], cnt[v][1], cnt[v][2]};
        int minVal = min(vals[0], min(vals[1], vals[2]));
        int minColors[3], k = 0;
        for (int c = 0; c < 3; ++c) if (vals[c] == minVal) minColors[k++] = c;

        int newC;
        if (k == 1) {
            newC = minColors[0];
            if (newC == oldC) {
                // no change; pick another vertex next iteration
                continue;
            }
        } else {
            // choose among minimal colors, prefer changing color if possible
            int pick = uniform_int_distribution<int>(0, k-1)(rng);
            newC = minColors[pick];
            if (newC == oldC) {
                // choose a different minimal color
                int alt = (pick + 1 + uniform_int_distribution<int>(0, k-2)(rng)) % k;
                newC = minColors[alt];
            }
        }

        if (newC == oldC) continue; // safety

        // Apply move v: oldC -> newC
        int countOld = cnt[v][oldC];
        int countNew = cnt[v][newC];
        // Update neighbors
        for (int u : adj[v]) {
            cnt[u][oldC]--;
            cnt[u][newC]++;
            if (color[u] == oldC) {
                conf[u]--;
                if (conf[u] == 0) removeIfResolved(u);
            } else if (color[u] == newC) {
                if (conf[u] == 0) addIfConflicted(u);
                conf[u]++;
            }
        }
        // Update v
        conf[v] = cnt[v][newC];
        color[v] = newC;
        maintainMembership(v);

        // Update total conflicts
        totalConfEdges += (long long)(countNew - countOld);

        // Track best
        if (totalConfEdges < bestConfEdges) {
            bestConfEdges = totalConfEdges;
            bestColor = color;
            if (bestConfEdges == 0) break;
        }
    }

    // Output best found coloring (1..3)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestColor[i] + 1);
    }
    cout << '\n';
    return 0;
}