#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<int> eu(M), ev(M);
    vector<vector<int>> adj(N + 1);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        eu[i] = u;
        ev[i] = v;
        adj[u].push_back(i);
        adj[v].push_back(i);
    }

    vector<int> deg(N + 1);
    for (int i = 1; i <= N; ++i) {
        deg[i] = (int)adj[i].size();
    }

    // Precompute vertex orders by degree
    vector<int> orderAsc(N);
    for (int i = 0; i < N; ++i) orderAsc[i] = i + 1;
    sort(orderAsc.begin(), orderAsc.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    vector<int> orderDesc = orderAsc;
    reverse(orderDesc.begin(), orderDesc.end());

    // Candidate 1: Greedy vertex cover (set cover style) + minimalization
    vector<char> chosen1(N + 1, 0);
    vector<char> edgeCovered(M, 0);
    vector<int> score(N + 1, 0);
    for (int v = 1; v <= N; ++v) {
        score[v] = deg[v];
    }

    int uncovered = M;
    priority_queue<pair<int, int>> pq;
    for (int v = 1; v <= N; ++v) {
        if (score[v] > 0) pq.push({score[v], v});
    }

    while (uncovered > 0 && !pq.empty()) {
        auto [sc, v] = pq.top();
        pq.pop();
        if (chosen1[v]) continue;
        if (sc != score[v]) continue;
        if (sc == 0) continue; // safety, should not happen when uncovered > 0

        chosen1[v] = 1;
        for (int ei : adj[v]) {
            if (!edgeCovered[ei]) {
                edgeCovered[ei] = 1;
                --uncovered;
                int u = (eu[ei] == v ? ev[ei] : eu[ei]);
                if (!chosen1[u]) {
                    if (score[u] > 0) --score[u];
                    pq.push({score[u], u});
                }
            }
        }
    }

    // Fallback in the unlikely case uncovered > 0 due to some bug
    if (uncovered > 0) {
        fill(chosen1.begin(), chosen1.end(), 0);
        for (int v = 1; v <= N; ++v) {
            if (deg[v] > 0) chosen1[v] = 1;
        }
    }

    // Minimalization of candidate 1
    vector<uint8_t> cov(M, 0);
    for (int i = 0; i < M; ++i) {
        cov[i] = (chosen1[eu[i]] ? 1 : 0) + (chosen1[ev[i]] ? 1 : 0);
    }

    for (int idx = 0; idx < N; ++idx) {
        int v = orderAsc[idx];
        if (!chosen1[v]) continue;
        bool canRemove = true;
        for (int ei : adj[v]) {
            if (cov[ei] <= 1) {
                canRemove = false;
                break;
            }
        }
        if (!canRemove) continue;
        chosen1[v] = 0;
        for (int ei : adj[v]) {
            --cov[ei];
        }
    }

    int bestK = 0;
    for (int v = 1; v <= N; ++v) if (chosen1[v]) ++bestK;
    vector<char> bestChosen = chosen1;

    // Helper lambda to build MIS-based cover from a given order
    auto buildMISCover = [&](const vector<int>& order) -> vector<char> {
        vector<char> inI(N + 1, 0);
        for (int v : order) {
            bool ok = true;
            for (int ei : adj[v]) {
                int u = (eu[ei] == v ? ev[ei] : eu[ei]);
                if (inI[u]) {
                    ok = false;
                    break;
                }
            }
            if (ok) inI[v] = 1;
        }
        vector<char> cover(N + 1, 0);
        for (int v = 1; v <= N; ++v) {
            cover[v] = inI[v] ? 0 : 1;
        }
        return cover;
    };

    auto evaluateAndUpdateBest = [&](vector<char>& cand) {
        int K = 0;
        for (int v = 1; v <= N; ++v) if (cand[v]) ++K;
        if (K < bestK) {
            bestK = K;
            bestChosen = cand;
        }
    };

    // Candidate 2: MIS with ascending degree order
    {
        vector<char> cand = buildMISCover(orderAsc);
        evaluateAndUpdateBest(cand);
    }

    // Candidate 3: MIS with descending degree order
    {
        vector<char> cand = buildMISCover(orderDesc);
        evaluateAndUpdateBest(cand);
    }

    // Candidate 4: MIS with random order (deterministic seed)
    {
        mt19937 rng(71236781);
        vector<int> orderRand = orderAsc;
        shuffle(orderRand.begin(), orderRand.end(), rng);
        vector<char> cand = buildMISCover(orderRand);
        evaluateAndUpdateBest(cand);
    }

    // Final safety check: ensure bestChosen is a vertex cover; fallback to trivial if not
    bool ok = true;
    for (int i = 0; i < M; ++i) {
        int u = eu[i], v = ev[i];
        if (!bestChosen[u] && !bestChosen[v]) {
            ok = false;
            break;
        }
    }
    if (!ok) {
        fill(bestChosen.begin(), bestChosen.end(), 0);
        for (int v = 1; v <= N; ++v) {
            if (deg[v] > 0) bestChosen[v] = 1;
        }
    }

    for (int v = 1; v <= N; ++v) {
        cout << (bestChosen[v] ? 1 : 0) << '\n';
    }

    return 0;
}