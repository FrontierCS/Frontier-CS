#include <bits/stdc++.h>
using namespace std;

struct Graph {
    int n;
    int m;
    vector<pair<int,int>> edges; // 0-based
    vector<vector<int>> adjE;    // adjacency as edge indices

    Graph(int n, int m): n(n), m(m), edges(m), adjE(n) {}
};

vector<int> greedy_degree_cover(const Graph& G) {
    int n = G.n, m = G.m;
    vector<int> deg_rem(n, 0);
    for (int i = 0; i < m; ++i) {
        deg_rem[G.edges[i].first]++;
        deg_rem[G.edges[i].second]++;
    }
    vector<char> covered(m, 0);
    vector<int> S(n, 0);

    for (int i = 0; i < m; ++i) {
        if (covered[i]) continue;
        int u = G.edges[i].first, v = G.edges[i].second;
        if (S[u] || S[v]) {
            // If either already selected, cover edges accordingly
            int pick = S[u] ? u : v;
            for (int eid : G.adjE[pick]) {
                if (!covered[eid]) {
                    covered[eid] = 1;
                    int a = G.edges[eid].first, b = G.edges[eid].second;
                    int other = (a == pick ? b : a);
                    if (!S[other]) deg_rem[other]--;
                }
            }
            continue;
        }
        int pick = (deg_rem[u] >= deg_rem[v] ? u : v);
        if (!S[pick]) {
            S[pick] = 1;
            // cover all incident edges of pick
            for (int eid : G.adjE[pick]) {
                if (!covered[eid]) {
                    covered[eid] = 1;
                    int a = G.edges[eid].first, b = G.edges[eid].second;
                    int other = (a == pick ? b : a);
                    if (!S[other]) deg_rem[other]--;
                }
            }
            deg_rem[pick] = 0;
        }
    }
    return S;
}

vector<int> maximal_matching_cover(const Graph& G) {
    int n = G.n, m = G.m;
    vector<char> matched(n, 0);
    vector<int> S(n, 0);
    for (int i = 0; i < m; ++i) {
        int u = G.edges[i].first, v = G.edges[i].second;
        if (!matched[u] && !matched[v]) {
            matched[u] = matched[v] = 1;
            S[u] = S[v] = 1;
        }
    }
    return S;
}

void remove_redundant(const Graph& G, vector<int>& S) {
    bool changed = true;
    // Multiple passes to catch cascading opportunities
    while (changed) {
        changed = false;
        for (int v = 0; v < G.n; ++v) {
            if (!S[v]) continue;
            bool can_remove = true;
            for (int eid : G.adjE[v]) {
                int a = G.edges[eid].first, b = G.edges[eid].second;
                int u = (a == v ? b : a);
                if (!S[u]) { can_remove = false; break; }
            }
            if (can_remove) {
                S[v] = 0;
                changed = true;
            }
        }
    }
}

bool is_valid(const Graph& G, const vector<int>& S) {
    for (int i = 0; i < G.m; ++i) {
        int u = G.edges[i].first, v = G.edges[i].second;
        if (!(S[u] || S[v])) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    Graph G(N, M);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        G.edges[i] = {u, v};
        G.adjE[u].push_back(i);
        G.adjE[v].push_back(i);
    }

    vector<int> S1 = greedy_degree_cover(G);
    remove_redundant(G, S1);

    vector<int> S2 = maximal_matching_cover(G);
    remove_redundant(G, S2);

    // Choose the smaller valid solution. In unlikely case of invalid (shouldn't happen), fallback.
    vector<int>* best = &S1;
    if (is_valid(G, S2)) {
        if (!is_valid(G, S1) || accumulate(S2.begin(), S2.end(), 0) < accumulate(S1.begin(), S1.end(), 0)) {
            best = &S2;
        }
    } else if (!is_valid(G, S1)) {
        // Fallback to simple maximal matching without reduction (always valid)
        best = new vector<int>(maximal_matching_cover(G));
    }

    for (int i = 0; i < N; ++i) {
        cout << (*best)[i] << '\n';
    }

    return 0;
}