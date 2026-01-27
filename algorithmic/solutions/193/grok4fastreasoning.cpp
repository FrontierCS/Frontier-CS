#include <bits/stdc++.h>

using namespace std;

bool eval_lit(int l, const vector<char>& assign) {
    int v = abs(l);
    bool val = assign[v];
    return l > 0 ? val : !val;
}

int compute_score(const vector<pair<int, int>>& clauses, const vector<char>& assign) {
    int s = 0;
    for (auto& cl : clauses) {
        int a = cl.first, b = cl.second;
        if (eval_lit(a, assign) || eval_lit(b, assign)) s++;
    }
    return s;
}

int compute_delta(int v, const vector<char>& assign, const vector<vector<pair<int, bool>>>& incidences) {
    int d = 0;
    bool current = assign[v];
    for (auto& p : incidences[v]) {
        int o = p.first;
        bool is_direct = p.second;
        bool eval_l = is_direct ? current : !current;
        bool eval_o = eval_lit(o, assign);
        if (!eval_l && !eval_o) d += 1;
        if (eval_l && !eval_o) d -= 1;
    }
    return d;
}

vector<char> do_local_search(int n, const vector<pair<int, int>>& clauses,
                             const vector<vector<pair<int, bool>>>& incidences,
                             const vector<vector<int>>& adj) {
    vector<char> assign(n + 1);
    for (int i = 1; i <= n; i++) {
        assign[i] = rand() % 2;
    }
    vector<int> delta(n + 1);
    for (int v = 1; v <= n; v++) {
        delta[v] = compute_delta(v, assign, incidences);
    }
    bool improved = true;
    while (improved) {
        improved = false;
        int best_v = -1, best_d = 0;
        for (int v = 1; v <= n; v++) {
            if (delta[v] > best_d) {
                best_d = delta[v];
                best_v = v;
            }
        }
        if (best_d > 0) {
            assign[best_v] = 1 - assign[best_v];
            set<int> to_up;
            to_up.insert(best_v);
            for (int w : adj[best_v]) to_up.insert(w);
            for (int w : to_up) {
                delta[w] = compute_delta(w, assign, incidences);
            }
            improved = true;
        }
    }
    return assign;
}

int main() {
    srand(time(NULL));
    int n, m;
    cin >> n >> m;
    vector<pair<int, int>> clauses(m);
    vector<vector<pair<int, bool>>> incidences(n + 1);
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        clauses[i] = {a, b};
        int ua = abs(a), ub = abs(b);
        incidences[ua].emplace_back(b, a > 0);
        incidences[ub].emplace_back(a, b > 0);
        adj[ua].push_back(ub);
        adj[ub].push_back(ua);
    }
    vector<char> best_assign(n + 1, 0);
    int best_score = -1;
    const int TRIALS = 10;
    for (int trial = 0; trial < TRIALS; trial++) {
        vector<char> assign = do_local_search(n, clauses, incidences, adj);
        int score = compute_score(clauses, assign);
        if (score > best_score) {
            best_score = score;
            best_assign = assign;
        }
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << (int)best_assign[i];
    }
    cout << endl;
    return 0;
}