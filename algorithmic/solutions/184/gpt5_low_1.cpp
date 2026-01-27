#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<int>> adj(N);
    adj.reserve(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> degree(N);
    for (int i = 0; i < N; ++i) degree[i] = (int)adj[i].size();

    auto start = chrono::steady_clock::now();
    const double timeLimitSec = 1.85; // leave margin for I/O
    auto timeLeft = [&]() {
        chrono::duration<double> elapsed = chrono::steady_clock::now() - start;
        return elapsed.count() < timeLimitSec;
    };

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Helper functions
    auto computeCounts = [&](const vector<char>& sel) {
        vector<int> cnt(N, 0);
        for (int v = 0; v < N; ++v) if (sel[v]) {
            for (int u : adj[v]) cnt[u]++;
        }
        return cnt;
    };

    auto add_vertex = [&](int v, vector<char>& sel, vector<int>& cnt) {
        sel[v] = 1;
        for (int u : adj[v]) cnt[u]++;
    };

    auto remove_vertex = [&](int v, vector<char>& sel, vector<int>& cnt) {
        sel[v] = 0;
        for (int u : adj[v]) cnt[u]--;
    };

    auto greedy_fill = [&](vector<char>& sel, vector<int>& cnt) {
        while (true) {
            int chosen = -1;
            int bestDeg = INT_MAX;
            for (int i = 0; i < N; ++i) {
                if (!sel[i] && cnt[i] == 0) {
                    int d = degree[i];
                    if (d < bestDeg) {
                        bestDeg = d;
                        chosen = i;
                    }
                }
            }
            if (chosen == -1) break;
            add_vertex(chosen, sel, cnt);
        }
    };

    // Initial solution: start empty and greedy fill by min degree
    vector<char> sel(N, 0);
    vector<int> cnt(N, 0);
    greedy_fill(sel, cnt);
    int curSize = accumulate(sel.begin(), sel.end(), 0);

    vector<char> bestSel = sel;
    int bestSize = curSize;

    // Local search with swaps and greedy augmentation
    int stagnation = 0;
    while (timeLeft()) {
        // Ensure maximal
        greedy_fill(sel, cnt);
        curSize = accumulate(sel.begin(), sel.end(), 0);
        if (curSize > bestSize) {
            bestSize = curSize;
            bestSel = sel;
            stagnation = 0;
        } else {
            stagnation++;
        }

        // Collect candidates with exactly one conflict (nbrSelCount == 1)
        vector<int> cand;
        cand.reserve(N);
        for (int v = 0; v < N; ++v) {
            if (!sel[v] && cnt[v] == 1) cand.push_back(v);
        }

        bool progressed = false;

        if (!cand.empty()) {
            uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
            int v = cand[dist(rng)];

            int w = -1;
            for (int u : adj[v]) if (sel[u]) { w = u; break; }
            if (w != -1) {
                // Backup
                vector<char> sel_backup = sel;
                vector<int> cnt_backup = cnt;
                int prevSize = curSize;

                remove_vertex(w, sel, cnt);
                add_vertex(v, sel, cnt);
                greedy_fill(sel, cnt);
                curSize = accumulate(sel.begin(), sel.end(), 0);

                if (curSize >= prevSize) {
                    progressed = true;
                    if (curSize > bestSize) {
                        bestSize = curSize;
                        bestSel = sel;
                        stagnation = 0;
                    }
                } else {
                    sel.swap(sel_backup);
                    cnt.swap(cnt_backup);
                    curSize = prevSize;
                }
            }
        }

        // Diversification: occasionally drop a random selected vertex to escape local optimum
        if (!progressed) {
            if (stagnation > 50) {
                vector<int> selectedVerts;
                for (int i = 0; i < N; ++i) if (sel[i]) selectedVerts.push_back(i);
                if (!selectedVerts.empty()) {
                    uniform_int_distribution<int> dist(0, (int)selectedVerts.size() - 1);
                    int w = selectedVerts[dist(rng)];
                    remove_vertex(w, sel, cnt);
                    stagnation = 0;
                } else {
                    break;
                }
            }
        }
    }

    // Output best solution
    for (int i = 0; i < N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << '\n';
    }
    return 0;
}