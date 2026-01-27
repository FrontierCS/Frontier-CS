#include <bits/stdc++.h>
using namespace std;

struct Entry {
    int id;
    int gain;
    double key;
    bool operator<(Entry const& other) const {
        if (key != other.key) return key > other.key; // min-heap behavior via greater key
        if (gain != other.gain) return gain < other.gain; // prefer larger gain
        return id > other.id;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<long long> cost(m);
    for (int i = 0; i < m; ++i) cin >> cost[i];
    vector<vector<int>> setsElems(m);
    vector<vector<int>> elemsSets(n);
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        elemsSets[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int a; cin >> a; --a;
            if (a >= 0 && a < m) {
                setsElems[a].push_back(i);
                elemsSets[i].push_back(a);
            }
        }
    }

    // Quick feasibility check
    for (int i = 0; i < n; ++i) {
        if (elemsSets[i].empty()) {
            cout << 0 << "\n\n";
            return 0;
        }
    }

    auto solveOnce = [&](mt19937 &rng, double noiseAmp) {
        vector<double> adjCost(m);
        uniform_real_distribution<double> dist(1.0 - noiseAmp, 1.0 + noiseAmp);
        for (int i = 0; i < m; ++i) {
            adjCost[i] = (double)cost[i] * dist(rng);
            if (adjCost[i] <= 0) adjCost[i] = 1e-12;
        }
        vector<int> gain(m);
        for (int i = 0; i < m; ++i) gain[i] = (int)setsElems[i].size();
        vector<char> covered(n, 0), chosen(m, 0);
        int uncovered = n;
        priority_queue<Entry> pq;
        for (int i = 0; i < m; ++i) {
            if (gain[i] > 0) pq.push({i, gain[i], adjCost[i] / (double)gain[i]});
        }
        vector<int> sel;
        sel.reserve(n);
        while (uncovered > 0 && !pq.empty()) {
            Entry cur = pq.top(); pq.pop();
            int id = cur.id;
            if (chosen[id]) continue;
            if (cur.gain != gain[id]) {
                if (gain[id] > 0) pq.push({id, gain[id], adjCost[id] / (double)gain[id]});
                continue;
            }
            if (gain[id] == 0) continue;
            // pick set id
            chosen[id] = 1;
            sel.push_back(id);
            for (int e : setsElems[id]) {
                if (!covered[e]) {
                    covered[e] = 1;
                    --uncovered;
                    for (int s : elemsSets[e]) {
                        if (!chosen[s] && gain[s] > 0) {
                            --gain[s];
                            if (gain[s] > 0) {
                                pq.push({s, gain[s], adjCost[s] / (double)gain[s]});
                            }
                        }
                    }
                }
            }
        }

        // If still uncovered (shouldn't happen if feasible), try to add any set covering uncovered elements
        if (uncovered > 0) {
            vector<int> need;
            need.reserve(uncovered);
            for (int i = 0; i < n; ++i) if (!covered[i]) need.push_back(i);
            for (int e : need) {
                int best = -1;
                double bestKey = 1e300;
                for (int s : elemsSets[e]) {
                    if (!chosen[s]) {
                        double key = adjCost[s] / max(1, (int)setsElems[s].size());
                        if (key < bestKey) {
                            bestKey = key;
                            best = s;
                        }
                    }
                }
                if (best != -1 && !chosen[best]) {
                    chosen[best] = 1;
                    sel.push_back(best);
                    for (int ee : setsElems[best]) {
                        if (!covered[ee]) {
                            covered[ee] = 1;
                            --uncovered;
                        }
                    }
                }
                if (uncovered == 0) break;
            }
        }

        // If still uncovered, give up and return empty
        if (uncovered > 0) {
            return vector<int>();
        }

        // Prune redundant sets
        vector<int> coverCnt(n, 0);
        for (int s : sel) {
            for (int e : setsElems[s]) ++coverCnt[e];
        }
        sort(sel.begin(), sel.end(), [&](int a, int b){
            if (cost[a] != cost[b]) return cost[a] > cost[b]; // try to drop expensive first
            return setsElems[a].size() < setsElems[b].size();
        });
        vector<char> keep(m, 0);
        for (int s : sel) keep[s] = 1;
        for (int s : sel) {
            bool canRemove = true;
            for (int e : setsElems[s]) {
                if (coverCnt[e] <= 1) { canRemove = false; break; }
            }
            if (canRemove) {
                keep[s] = 0;
                for (int e : setsElems[s]) --coverCnt[e];
            }
        }
        vector<int> result;
        result.reserve(sel.size());
        for (int s : sel) if (keep[s]) result.push_back(s);
        return result;
    };

    auto computeCost = [&](const vector<int>& sel) {
        long long c = 0;
        for (int s : sel) c += cost[s];
        return c;
    };

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto start = chrono::steady_clock::now();
    const double timeLimitSec = 9.5;
    vector<int> bestSel;
    long long bestCost = LLONG_MAX;

    // Deterministic run without noise first
    {
        mt19937 rng0(1234567);
        auto sel = solveOnce(rng0, 0.0);
        if (!sel.empty()) {
            long long c = computeCost(sel);
            if (c < bestCost) {
                bestCost = c;
                bestSel = move(sel);
            }
        }
    }

    int iter = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > timeLimitSec) break;
        double noiseAmp = 0.15; // +/- 15%
        auto sel = solveOnce(rng, noiseAmp);
        if (!sel.empty()) {
            long long c = computeCost(sel);
            if (c < bestCost) {
                bestCost = c;
                bestSel = move(sel);
            }
        }
        ++iter;
    }

    if (bestSel.empty()) {
        cout << 0 << "\n\n";
        return 0;
    }
    // Output
    cout << bestSel.size() << "\n";
    for (size_t i = 0; i < bestSel.size(); ++i) {
        if (i) cout << ' ';
        cout << (bestSel[i] + 1);
    }
    cout << "\n";
    return 0;
}