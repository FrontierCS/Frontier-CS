#include <bits/stdc++.h>
using namespace std;

static void pruneMinimal(int N, const vector<pair<int,int>>& edges, const vector<vector<int>>& inc, vector<char>& sel) {
    int M = (int)edges.size();
    vector<int> cntNotSel(N, 0);
    for (int i = 0; i < M; ++i) {
        int u = edges[i].first, v = edges[i].second;
        if (sel[u] && !sel[v]) cntNotSel[u]++;
        if (sel[v] && !sel[u]) cntNotSel[v]++;
    }
    deque<int> q;
    for (int v = 0; v < N; ++v) if (sel[v] && cntNotSel[v] == 0) q.push_back(v);
    while (!q.empty()) {
        int v = q.front(); q.pop_front();
        if (!sel[v] || cntNotSel[v] != 0) continue;
        sel[v] = 0;
        for (int ei : inc[v]) {
            int u = edges[ei].first ^ edges[ei].second ^ v;
            if (sel[u]) {
                cntNotSel[u]++; // v becomes not selected, so u gains a non-selected neighbor
            }
        }
    }
}

static vector<char> solveMatching(int N, const vector<pair<int,int>>& edges, const vector<vector<int>>& inc) {
    int M = (int)edges.size();
    vector<char> sel(N, 0), matched(N, 0);
    for (int i = 0; i < M; ++i) {
        int u = edges[i].first, v = edges[i].second;
        if (!matched[u] && !matched[v]) {
            matched[u] = matched[v] = 1;
            sel[u] = sel[v] = 1;
        }
    }
    pruneMinimal(N, edges, inc, sel);
    return sel;
}

static vector<char> solveGreedy(int N, const vector<pair<int,int>>& edges, const vector<vector<int>>& inc) {
    int M = (int)edges.size();
    vector<int> curr_deg(N, 0);
    for (int v = 0; v < N; ++v) curr_deg[v] = (int)inc[v].size();
    vector<char> sel(N, 0);
    vector<char> covered(M, 0);
    priority_queue<pair<int,int>> pq;
    for (int v = 0; v < N; ++v) pq.emplace(curr_deg[v], v);
    int uncovered = M;
    while (uncovered > 0) {
        if (pq.empty()) {
            // Fallback: pick an endpoint of any uncovered edge
            int v = -1;
            for (int i = 0; i < M; ++i) if (!covered[i]) { v = edges[i].first; break; }
            if (v == -1) break;
            if (!sel[v]) {
                sel[v] = 1;
                for (int ei : inc[v]) {
                    if (!covered[ei]) {
                        covered[ei] = 1;
                        --uncovered;
                        int w = edges[ei].first ^ edges[ei].second ^ v;
                        if (!sel[w]) {
                            curr_deg[w]--;
                            pq.emplace(curr_deg[w], w);
                        }
                    }
                }
                curr_deg[v] = 0;
            }
            continue;
        }
        auto [d, v] = pq.top(); pq.pop();
        if (d != curr_deg[v] || sel[v]) continue;
        if (d == 0) {
            // No uncovered edges incident; find any uncovered edge
            int pick = -1;
            for (int i = 0; i < M; ++i) if (!covered[i]) { pick = edges[i].first; break; }
            if (pick == -1) break;
            v = pick;
        }
        if (!sel[v]) {
            sel[v] = 1;
            for (int ei : inc[v]) {
                if (!covered[ei]) {
                    covered[ei] = 1;
                    --uncovered;
                    int w = edges[ei].first ^ edges[ei].second ^ v;
                    if (!sel[w]) {
                        curr_deg[w]--;
                        pq.emplace(curr_deg[w], w);
                    }
                }
            }
            curr_deg[v] = 0;
        }
    }
    pruneMinimal(N, edges, inc, sel);
    return sel;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long M_in;
    if (!(cin >> N >> M_in)) return 0;
    vector<pair<int,int>> edgesInput;
    edgesInput.reserve((size_t)M_in);
    for (long long i = 0; i < M_in; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        edgesInput.emplace_back(u, v);
    }
    sort(edgesInput.begin(), edgesInput.end());
    edgesInput.erase(unique(edgesInput.begin(), edgesInput.end()), edgesInput.end());
    int M = (int)edgesInput.size();

    vector<vector<int>> inc(N);
    for (int i = 0; i < M; ++i) {
        int u = edgesInput[i].first, v = edgesInput[i].second;
        inc[u].push_back(i);
        inc[v].push_back(i);
    }

    vector<char> solA = solveMatching(N, edgesInput, inc);
    vector<char> solB = solveGreedy(N, edgesInput, inc);

    int cntA = 0, cntB = 0;
    for (int i = 0; i < N; ++i) { cntA += solA[i]; cntB += solB[i]; }

    const vector<char>& best = (cntB < cntA ? solB : solA);
    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}